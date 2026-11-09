import { readFileSync } from 'node:fs';
import { Client } from './client.js';

try {
  const password = readFileSync(process.env.DMR_HOTSPOT_PASSWORD_FILE ?? '/run/secrets/dmr_password');
  const client = new Client({
    port: Number(process.env.DMR_MASTER_PORT ?? 62031), password,
    log: line => {
      if (JSON.parse(line).state === 'ready') setImmediate(() => {
        clearTimeout(deadline);
        client.stop();
        password.fill(0);
        process.exitCode = 0;
      });
    }
  });
  const deadline = setTimeout(() => {client.stop(); password.fill(0); process.exitCode = 1;},2000);
  client.start();
} catch { process.exitCode = 1; }
