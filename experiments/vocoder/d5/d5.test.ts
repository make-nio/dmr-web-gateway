import assert from "node:assert/strict";
import test from "node:test";
import { LOCAL, PCM, VocoderError, type VocoderSession } from "../d4/contract.js";
import { runChannel, type Sink } from "./channel.js";
import { DEFAULT_LIMITS, evaluateLimits } from "./limits.js";
import { PERIOD_NS, ticks, type Clock } from "./pacing.js";
import { percentile, summarize } from "./stats.js";

// Reloj simulado: el tiempo sólo avanza al dormir o cuando una operación «cuesta» algo.
function fakeClock() {
  let now = 1_000_000_000n;
  const clock: Clock & { advance(ns: bigint): void } = {
    nowNs: () => now,
    async sleepUntilNs(target) { if (target > now) now = target; },
    advance(ns) { now += ns; }
  };
  return clock;
}

function collector() {
  const log = { ops: [] as [string, number][], frames: [] as [number, number, boolean][], failures: [] as string[] };
  const sink: Sink = {
    op: (k, ns) => log.ops.push([k, ns]),
    frame: (d, l, late) => log.frames.push([d, l, late]),
    failure: code => log.failures.push(code)
  };
  return { log, sink };
}

function fakeSession(clock: ReturnType<typeof fakeClock>, costNs: (n: number) => bigint, failAt = -1): VocoderSession {
  let n = 0;
  return {
    async encode() { if (n === failAt) throw new VocoderError("TIMEOUT", "x"); clock.advance(costNs(n++)); return { format: LOCAL, bytes: new Uint8Array(9) }; },
    async decode() { if (n === failAt) throw new VocoderError("WORKER", "x"); clock.advance(costNs(n++)); return { format: PCM, bytes: new Uint8Array(320) }; },
    async reset() {}, async close() {}
  };
}

const pcm = Buffer.alloc(320 * 4), ambe = Buffer.alloc(9 * 4);
const opts = (clock: Clock, over: object = {}) => ({ mode: "tx" as const, frames: 5, firstNs: clock.nowNs() + 20_000_000n, pcm, ambe, offset: 0, shouldStop: () => false, ...over });

test("el pacing marca un tick cada 20 ms exactos con reloj simulado", async () => {
  const clock = fakeClock(), first = clock.nowNs();
  const seen: bigint[] = [];
  for await (const t of ticks(clock, 6, first)) { seen.push(t.startNs - first); assert.equal(t.latenessNs, 0n); }
  assert.deepEqual(seen, [0n, 1n, 2n, 3n, 4n, 5n].map(i => i * PERIOD_NS));
});

test("si el consumidor se atrasa no se saltean ticks y el atraso queda registrado", async () => {
  const clock = fakeClock(), first = clock.nowNs(), lateness: bigint[] = [];
  for await (const t of ticks(clock, 4, first)) {
    lateness.push(t.latenessNs);
    if (t.index === 1) clock.advance(70_000_000n);       // un tick tarda 70 ms
  }
  // tick 2 y 3 vencían en 40 y 60 ms; se está en 90 ms: se recuperan sin dormir
  assert.deepEqual(lateness, [0n, 0n, 50_000_000n, 30_000_000n]);
});

test("canal TX: 1 ms de costo por trama, ninguna fuera de plazo", async () => {
  const clock = fakeClock(), { log, sink } = collector();
  await runChannel(fakeSession(clock, () => 1_000_000n), clock, sink, opts(clock));
  assert.equal(log.frames.length, 5);
  assert.ok(log.frames.every(([d, , late]) => d === 1_000_000 && !late));
  assert.ok(log.ops.every(([k, ns]) => k === "E" && ns === 1_000_000));
});

test("canal RX usa decode y dúplex usa encode y decode en la misma trama", async () => {
  for (const [mode, kinds] of [["rx", "D"], ["duplex", "ED"]] as const) {
    const clock = fakeClock(), { log, sink } = collector();
    await runChannel(fakeSession(clock, () => 1_000_000n), clock, sink, opts(clock, { mode, frames: 3 }));
    assert.equal(log.ops.map(([k]) => k).join(""), kinds.repeat(3), mode);
    assert.equal(log.frames.length, 3);
  }
});

test("una trama que se entrega pasados 20 ms cuenta como fuera de plazo", async () => {
  const clock = fakeClock(), { log, sink } = collector();
  await runChannel(fakeSession(clock, n => (n === 2 ? 25_000_000n : 1_000_000n)), clock, sink, opts(clock));
  assert.deepEqual(log.frames.map(f => f[2]), [false, false, true, false, false]);
});

test("un fallo de la sesión se registra con su código y termina ese canal", async () => {
  const clock = fakeClock(), { log, sink } = collector();
  await runChannel(fakeSession(clock, () => 1_000_000n, 2), clock, sink, opts(clock));
  assert.deepEqual(log.failures, ["TIMEOUT"]);
  assert.equal(log.frames.length, 2);
});

test("shouldStop detiene el canal sin más tramas", async () => {
  const clock = fakeClock(), { log, sink } = collector();
  let n = 0;
  await runChannel(fakeSession(clock, () => 1_000_000n), clock, sink, opts(clock, { frames: 50, shouldStop: () => n++ >= 3 }));
  assert.equal(log.frames.length, 3);
});

test("percentiles: mismo criterio que D4 (índices 499 y 949 sobre 1000)", () => {
  const v = Array.from({ length: 1000 }, (_, i) => i);
  assert.equal(percentile(v, 0.5), 499);
  assert.equal(percentile(v, 0.95), 949);
  assert.equal(percentile(v, 0.99), 989);
  assert.deepEqual(summarize([3, 1, 2]), { count: 3, p50: 2, p95: 3, p99: 3, max: 3 });
  assert.ok(Number.isNaN(percentile([], 0.5)));
});

test("límites de parada: cada umbral detiene y lo normal no", () => {
  const ok = { frames: 50, late: 0, tickP99Ms: 3, memMiB: 100, pids: 30, failures: 0 };
  assert.equal(evaluateLimits(ok, DEFAULT_LIMITS), undefined);
  assert.match(evaluateLimits({ ...ok, failures: 1 }, DEFAULT_LIMITS)!, /fallos/);
  assert.match(evaluateLimits({ ...ok, memMiB: 451 }, DEFAULT_LIMITS)!, /memoria/);
  assert.match(evaluateLimits({ ...ok, pids: 201 }, DEFAULT_LIMITS)!, /procesos/);
  assert.match(evaluateLimits({ ...ok, late: 26 }, DEFAULT_LIMITS)!, /fuera de plazo/);
  assert.match(evaluateLimits({ ...ok, tickP99Ms: 201 }, DEFAULT_LIMITS)!, /p99/);
  assert.equal(evaluateLimits({ ...ok, late: 25 }, DEFAULT_LIMITS), undefined);   // exactamente en el tope: sigue
  assert.equal(evaluateLimits({ ...ok, memMiB: undefined, pids: undefined }, DEFAULT_LIMITS), undefined);
});
