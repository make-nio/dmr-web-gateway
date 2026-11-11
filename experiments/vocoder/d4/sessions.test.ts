import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { configure } from "./config.js";
import { PCM, LOCAL, provider, type Pcm, type VocoderSession } from "./contract.js";
import { worker } from "./worker.js";

const input = (byte: number) => ({ format: PCM, bytes: Buffer.alloc(320, byte) } as const);
const channel = (byte: number) => ({ format: LOCAL, bytes: Buffer.alloc(9, byte) } as const);
const hex = (value: Uint8Array) => Buffer.from(value).toString("hex");
const hash = (value: Buffer) => createHash("sha256").update(value).digest("hex");

test("simulated golden first encode/decode and strict selection", async () => {
  const session = await configure("simulated").createSession();
  try {
    assert.equal(hex((await session.encode(input(0))).bytes), "355e9c91c572ed050f");
    assert.equal(hex((await session.decode(channel(0))).bytes),
      "35a7e0f8a31762cce7db52c6cc834e60b4e1340dc1bcc7cf6333cdd1e8bd0e94".repeat(10));
    assert.throws(() => configure("unknown"));
    assert.throws(() => configure("blip25", 0));
  } finally { await session.close(); }
});

const names = process.env.D4_NATIVE === "1" ? ["simulated","opendmr","blip25"] : ["simulated"];

for (const name of names) {
  test(name + ": interleaved streams match isolated streams before/after reset", async () => {
    const factory = configure(name);
    const sessions: VocoderSession[] = [];
    async function step(session: VocoderSession, byte: number) {
      const frame = await session.encode(input(byte));
      const pcm = await session.decode(frame);
      return [hex(frame.bytes), hex(pcm.bytes)];
    }
    async function series(session: VocoderSession, seed: number) {
      const result = [];
      for (let i=0; i<12; i++) result.push(await step(session,seed+i));
      return result;
    }
    try {
      for (let i=0; i<3; i++) sessions.push(await factory.createSession());
      const [oracle, a, b] = sessions;
      const first = await series(oracle, 10);
      await oracle.reset();
      const second = await series(oracle, 50);
      assert.notDeepEqual(first,second);
      for (let i=0; i<12; i++) {
        const pair = await Promise.all([step(a,10+i),step(b,50+i)]);
        assert.deepEqual(pair,[first[i],second[i]]);
        if (i===4) {
          await a.reset();
          for (let j=0;j<=4;j++) assert.deepEqual(await step(a,10+j),first[j]);
        }
      }
      await a.close();
      await a.close();
      await assert.rejects(a.encode(input(1)),{code:"CLOSED"});
      await assert.rejects(a.reset(),{code:"CLOSED"});
      await b.reset();
      assert.deepEqual(await step(b,50),second[0]);
    } finally { await Promise.all(sessions.map(s=>s.close())); }
  });

  test(name + ": invalid frames preserve state; overlapping calls rejected", async () => {
    const session = await configure(name).createSession();
    try {
      const baseline = await session.encode(input(42));
      await session.reset();
      for (const size of [0,319,321]) {
        await assert.rejects(session.encode({format:PCM,bytes:Buffer.alloc(size)}),{code:"FORMAT"});
      }
      for (const size of [7,8,10]) {
        await assert.rejects(session.decode({format:LOCAL,bytes:Buffer.alloc(size)}),{code:"FORMAT"});
      }
      await assert.rejects(session.encode({format:"pcm-be",bytes:Buffer.alloc(320)} as unknown as Pcm),{code:"FORMAT"});
      await assert.rejects(session.decode({format:"dmr-interleaved",bytes:Buffer.alloc(9)} as never),{code:"FORMAT"});
      const pending = session.encode(input(42));
      const checks = [session.encode(input(1)),session.reset(),session.close()]
        .map(p=>assert.rejects(p,{code:"BUSY"}));
      assert.deepEqual(await pending,baseline);
      await Promise.all(checks);
    } finally { await session.close(); }
  });
}

for (const [label, action, code] of [
  ["timeout","setInterval(()=>{},10000)", "TIMEOUT"],
  ["crash","process.exit(19)", "WORKER"],
  ["bad reply","process.stdout.write('1 00\\n')", "PROTOCOL"]
]) {
  test("IPC "+label+" terminates only affected session", async () => {
    const behavior = "process.stdin.on('data',chunk=>{if(chunk.toString().startsWith('E 01')){"
      +action+"}else{process.stdout.write('0 '+'00'.repeat(9)+'\\n')}})";
    const factory = provider(()=>worker(process.execPath,["-e",behavior],label==="timeout"?500:5000));
    const dead = await factory.createSession();
    const healthy = await factory.createSession();
    try {
      await assert.rejects(dead.encode(input(1)),{code});
      await assert.rejects(dead.decode(channel(1)),{code:"CLOSED"});
      assert.equal((await healthy.encode(input(0))).bytes.length,9);
    } finally { await Promise.all([dead.close(),healthy.close()]); }
  });
}

if (process.env.D4_NATIVE==="1") {
  const evidence = "/repo/experiments/vocoder/evidence/d3b/";
  const manifest = JSON.parse(readFileSync(evidence+"manifest.json","utf8"));
  for (const [encoder,decoder,route] of [["blip25","opendmr","RX"],["opendmr","blip25","TX"]]) {
    test(route+": full D3b golden via configured providers",async () => {
      const pcm = readFileSync("/tmp/d4.s16le");
      const reference = manifest.routes[route];
      const enc = await configure(encoder).createSession();
      const dec = await configure(decoder).createSession();
      const encoded = [], decoded = [];
      try {
        for (let i=0;i<1000;i++) {
          const f = await enc.encode({format:PCM,bytes:pcm.subarray(i*320,(i+1)*320)});
          encoded.push(f.bytes);
          decoded.push((await dec.decode(f)).bytes);
        }
        assert.equal(hash(Buffer.concat(encoded)),reference.bitstreamSha256);
        assert.equal(hash(Buffer.concat(decoded)),reference.pcmSha256);
      } finally { await Promise.all([enc.close(),dec.close()]); }
    });
  }
}
