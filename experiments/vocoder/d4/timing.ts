import { readFileSync } from "node:fs";
import { configure } from "./config.js";
import { PCM } from "./contract.js";

const pcm = readFileSync("/tmp/d4.s16le");
for (const name of ["opendmr","blip25"]) {
  let nativeNs = 0;
  const session = await configure(name,5000,value => { nativeNs = value; }).createSession();
  const timings = { encode: [] as number[][], decode: [] as number[][] };
  try {
    for (let i = 0; i < 1000; i++) {
      const input = { format: PCM, bytes: pcm.subarray(i*320,(i+1)*320) } as const;
      let t = process.hrtime.bigint();
      const frame = await session.encode(input);
      const encodeNs = Number(process.hrtime.bigint()-t);
      timings.encode.push([nativeNs,encodeNs,encodeNs-nativeNs]);
      t = process.hrtime.bigint();
      await session.decode(frame);
      const decodeNs = Number(process.hrtime.bigint()-t);
      timings.decode.push([nativeNs,decodeNs,decodeNs-nativeNs]);
    }
  } finally { await session.close(); }
  for (const [op,rows] of Object.entries(timings)) {
    const metrics = ["native","roundTrip","outsideNative"].map((label,j) => {
      const values = rows.map(row=>row[j]/1e6).sort((a,b)=>a-b);
      return [label,{p50:values[499],p95:values[949]}];
    });
    console.log(JSON.stringify({name,op,count:rows.length,ms:Object.fromEntries(metrics)}));
  }
}
