// Pacing real de tramas de 20 ms, con reloj inyectable para probarlo sin esperar.
export const PERIOD_NS = 20_000_000n;

export interface Clock {
  nowNs(): bigint;
  sleepUntilNs(targetNs: bigint): Promise<void>;
}

// Reloj real: hrtime monotónico y setTimeout de al menos 1 ms. NO hace espera activa: un servidor
// real no la haría, y con 25 canales contaminaría la CPU y el bucle de eventos. La demora del
// temporizador (hasta ~1 ms) queda registrada como "lateness". (La primera versión devolvía una
// promesa ya resuelta cuando faltaba menos de 1 ms, lo que giraba en microtareas hasta el instante
// exacto: medía un pacing más preciso que el de un servidor real. Corregido el 17-nov.)
export function realClock(): Clock {
  return {
    nowNs: () => process.hrtime.bigint(),
    sleepUntilNs(target) {
      const ms = Math.max(1, Number((target - process.hrtime.bigint()) / 1_000_000n));
      return new Promise<void>(resolve => setTimeout(resolve, ms));
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
