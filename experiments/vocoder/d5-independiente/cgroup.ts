import { readFileSync } from "node:fs";

// Lectura del cgroup v2 del propio contenedor. Sin cgroup v2 los campos quedan indefinidos y el
// informe lo dice; no se inventan valores.
export interface CgroupSample { cpuUsec?: number; throttledUsec?: number; memBytes?: number; memPeakBytes?: number; pids?: number }

function number(path: string): number | undefined {
  try { const v = Number(readFileSync(path, "utf8").trim()); return Number.isFinite(v) ? v : undefined; }
  catch { return undefined; }
}

export function readCgroup(root = "/sys/fs/cgroup"): CgroupSample {
  let cpuUsec: number | undefined, throttledUsec: number | undefined;
  try {
    const stat = readFileSync(root + "/cpu.stat", "utf8");
    cpuUsec = Number(/^usage_usec (\d+)$/m.exec(stat)?.[1]);
    throttledUsec = Number(/^throttled_usec (\d+)$/m.exec(stat)?.[1]);
  } catch { cpuUsec = undefined; }
  return { cpuUsec: Number.isFinite(cpuUsec) ? cpuUsec : undefined,
           throttledUsec: Number.isFinite(throttledUsec) ? throttledUsec : undefined,
           memBytes: number(root + "/memory.current"), memPeakBytes: number(root + "/memory.peak"),
           pids: number(root + "/pids.current") };
}
