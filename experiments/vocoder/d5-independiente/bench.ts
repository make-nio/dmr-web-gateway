import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { configure } from "../d4/config.js";
import { LOCAL, PCM, type VocoderSession } from "../d4/contract.js";
import { readCgroup } from "./cgroup.js";
import { runChannel, type Mode, type Sink } from "./channel.js";
import { DEFAULT_LIMITS, evaluateLimits, type Limits } from "./limits.js";
import { PERIOD_NS, realClock } from "./pacing.js";
import { summarize } from "./stats.js";

// Uso: node bench.js --provider opendmr|blip25|simulated --mode rx|tx|duplex --channels N
//                    [--seconds 20] [--limits '{"maxMemMiB":400}'] [--out resultado.json]
function arg(name: string, fallback?: string): string {
  const at = process.argv.indexOf("--" + name);
  const value = at >= 0 ? process.argv[at + 1] : fallback;
  if (value === undefined) throw new RangeError("falta --" + name);
  return value;
}

const provider = arg("provider"), mode = arg("mode") as Mode, channels = Number(arg("channels"));
const seconds = Number(arg("seconds", "20")), out = arg("out", "");
const limits: Limits = { ...DEFAULT_LIMITS, ...JSON.parse(arg("limits", "{}")) };
if (!["rx", "tx", "duplex"].includes(mode) || !Number.isInteger(channels) || channels < 1 || !(seconds > 0))
  throw new RangeError("argumentos inválidos");

function loadPcm(): Buffer {
  const path = process.env.D5_PCM ?? "/tmp/d4.s16le";
  if (existsSync(path)) return readFileSync(path).subarray(0, 1000 * 320);
  if (provider !== "simulated") throw new Error("falta el PCM de referencia " + path + " (ver d4/prepare.py)");
  const parts: Buffer[] = [];           // simulado sin archivo: PCM determinista
  for (let i = 0; i < 1000; i++) parts.push(Buffer.concat(Array(10).fill(createHash("sha256").update(String(i)).digest())).subarray(0, 320));
  return Buffer.concat(parts);
}

const clock = realClock();
const pcm = loadPcm();
const frames = Math.round(seconds * 1e9 / Number(PERIOD_NS));
const vocoder = configure(provider, 5000);

// Preparación fuera de la medición: tramas AMBE para el sentido RX.
const prep = await vocoder.createSession();
const ambeParts: Buffer[] = [];
for (let i = 0; i < 1000; i++)
  ambeParts.push(Buffer.from((await prep.encode({ format: PCM, bytes: pcm.subarray(i * 320, i * 320 + 320) })).bytes));
await prep.close();
const ambe = Buffer.concat(ambeParts);
void LOCAL;

const cgBase = readCgroup();     // antes de arrancar las sesiones
// Arranque de las sesiones (una por canal), con su tiempo.
const sessions: VocoderSession[] = [], startupMs: number[] = [];
let stopReason: string | undefined;
const startFailures: string[] = [];
for (let i = 0; i < channels; i++) {
  const t = clock.nowNs();
  try { sessions.push(await vocoder.createSession()); startupMs.push(Number(clock.nowNs() - t) / 1e6); }
  catch (error) { startFailures.push(String((error as Error).message)); stopReason = "no arrancó la sesión " + (i + 1); break; }
}

// Recolección.
const encodeMs: number[] = [], decodeMs: number[] = [], deliveryMs: number[] = [], latenessMs: number[] = [];
let late = 0, failures = startFailures.length, frameCount = 0;
const failureCodes: Record<string, number> = {};
let win = { frames: 0, late: 0, delivery: [] as number[] };
const sink: Sink = {
  op: (kind, ns) => (kind === "E" ? encodeMs : decodeMs).push(ns / 1e6),
  frame(deliveryNs, latenessNs, isLate) {
    deliveryMs.push(deliveryNs / 1e6); latenessMs.push(latenessNs / 1e6); frameCount++;
    win.frames++; win.delivery.push(deliveryNs / 1e6);
    if (isLate) { late++; win.late++; }
  },
  failure(code) { failures++; failureCodes[code] = (failureCodes[code] ?? 0) + 1; }
};

const cg0 = readCgroup();
// memory.current incluye lo que ocupa el propio entorno (tmpfs con el runtime y lo compilado): se informa
// la base medida antes de las sesiones para poder restarla.
const memBaselineMiB = cgBase.memBytes !== undefined ? cgBase.memBytes / 1048576 : null;
const memSamples: number[] = [], pidSamples: number[] = [];
const firstNs = clock.nowNs() + 100_000_000n;
let stopped = false;
const sampler = setInterval(() => {
  const c = readCgroup();
  if (c.memBytes !== undefined) memSamples.push(c.memBytes / 1048576);
  if (c.pids !== undefined) pidSamples.push(c.pids);
  const sorted = [...win.delivery].sort((a, b) => a - b);
  const reason = evaluateLimits({
    frames: win.frames, late: win.late, failures, memMiB: c.memBytes !== undefined ? c.memBytes / 1048576 : undefined,
    pids: c.pids, tickP99Ms: sorted.length ? sorted[Math.min(sorted.length - 1, Math.ceil(0.99 * sorted.length) - 1)] : 0
  }, limits);
  win = { frames: 0, late: 0, delivery: [] };
  if (reason && !stopped) { stopped = true; stopReason = reason; }
}, 1000);

if (!stopReason) {
  await Promise.all(sessions.map((s, i) => runChannel(s, clock, sink, {
    mode, frames, firstNs, pcm, ambe, offset: (i * 37) % 1000, shouldStop: () => stopped
  })));
}
clearInterval(sampler);
const wallUs = Number(clock.nowNs() - firstNs) / 1000;
const cg1 = readCgroup();

// Cierre de las sesiones, con su tiempo.
const closeMs: number[] = [];
for (const s of sessions) {
  const t = clock.nowNs();
  try { await s.close(); } catch { failures++; failureCodes.CLOSE = (failureCodes.CLOSE ?? 0) + 1; }
  closeMs.push(Number(clock.nowNs() - t) / 1e6);
}

const mean = (v: number[]) => v.length ? v.reduce((a, b) => a + b, 0) / v.length : NaN;
const result = {
  provider, mode, channels, seconds, periodMs: Number(PERIOD_NS) / 1e6, framesPlanned: frames * channels, framesDelivered: frameCount,
  stopReason: stopReason ?? null, failures, failureCodes, limits,
  latencyMs: { encode: summarize(encodeMs), decode: summarize(decodeMs), delivery: summarize(deliveryMs), timerLateness: summarize(latenessMs) },
  lateFrames: late, lateRatio: frameCount ? late / frameCount : null,
  cpuPercentOfOneCpu: cg0.cpuUsec !== undefined && cg1.cpuUsec !== undefined ? 100 * (cg1.cpuUsec - cg0.cpuUsec) / wallUs : null,
  memMaxMiB: memSamples.length ? Math.max(...memSamples) : null,
  cpuThrottledUsec: cg0.throttledUsec !== undefined && cg1.throttledUsec !== undefined ? cg1.throttledUsec - cg0.throttledUsec : null,
  memBaselineMiB,
  memDeltaMaxMiB: memSamples.length && memBaselineMiB !== null ? Math.max(...memSamples) - memBaselineMiB : null,
  memPeakMiBCgroup: cg1.memPeakBytes !== undefined ? cg1.memPeakBytes / 1048576 : null,
  pidsMax: pidSamples.length ? Math.max(...pidSamples) : null,
  startupMs: { mean: mean(startupMs), max: startupMs.length ? Math.max(...startupMs) : null,
               slowest: startupMs.map((ms, index) => ({ session: index + 1, ms })).sort((a, b) => b.ms - a.ms).slice(0, 3) },
  closeMs: { mean: mean(closeMs), max: closeMs.length ? Math.max(...closeMs) : null },
  environment: { node: process.version, platform: process.platform + "/" + process.arch, cgroupV2: cg1.cpuUsec !== undefined }
};
const text = JSON.stringify(result, null, 1);
if (out) writeFileSync(out, text + "\n"); else console.log(text);
process.exit(failures || stopReason ? 3 : 0);
