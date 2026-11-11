export const PCM = "pcm-s16le-mono-8000-160" as const;
export const LOCAL = "ambe-local-msb-A24-B23-C25" as const;
export type Packet<F extends string> = Readonly<{ format: F; bytes: Uint8Array }>;
export type Pcm = Packet<typeof PCM>;
export type Frame = Packet<typeof LOCAL>;

export interface VocoderSession {
  encode(pcm: Pcm): Promise<Frame>;
  decode(frame: Frame): Promise<Pcm>;
  reset(): Promise<void>;
  close(): Promise<void>;
}

export interface VocoderProvider {
  createSession(): Promise<VocoderSession>;
}

export class VocoderError extends Error {
  constructor(readonly code: "FORMAT" | "BUSY" | "CLOSED" | "TIMEOUT" | "WORKER" | "PROTOCOL", message: string) {
    super(message);
  }
}

export interface Engine {
  exchange(op: "E" | "D", input: Buffer): Promise<Buffer>;
  stop(): Promise<void>;
}

export type Start = () => Promise<Engine>;

export function provider(start: Start): VocoderProvider {
  return { async createSession() {
    let engine = await start();
    let closed = false;
    let busy = false;
    let closing: Promise<void> | undefined;

    async function exclusive<T>(action: () => Promise<T>): Promise<T> {
      if (closed) throw new VocoderError("CLOSED", "session closed");
      if (busy) throw new VocoderError("BUSY", "operation already in progress");
      busy = true;
      try { return await action(); } finally { busy = false; }
    }

    function exchange(op: "E" | "D", packet: Frame | Pcm) {
      return exclusive(async () => {
        const encode = op === "E";
        if (packet?.format !== (encode ? PCM : LOCAL) || !(packet.bytes instanceof Uint8Array)
            || packet.bytes.length !== (encode ? 320 : 9)) {
          throw new VocoderError("FORMAT", "invalid format or byte count");
        }
        try {
          const bytes = await engine.exchange(op, Buffer.from(packet.bytes));
          if (bytes.length !== (encode ? 9 : 320)) throw new VocoderError("PROTOCOL", "invalid reply length");
          return bytes;
        } catch (error) {
          closed = true;
          await engine.stop();
          throw error;
        }
      });
    }
    return {
      async encode(packet) { return { format: LOCAL, bytes: await exchange("E", packet) }; },
      async decode(packet) { return { format: PCM, bytes: await exchange("D", packet) }; },
      reset() { return exclusive(async () => {
        try { await engine.stop(); engine = await start(); }
        catch (error) { closed = true; throw error; }
      }); },
      async close() {
        if (closing) return closing;
        if (busy) throw new VocoderError("BUSY", "finish pending operation before close");
        closed = true;
        closing = engine.stop();
        return closing;
      }
    };
  }};
}
