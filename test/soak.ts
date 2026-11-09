import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { randomBytes } from 'node:crypto';
import { Client } from '../src/client.js';
const directory = mkdtempSync(join(tmpdir(),'dmr-soak-'));
const secret = join(directory,'password');
const password = randomBytes(32);
writeFileSync(secret,password);
const master = spawn(process.execPath,['dist/src/simulator.js'],{env:{...process.env,DMR_HOTSPOT_PASSWORD_FILE:secret,DMR_MASTER_PORT:'62039'},stdio:'ignore'});
const start = Date.now();
let readySince = 0;
let failures = 0;
const client = new Client({port:62039,password,log:line => {
  const state = JSON.parse(line).state;
  if (state === 'ready') readySince = Date.now();
  if (state === 'retry' && readySince) failures++;
}});
client.start();
const timer = setInterval(() => {
  if (Date.now() - start > 620000 || (readySince && Date.now() - readySince >= 600000)) {
    const success = client.state === 'ready' && failures === 0 && Date.now() - readySince >= 600000;
    console.log(JSON.stringify({test:'600s UDP soak',success,failures,elapsedMs:Date.now()-start}));
    clearInterval(timer); client.stop(); master.kill(); password.fill(0); rmSync(directory,{recursive:true}); process.exitCode = success ? 0 : 1;
  }
},1000);
