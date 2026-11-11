import { provider, type VocoderProvider } from "./contract.js";
import { simulated } from "./simulated.js";
import { worker } from "./worker.js";

export function configure(name: string, timeoutMs = 5000, observeNativeNs?: (ns: number) => void): VocoderProvider {
  if (!Number.isSafeInteger(timeoutMs) || timeoutMs <= 0 || timeoutMs > 2147483647)
    throw new RangeError("invalid timeoutMs");
  switch (name) {
    case "simulated": return provider(simulated);
    case "opendmr": return provider(() => worker("/tmp/d4-open", [], timeoutMs, observeNativeNs));
    case "blip25": return provider(() => worker("/lab/rust-worker/target/release/vocoder-spike-worker", [], timeoutMs, observeNativeNs));
    default: throw new RangeError("unknown provider: " + name);
  }
}
