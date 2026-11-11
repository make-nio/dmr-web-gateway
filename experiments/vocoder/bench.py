import argparse
import hashlib
import json
import math
import os
import platform
import random
import selectors
import struct
import subprocess
import time
import wave
from pathlib import Path

OUT = Path('/results')
COMMANDS = {'opendmr':['/lab/opendmr-worker'], 'blip25':['/lab/rust-worker/target/release/vocoder-spike-worker']}

class Worker:
    def __init__(self, name):
        self.name = name
        self.proc = subprocess.Popen(COMMANDS[name],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(OUT/(name+'.stderr'),'ab'),bufsize=0)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.proc.stdout,selectors.EVENT_READ)
    def request(self, operation, payload=b''):
        started = time.perf_counter_ns()
        self.proc.stdin.write((operation+(' '+payload.hex() if operation!='R' else '')+'\n').encode())
        if not self.selector.select(5):
            raise TimeoutError(self.name)
        response = self.proc.stdout.readline().decode().strip()
        elapsed = time.perf_counter_ns()-started
        if response == 'ERR':
            raise ValueError('worker rejected frame')
        nanos, _, value = response.partition(' ')
        result = bytes.fromhex(value)
        expected = {'E':9,'D':320,'R':0}[operation]
        assert len(result) == expected, (self.name,operation,len(result))
        return result,int(nanos),elapsed
    def close(self):
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill(); self.proc.wait()
        self.selector.close()
    def resource(self):
        status = Path(f'/proc/{self.proc.pid}/status').read_text()
        rss = int(next(line.split()[1] for line in status.splitlines() if line.startswith('VmRSS:')))*1024
        fields = Path(f'/proc/{self.proc.pid}/stat').read_text().split()
        cpu = (int(fields[13])+int(fields[14]))/os.sysconf('SC_CLK_TCK')
        return {'rssBytes':rss,'cpuSeconds':cpu}

def stats(values):
    ordered=sorted(values)
    return {'count':len(values), 'p50Ms':ordered[int((len(ordered)-1)*.5)]/1e6,'p95Ms':ordered[int((len(ordered)-1)*.95)]/1e6,'p99Ms':ordered[int((len(ordered)-1)*.99)]/1e6,'maxMs':ordered[-1]/1e6}

def wav(name,data):
    with wave.open(str(OUT/name),'wb') as output:
        output.setparams((1,2,8000,0,'NONE','not compressed'));output.writeframes(data)

def quality(data):
    samples=struct.unpack('<'+'h'*(len(data)//2),data)
    return {'rms':math.sqrt(sum(value*value for value in samples)/len(samples)), 'dc':sum(samples)/len(samples), 'clippedFraction':sum(abs(value)>=32767 for value in samples)/len(samples),'zeroFraction':samples.count(0)/len(samples)}

def corpus():
    with wave.open('/lab/speech.wav','rb') as source:
        assert (source.getnchannels(),source.getsampwidth(),source.getframerate())==(1,2,8000)
        speech=source.readframes(8000*20)
    rng=random.Random(20261109)
    tone=struct.pack('<8000h',*[round(6000*math.sin(2*math.pi*440*index/8000)) for index in range(8000)])
    noise=struct.pack('<8000h',*[rng.randint(-2000,2000) for _ in range(8000)])
    return {'silence':bytes(16000),'tone':tone,'noise':noise,'speech':speech}

def main():
    args=argparse.ArgumentParser();args.add_argument('--soak',type=int,default=600);duration=args.parse_args().soak
    OUT.mkdir(exist_ok=True)
    sources=corpus()
    report={'environment':{'platform':platform.platform(),'machine':platform.machine(),'cpu':Path('/proc/cpuinfo').read_text().split('model name')[1].split('\n')[0].strip(),'python':platform.python_version()},'corpus':{'source':'Open Speech Repository','url':'https://www.voiptroubleshooter.com/open_speech/american/OSR_us_000_0010_8k.wav','sha256':hashlib.sha256(Path('/lab/speech.wav').read_bytes()).hexdigest()},'functional':{},'throughput':{},'soak':{},'omitted':['Independent DVSI/DMR reference vectors unavailable; no interoperability certification','Human listening not yet performed; no MOS','No patent clearance or redistribution authorization','No sanitizer run in this baseline experiment']}
    workers={name:Worker(name) for name in COMMANDS}
    try:
        for name,worker in workers.items():
            for operation,bad in [('E',b''),('E',bytes(319)),('D',bytes(8)),('D',bytes(10))]:
                try:
                    worker.request(operation,bad)
                    raise AssertionError('invalid length accepted')
                except ValueError: pass
            for source,pcm in sources.items():
                worker.request('R')
                frames=[worker.request('E',pcm[offset:offset+320])[0] for offset in range(0,len(pcm)-319,320)]
                for receiver,decoder in workers.items():
                    decoder.request('R')
                    decoded=b''.join(decoder.request('D',frame)[0] for frame in frames)
                    key=f'{name}-to-{receiver}-{source}'
                    report['functional'][key]={'frames':len(frames),'outputBytes':len(decoded),'signal':quality(decoded)}
                    if source=='speech': wav(key+'.wav',decoded)
        wav('original-speech.wav',sources['speech'])
        frame=sources['speech'][32000:32320]
        for name,worker in workers.items():
            worker.request('R')
            for _ in range(100): worker.request('D',worker.request('E',frame)[0])
            measurements={key:[] for key in ['encodeCodec','decodeCodec','encodeIPC','decodeIPC']}
            started=time.monotonic()
            for _ in range(1000):
                encoded,codec,ipc=worker.request('E',frame);measurements['encodeCodec'].append(codec);measurements['encodeIPC'].append(ipc)
                _,codec,ipc=worker.request('D',encoded);measurements['decodeCodec'].append(codec);measurements['decodeIPC'].append(ipc)
            elapsed=time.monotonic()-started
            report['throughput'][name]={'roundtripFramesPerSecond':1000/elapsed,**{key:stats(values) for key,values in measurements.items()}}
        print(json.dumps({'event':'functional_and_throughput_done','throughput':report['throughput']}),flush=True)
        if duration:
            measurements={name:{key:[] for key in ['encodeCodec','decodeCodec','encodeIPC','decodeIPC','queueDelay','scheduledRoundtrip']} for name in workers}
            samples=[]
            for worker in workers.values(): worker.request('R')
            baseline={name:worker.resource() for name,worker in workers.items()}
            started=time.monotonic();frame_index=0; deadline_misses={name:0 for name in workers}
            sequence=b''.join(sources.values())
            with open(OUT/'samples.jsonl','w') as sample_file:
                while frame_index < duration*50 or time.monotonic()-started < duration:
                    due=started+frame_index*.020
                    time.sleep(max(0,due-time.monotonic()))
                    offset=(frame_index%(len(sequence)//320))*320
                    payload=sequence[offset:offset+320]
                    order=list(workers.items())
                    if frame_index%2: order.reverse()
                    for name,worker in order:
                        queue=int(max(0,time.monotonic()-due)*1e9)
                        encoded,codec,ipc=worker.request('E',payload)
                        measurements[name]['encodeCodec'].append(codec);measurements[name]['encodeIPC'].append(ipc)
                        _,codec,ipc=worker.request('D',encoded)
                        measurements[name]['decodeCodec'].append(codec);measurements[name]['decodeIPC'].append(ipc)
                        scheduled=int((time.monotonic()-due)*1e9)
                        measurements[name]['queueDelay'].append(queue);measurements[name]['scheduledRoundtrip'].append(scheduled)
                        if scheduled>20000000: deadline_misses[name]+=1
                    if frame_index%250==0:
                        sample={'seconds':time.monotonic()-started,**{name:worker.resource() for name,worker in workers.items()}}
                        samples.append(sample);sample_file.write(json.dumps(sample)+'\n');sample_file.flush()
                        if frame_index%2500==0: print(json.dumps({'event':'soak_progress','seconds':round(sample['seconds'],2),'framesEach':frame_index+1}),flush=True)
                    frame_index+=1
                elapsed=time.monotonic()-started
            for name,worker in workers.items():
                final=worker.resource()
                report['soak'][name]={'elapsedSeconds':elapsed,'framesPerDirection':frame_index,'failures':0,'deadlineMisses':deadline_misses[name],'cpuPercentOneCore':100*(final['cpuSeconds']-baseline[name]['cpuSeconds'])/elapsed,'peakSampledRssMiB':max(sample[name]['rssBytes'] for sample in samples)/1048576,'initialRssBytes':baseline[name]['rssBytes'],'finalRssBytes':final['rssBytes'],**{key:stats(values) for key,values in measurements[name].items()}}
        report['completed']=True
    except Exception as error:
        report['completed']=False;report['failure']=repr(error)
        raise
    finally:
        (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
        for worker in workers.values(): worker.close()
    print(json.dumps({'event':'complete','completed':report['completed'],'soak':report['soak']}),flush=True)

if __name__=='__main__': main()
