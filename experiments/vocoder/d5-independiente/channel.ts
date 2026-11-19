import { LOCAL, PCM, VocoderError, type VocoderSession } from "../d4/contract.js";
import { PERIOD_NS, ticks, type Clock } from "./pacing.js";

export type Mode = "rx" | "tx" | "duplex";

export interface Sink {
  op(kind: "E" | "D", ns: number): void;                 // latencia de una operación (comparable con D4)
  frame(deliveryNs: number, latenessNs: number, late: boolean): void;
  failure(code: string): void;
}

export interface ChannelOptions {
  mode: Mode;
  frames: number;
  firstNs: bigint;
  pcm: Buffer;               // múltiplo de 320 bytes; se recorre de forma circular
  ambe: Buffer;              // múltiplo de 9 bytes (tramas locales ya codificadas); se usa en RX
  offset: number;            // trama inicial dentro de pcm/ambe, para que los canales no vayan sincronizados
  periodNs?: bigint;
  shouldStop(): boolean;
}

// RX = decode de una trama recibida; TX = encode de una trama de audio; dúplex = las dos en la
// misma trama de 20 ms (encode y luego decode de su resultado: una sesión admite una operación a la vez).
// Una trama está «fuera de plazo» si su resultado se entrega más de un período después de lo programado.
export async function runChannel(session: VocoderSession, clock: Clock, sink: Sink, o: ChannelOptions): Promise<void> {
  const period = o.periodNs ?? PERIOD_NS;
  const pcmFrames = o.pcm.length / 320, ambeFrames = o.ambe.length / 9;
  for await (const tick of ticks(clock, o.frames, o.firstNs, period)) {
    if (o.shouldStop()) return;
    try {
      if (o.mode === "rx") {
        const at = (o.offset + tick.index) % ambeFrames;
        await timed(sink, "D", clock, () => session.decode({ format: LOCAL, bytes: o.ambe.subarray(at * 9, at * 9 + 9) }));
      } else {
        const at = (o.offset + tick.index) % pcmFrames;
        const frame = await timed(sink, "E", clock, () => session.encode({ format: PCM, bytes: o.pcm.subarray(at * 320, at * 320 + 320) }));
        if (o.mode === "duplex") await timed(sink, "D", clock, () => session.decode(frame));
      }
    } catch (error) {
      sink.failure(error instanceof VocoderError ? error.code : "ERROR");
      return;            // la sesión terminó (contrato D4): este canal no sigue
    }
    const delivery = clock.nowNs() - tick.scheduledNs;
    sink.frame(Number(delivery), Number(tick.latenessNs), delivery > period);
  }
}

async function timed<T>(sink: Sink, kind: "E" | "D", clock: Clock, run: () => Promise<T>): Promise<T> {
  const start = clock.nowNs();
  const result = await run();
  sink.op(kind, Number(clock.nowNs() - start));
  return result;
}
