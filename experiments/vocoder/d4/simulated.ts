import { createHash } from "node:crypto";
import type { Engine } from "./contract.js";

// Deterministic fixture engine. Encode and decode keep independent histories.
export async function simulated(): Promise<Engine> {
  const history = { E: Buffer.alloc(32), D: Buffer.alloc(32) };
  return {
    async exchange(op, bytes) {
      const digest = createHash("sha256").update(op).update(history[op]).update(bytes).digest();
      history[op] = digest;
      return op === "E" ? digest.subarray(0, 9) : Buffer.concat(Array(10).fill(digest));
    },
    async stop() {}
  };
}
