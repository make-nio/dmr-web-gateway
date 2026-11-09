import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';

test('file secret and portless healthcheck with real processes', async context => {
  const directory = mkdtempSync(join(tmpdir(),'dmr-process-'));
  const secret = join(directory,'test.secret');
  writeFileSync(secret,'local-marker-only');
  const env = {...process.env,TMP:directory,TEMP:directory,TMPDIR:directory,DMR_HOTSPOT_PASSWORD_FILE:secret,DMR_MASTER_PORT:'62042'};
  const master = spawn(process.execPath,['dist/src/simulator.js'],{env,stdio:'ignore'});
  const gateway = spawn(process.execPath,['dist/src/main.js'],{env,stdio:['ignore','pipe','pipe']});
  let output = '';
  gateway.stdout.on('data',data => {output += data.toString();});
  gateway.stderr.on('data',data => {output += data.toString();});
  context.after(async () => {
    const exited = Promise.all([master,gateway].map(child => child.exitCode !== null ? Promise.resolve() : new Promise(resolve => child.once('exit',resolve))));
    gateway.kill(); master.kill(); await exited;
    rmSync(directory,{recursive:true,force:true});
  });
  let healthy = false;
  for (let attempt = 0; attempt < 50; attempt++) {
    await delay(100);
    if (existsSync(join(directory,'dmr-health.json')) && spawnSync(process.execPath,['dist/src/healthcheck.js'],{env}).status === 0) {healthy = true;break;}
  }
  assert.ok(healthy);
  assert.ok(!output.includes('local-marker-only'));
  writeFileSync(join(directory,'dmr-health.json'),JSON.stringify({ready:true,time:0}));
  assert.equal(spawnSync(process.execPath,['dist/src/healthcheck.js'],{env}).status,1);
});
test('startup errors never echo environment paths or values', () => {
  const result = spawnSync(process.execPath,['dist/src/main.js'],{env:{...process.env,DMR_HOTSPOT_PASSWORD_FILE:'private-marker-missing-file'},encoding:'utf8'});
  assert.equal(result.status,1);
  assert.equal(result.stderr.trim(),'{"event":"startup_failed"}');
});
