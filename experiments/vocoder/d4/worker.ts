import { spawn } from "node:child_process";
import { VocoderError, type Engine } from "./contract.js";

export async function worker(file: string, args: string[], timeoutMs: number,
                             observeNativeNs?: (ns: number) => void): Promise<Engine> {
  const child = spawn(file, args, { stdio: ["pipe", "pipe", "ignore"], windowsHide: true });
  const exited = new Promise<void>(resolve => child.once("close", () => resolve()));
  let failure: VocoderError | undefined;
  let pending: { length: number; resolve: (bytes: Buffer) => void; reject: (error: Error) => void } | undefined;
  let buffer = "";
  function fail(error: VocoderError) {
    failure ??= error;
    pending?.reject(failure);
    pending = undefined;
    if (child.pid && child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
  }
  child.on("error", () => fail(new VocoderError("WORKER", "worker process unavailable")));
  child.stdin.on("error", () => fail(new VocoderError("WORKER", "worker input closed")));
  child.stdout.on("error", () => fail(new VocoderError("WORKER", "worker output closed")));
  child.on("close", () => fail(new VocoderError("WORKER", "worker exited")));
  child.stdout.setEncoding("utf8").on("data", (part: string) => {
    buffer += part;
    if (!pending || buffer.length > 680) {
      fail(new VocoderError("PROTOCOL", "unexpected or oversized reply"));
      return;
    }
    if (!buffer.includes("\n")) return;
    const line = /^(\d{1,20}) ([a-fA-F0-9]+)\r?\n$/.exec(buffer);
    if (!line || line[0] !== buffer || line[2].length !== pending.length * 2) {
      fail(new VocoderError("PROTOCOL", "invalid worker reply"));
      return;
    }
    const request = pending;
    pending = undefined;
    buffer = "";
    observeNativeNs?.(Number(line[1]));
    request.resolve(Buffer.from(line[2], "hex"));
  });
  await new Promise<void>((resolve, reject) => {
    child.once("spawn", resolve);
    child.once("error", () => reject(new VocoderError("WORKER", "could not start worker")));
  });
  return {
    async exchange(op, bytes) {
      if (failure) throw failure;
      let timer: NodeJS.Timeout | undefined;
      try {
        return await new Promise<Buffer>((resolve, reject) => {
          pending = { length: op === "E" ? 9 : 320, resolve, reject };
          timer = setTimeout(() => fail(new VocoderError("TIMEOUT", "worker reply deadline exceeded")), timeoutMs);
          child.stdin.write(op + " " + bytes.toString("hex") + "\n");
        });
      } finally { clearTimeout(timer); }
    },
    async stop() {
      if (child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
      await exited;
    }
  };
}
