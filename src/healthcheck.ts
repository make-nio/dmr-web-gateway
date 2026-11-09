import { readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
try {
  const health = JSON.parse(readFileSync(join(tmpdir(),'dmr-health.json'),'utf8'));
  const age = Date.now() - health.time;
  process.exitCode = health.ready === true && age >= 0 && age < 5000 ? 0 : 1;
} catch { process.exitCode = 1; }
