import { configure } from "./config.js";
import { PCM } from "./contract.js";
import { readFileSync } from "node:fs";

// One request per frame. Write concatenated local 72-bit frames to stdout.
const pcm = readFileSync(process.argv[2]);
if (pcm.length % 320 !== 0) throw new RangeError("partial input frame");
const session = await configure(process.env.VOCODER_PROVIDER ?? "simulated").createSession();
try {
  for (let pos = 0; pos < pcm.length; pos += 320) {
    const frame = await session.encode({ format: PCM, bytes: pcm.subarray(pos, pos + 320) });
    await new Promise<void>((resolve, reject) =>
      process.stdout.write(frame.bytes, err => err ? reject(err) : resolve()));
  }
} finally { await session.close(); }
