// Pacing real de tramas de 20 ms, con reloj inyectable para probarlo sin esperar.
export const PERIOD_NS = 20_000_000n;

export interface Clock {
  nowNs(): bigint;
  sleepUntilNs(targetNs: bigint): Promise<void>;
}

// Reloj real: hrtime monotónico y setTimeout. No hace espera activa: con 25 canales eso
// contaminaría la medición de CPU. La demora del temporizador queda registrada como "lateness".
export function realClock(): Clock {
  return {
    nowNs: () => process.hrtime.bigint(),
    sleepUntilNs(target) {
      const ms = Number((target - process.hrtime.bigint()) / 1_000_000n);
      return ms <= 0 ? Promise.resolve() : new Promise<void>(resolve => setTimeout(resolve, ms));
    }
  };
}

export interface Tick { index: number; scheduledNs: bigint; startNs: bigint; latenessNs: bigint }

// Una trama cada `periodNs`, a partir de `firstNs`. Si el consumidor se atrasa NO se saltean
// ticks (se recupera sin dormir): el atraso queda a la vista en `latenessNs`.
export async function* ticks(clock: Clock, count: number, firstNs: bigint,
                             periodNs: bigint = PERIOD_NS): AsyncGenerator<Tick> {
  for (let index = 0; index < count; index++) {
    const scheduledNs = firstNs + BigInt(index) * periodNs;
    // setTimeout redondea hacia abajo a ms: se vuelve a dormir hasta llegar al instante.
    while (clock.nowNs() < scheduledNs) await clock.sleepUntilNs(scheduledNs);
    const startNs = clock.nowNs();
    yield { index, scheduledNs, startNs, latenessNs: startNs - scheduledNs };
  }
}
