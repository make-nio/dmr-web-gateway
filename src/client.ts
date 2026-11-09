import { createSocket, type Socket } from 'node:dgram';
import { createHash } from 'node:crypto';

export type State = 'stopped' | 'login' | 'auth' | 'config' | 'ready' | 'retry';
export function packet(command: string, id: number, payload: Buffer = Buffer.alloc(0)): Buffer {
  const identifier = Buffer.alloc(4);
  identifier.writeUInt32BE(id);
  return Buffer.concat([Buffer.from(command), identifier, payload]);
}
export function digest(salt: Buffer, password: Buffer): Buffer {
  return createHash('sha256').update(salt).update(password).digest();
}
export function configuration(): Buffer {
  const fields: [string, number][] = [['N0CALL',8],['000000000',9],['000000000',9],['01',2],['01',2],['0.000000',8],['00.000000',9],['000',3],['Offline simulator',20],['Headless spike',19],['4',1],['',124],['dmr-web-gateway',40],['simulator',40]];
  return Buffer.from(fields.map(([value,width]) => value.padEnd(width)).join(''), 'ascii');
}
export class Client {
  state: State = 'stopped';
  private socket?: Socket;
  private timer?: NodeJS.Timeout;
  private attempts = 0;
  private awaitingPong = false;
  constructor(private options: {port: number; password: Buffer; id?: number; timeout?: number; ping?: number; retry?: number; log?: (line: string) => void}) {
    if (!Number.isInteger(options.port) || options.port < 1 || options.port > 65535) throw new Error('invalid_port');
    if (!Number.isInteger(options.id ?? 1234567) || (options.id ?? 1234567) < 1 || (options.id ?? 1234567) > 0xffffffff) throw new Error('invalid_id');
    if (!options.password.length || options.password.length > 1024) throw new Error('invalid_password');
  }
  private transition(state: State) {
    this.state = state;
    this.options.log?.(JSON.stringify({event:'state',state}));
  }
  private later(callback: () => void, delay: number) {
    clearTimeout(this.timer);
    this.timer = setTimeout(callback, delay);
  }
  start() {
    if (this.state !== 'stopped' && this.state !== 'retry') return;
    const socket = createSocket('udp4');
    this.socket = socket;
    this.transition('login');
    socket.on('error', () => { if (this.socket === socket) this.reconnect(); });
    socket.on('message', data => { if (this.socket === socket) this.receive(data); });
    socket.connect(this.options.port, '127.0.0.1', () => {
      if (this.socket !== socket) return;
      this.send('RPTL');
      this.later(() => this.reconnect(), this.options.timeout ?? 5000);
    });
  }
  private send(command: string, payload?: Buffer) {
    const socket = this.socket;
    socket?.send(packet(command, this.options.id ?? 1234567, payload), error => { if (error && this.socket === socket && this.state !== 'stopped') this.reconnect(); });
  }
  private receive(data: Buffer) {
    const matches = (command: string) => data.length === command.length + 4 && data.subarray(0,command.length).equals(Buffer.from(command));
    const ownId = data.length >= 4 && data.readUInt32BE(data.length - 4) === (this.options.id ?? 1234567);
    if ((matches('MSTNAK') || matches('MSTCL')) && ownId) return this.reconnect();
    if (matches('RPTACK')) {
      if (this.state === 'login') {
        this.transition('auth');
        this.send('RPTK', digest(data.subarray(6), this.options.password));
      } else if (this.state === 'auth' && ownId) {
        this.transition('config');
        this.send('RPTC', configuration());
      } else if (this.state === 'config' && ownId) {
        this.transition('ready');
        this.attempts = 0;
        this.awaitingPong = false;
        this.later(() => this.ping(), this.options.ping ?? 5000);
        return;
      } else return;
      this.later(() => this.reconnect(), this.options.timeout ?? 5000);
    } else if (matches('MSTPONG') && ownId && this.state === 'ready' && this.awaitingPong) {
      this.awaitingPong = false;
      this.later(() => this.ping(), this.options.ping ?? 5000);
    }
  }
  private ping() {
    this.awaitingPong = true;
    this.send('RPTPING');
    this.later(() => this.reconnect(), this.options.timeout ?? 5000);
  }
  private reconnect() {
    if (this.state === 'retry' || this.state === 'stopped') return;
    this.dispose();
    this.transition('retry');
    this.later(() => this.start(), Math.min(30000, (this.options.retry ?? 1000) * 2 ** Math.min(this.attempts++,5)));
  }
  private dispose() {
    clearTimeout(this.timer);
    const socket = this.socket;
    this.socket = undefined;
    socket?.close();
  }
  stop() {
    if (this.state === 'ready') this.send('RPTCL');
    this.transition('stopped');
    this.dispose();
  }
}
