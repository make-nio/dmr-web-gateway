import { createSocket } from 'node:dgram';
import { randomBytes, timingSafeEqual } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { digest, packet } from './client.js';

let password: Buffer;
try { password = readFileSync(process.env.DMR_HOTSPOT_PASSWORD_FILE ?? '/run/secrets/dmr_password'); }
catch { console.error(JSON.stringify({event:'simulator_startup_failed'})); process.exit(1); }
const master = createSocket('udp4');
master.on('error', () => {console.error(JSON.stringify({event:'simulator_socket_failed'}));master.close();process.exitCode = 1;});
const peers = new Map<number,{id:number;salt:Buffer;phase:string}>();
master.on('message',(data,peer) => {
  if (peer.address !== '127.0.0.1' || data.length < 8) return;
  const command = data.subarray(0,4).toString();
  const reply = (value:Buffer) => master.send(value,peer.port,peer.address);
  if (command === 'RPTL' && data.length === 8) {
    if (peers.size >= 100) peers.clear();
    const entry = {id:data.readUInt32BE(4),salt:randomBytes(4),phase:'auth'};
    peers.set(peer.port,entry);
    reply(Buffer.concat([Buffer.from('RPTACK'),entry.salt]));
    return;
  }
  const entry = peers.get(peer.port);
  if (!entry) return;
  if (command === 'RPTK' && data.length === 40 && entry.phase === 'auth' && data.readUInt32BE(4) === entry.id) {
    if (!timingSafeEqual(data.subarray(8),digest(entry.salt,password))) { reply(packet('MSTNAK',entry.id)); peers.delete(peer.port); return; }
    entry.phase = 'config';
    reply(packet('RPTACK',entry.id));
  } else if (command === 'RPTC' && data.length === 302 && entry.phase === 'config' && data.readUInt32BE(4) === entry.id) {
    entry.phase = 'ready'; reply(packet('RPTACK',entry.id));
  } else if (data.equals(packet('RPTPING',entry.id)) && entry.phase === 'ready') reply(packet('MSTPONG',entry.id));
  else if (data.equals(packet('RPTCL',entry.id))) peers.delete(peer.port);
});
master.bind(Number(process.env.DMR_MASTER_PORT ?? 62031),'127.0.0.1');
for (const signal of ['SIGINT','SIGTERM']) process.on(signal,() => {master.close();password.fill(0);});
