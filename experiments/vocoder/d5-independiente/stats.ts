// Percentil por rango más cercano: índice ceil(q·n)−1. Es el mismo criterio que usa D4
// (p50 = valores[499] y p95 = valores[949] sobre 1000 muestras).
export function percentile(sorted: readonly number[], q: number): number {
  if (sorted.length === 0) return NaN;
  return sorted[Math.min(sorted.length - 1, Math.max(0, Math.ceil(q * sorted.length) - 1))];
}

export interface Summary { count: number; p50: number; p95: number; p99: number; max: number }

export function summarize(valuesMs: readonly number[]): Summary {
  const sorted = [...valuesMs].sort((a, b) => a - b);
  return { count: sorted.length, p50: percentile(sorted, 0.5), p95: percentile(sorted, 0.95),
           p99: percentile(sorted, 0.99), max: sorted.length ? sorted[sorted.length - 1] : NaN };
}
