// Límite de parada seguro: se evalúa cada ventana de muestreo; si se supera, el banco se detiene solo.
export interface Limits {
  maxLateRatio: number;     // fracción de tramas fuera de plazo en la ventana (respuesta > 20 ms)
  maxTickP99Ms: number;     // p99 del tiempo de trama en la ventana
  maxMemMiB: number;        // memoria del cgroup
  maxPids: number;          // procesos del cgroup
  maxFailures: number;      // fallos acumulados (TIMEOUT, WORKER, PROTOCOL, BUSY…)
}

// Valores por defecto: hay margen sobre el uso previsto, pero lejos de dejar sin memoria la máquina.
export const DEFAULT_LIMITS: Limits = {
  maxLateRatio: 0.5, maxTickP99Ms: 200, maxMemMiB: 450, maxPids: 200, maxFailures: 0
};

export interface Window {
  frames: number; late: number; tickP99Ms: number; memMiB?: number; pids?: number; failures: number;
}

export function evaluateLimits(w: Window, limits: Limits): string | undefined {
  if (w.failures > limits.maxFailures) return `fallos ${w.failures} > ${limits.maxFailures}`;
  if (w.memMiB !== undefined && w.memMiB > limits.maxMemMiB) return `memoria ${w.memMiB.toFixed(1)} MiB > ${limits.maxMemMiB}`;
  if (w.pids !== undefined && w.pids > limits.maxPids) return `procesos ${w.pids} > ${limits.maxPids}`;
  if (w.frames > 0 && w.late / w.frames > limits.maxLateRatio)
    return `tramas fuera de plazo ${(100 * w.late / w.frames).toFixed(1)} % > ${100 * limits.maxLateRatio} %`;
  if (w.frames > 0 && w.tickP99Ms > limits.maxTickP99Ms) return `p99 ${w.tickP99Ms.toFixed(1)} ms > ${limits.maxTickP99Ms}`;
  return undefined;
}
