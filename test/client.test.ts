import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createSocket } from 'node:dgram';
import { createHash } from 'node:crypto';
import { setTimeout as delay } from 'node:timers/promises';
import { Client, packet, configuration, digest } from '../src/client.js';

const password = Buffer.from('offline-fixture-only');
test('immediate stop during asynchronous connect is safe and idempotent', async () => {
  const client = new Client({port:62048,password});
  client.start();
  client.stop();
  client.stop();
  await delay(30);
  assert.equal(client.state,'stopped');
});
async function until(predicate: () => boolean, timeout = 3000) {
  const deadline = Date.now() + timeout;
  while (!predicate()) { assert.ok(Date.now() < deadline, 'condition timed out'); await delay(10); }
}
test('wire fixtures, big endian id, fixed config widths and SHA256', () => {
  assert.equal(packet('RPTL',1234567).toString('hex'),'5250544c0012d687');
  assert.equal(configuration().length,294);
  assert.equal(configuration().subarray(0,8).toString(),'N0CALL  ');
  assert.equal(configuration().subarray(8,30).toString(),'0000000000000000000101');
  assert.equal(configuration().subarray(30,50).toString(),'0.00000000.000000000');
  assert.equal(configuration()[89],52);
  assert.equal(packet('RPTC',1234567,configuration()).length,302);
  assert.equal(digest(Buffer.from('ab'),Buffer.from('c')).toString('hex'),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
  assert.throws(() => new Client({port:0,password}));
  for (const value of [0,-1,NaN,Infinity,0.5,30001]) assert.throws(() => new Client({port:62031,password,timeout:value}));
});
test('UDP handshake, invalid frames, ping loss, reconnect, master close, NAK and client close; safe logs', async context => {
  const master = createSocket('udp4');
  await new Promise<void>(resolve => master.bind(0,'127.0.0.1',resolve));
  const events: string[] = [];
  const logs: string[] = [];
  let dropPong = false;
  let peerPort = 0;
  let logins = 0;
  const id = 1234567;
  const salt = Buffer.from('01020304','hex');
  master.on('message',(data, peer) => {
    peerPort = peer.port;
    const command = data.subarray(0,4).toString();
    events.push(data.subarray(0,7).toString());
    const reply = (value: Buffer) => master.send(value,peer.port,peer.address);
    if (command === 'RPTL') {
      assert.equal(data.length,8);
      logins++;
      reply(Buffer.from('RPTACK'));
      reply(Buffer.concat([Buffer.from('RPTACK'),salt]));
    } else if (command === 'RPTK') {
      assert.equal(data.length,40);
      assert.deepEqual(data.subarray(8),createHash('sha256').update(salt).update(password).digest());
      reply(packet('RPTACK',id));
    } else if (data.length === 302 && command === 'RPTC') {
      assert.equal(data.subarray(8,16).toString(),'N0CALL  ');
      reply(packet('RPTACK',id));
    } else if (data.subarray(0,7).toString() === 'RPTPING' && !dropPong) reply(packet('MSTPONG',id));
  });
  const client = new Client({port:master.address().port,password,timeout:100,ping:30,retry:20,log:line => logs.push(line)});
  context.after(() => {client.stop(); master.close();});
  client.start();
  await until(() => client.state === 'ready');
  master.send(Buffer.concat([Buffer.from('MSTNAK'),password]),peerPort,'127.0.0.1');
  master.send(packet('MSTCL',999),peerPort,'127.0.0.1');
  const stranger = createSocket('udp4');
  stranger.send(packet('MSTCL',id),peerPort,'127.0.0.1',() => stranger.close());
  for (const size of [0,1,5,9,11,512]) master.send(Buffer.alloc(size,65),peerPort,'127.0.0.1');
  await delay(70);
  assert.equal(client.state,'ready');
  dropPong = true;
  await until(() => logins >= 2);
  dropPong = false;
  await until(() => client.state === 'ready');
  master.send(packet('MSTCL',id),peerPort,'127.0.0.1');
  await until(() => logins >= 3 && client.state === 'ready');
  master.send(packet('MSTNAK',id),peerPort,'127.0.0.1');
  await until(() => logins >= 4 && client.state === 'ready');
  client.stop();
  await until(() => events.some(value => value.startsWith('RPTCL')));
  const stoppedLogins = logins;
  await delay(150);
  assert.equal(logins,stoppedLogins);
  assert.equal(client.state,'stopped');
  assert.ok(!logs.join('').includes(password.toString()));
  assert.ok(logs.every(line => Object.keys(JSON.parse(line)).join(',') === 'event,state'));
});
for (const phase of ['login','auth','config']) test(`timeout in ${phase} reconnects`, async context => {
  const master = createSocket('udp4');
  await new Promise<void>(resolve => master.bind(0,'127.0.0.1',resolve));
  let logins = 0;
  master.on('message',(data,peer) => {
    const command = data.subarray(0,4).toString();
    if (command === 'RPTL') { logins++; if (phase !== 'login') master.send(packet('RPTACK',1234567),peer.port,peer.address); }
    if (command === 'RPTK' && phase === 'config') master.send(packet('RPTACK',1234567),peer.port,peer.address);
  });
  const client = new Client({port:master.address().port,password,timeout:40,retry:10});
  context.after(() => {client.stop();master.close();});
  client.start();
  await until(() => logins >= 2);
});
