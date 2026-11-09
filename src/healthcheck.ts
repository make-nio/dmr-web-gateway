import { readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
try {
  const health = JSON.parse(readFileSync(join(tmpdir(),'dmr-health.json'),'utf8'));
  const age = Date.now() - health.time;
  const alive = health.alive === true && typeof health.time === 'number' && age >= 0 && age < 30000;
  process.exitCode = alive && (!process.argv.includes('--ready') || health.ready === true) ? 0 : 1;
} catch { process.exitCode = 1; }
