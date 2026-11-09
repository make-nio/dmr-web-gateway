import { readFileSync, writeFileSync, renameSync } from 'node:fs';
import { Client } from './client.js';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

try {
  if (process.env.DMR_MASTER_HOST && process.env.DMR_MASTER_HOST !== '127.0.0.1') throw new Error('offline_only');
  const password = readFileSync(process.env.DMR_HOTSPOT_PASSWORD_FILE ?? '/run/secrets/dmr_password');
  const client = new Client({port: Number(process.env.DMR_MASTER_PORT ?? 62031), password, log: line => console.log(line)});
  const heartbeat = () => {
    try {
      const path = join(tmpdir(),'dmr-health.json');
      writeFileSync(path + '.new', JSON.stringify({ready:client.state === 'ready',time:Date.now()}));
      renameSync(path + '.new',path);
    }
    catch { console.error(JSON.stringify({event:'health_write_failed'})); clearInterval(timer); client.stop(); process.exitCode = 1; }
  };
  const timer = setInterval(heartbeat, 1000);
  client.start();
  for (const signal of ['SIGINT','SIGTERM']) process.on(signal, () => { clearInterval(timer); client.stop(); password.fill(0); heartbeat(); });
} catch {
  console.error(JSON.stringify({event:'startup_failed'}));
  process.exitCode = 1;
}
