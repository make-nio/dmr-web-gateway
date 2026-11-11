"""One cross-codec pass per direction. Gate both bitstreams before PCM synthesis."""
import gzip
import json
import math
import struct
import subprocess
import sys
import wave
import zipfile
from pathlib import Path

BANK = Path('/bank')
sys.path.insert(0, str(BANK/'c6'))
from run import LIMIT, OUT, ROOT, convert, sha, stats, write_wav

RUST = Path('/lab/rust-worker/target/release')
WORKER = RUST/'vocoder-spike-worker'


def run(args, data=b''):
    return subprocess.run(args,input=data,capture_output=True,check=True,timeout=120).stdout


def worker(op, data, size, expected):
    assert len(data) == size*1000
    request = ''.join(op+' '+data[i:i+size].hex()+'\n' for i in range(0,len(data),size))
    lines = run([WORKER],request.encode()).decode().splitlines()
    assert len(lines) == 1000
    output = bytearray()
    for i,line in enumerate(lines):
        fields = line.split()
        if len(fields) != 2 or not fields[0].isdigit() or len(fields[1]) != 2*expected:
            raise ValueError(f'{op} invalid reply frame {i}')
        output.extend(bytes.fromhex(fields[1]))
    return bytes(output)


def build():
    deps = RUST/'deps'
    lib, = deps.glob('libblip25_vocoder-*.rlib')
    commands = [
        ['rustc','--edition=2021','-O','-L','dependency='+str(deps),'--extern','blip25_vocoder='+str(lib),
         '/bank/d3b/check.rs','-o','/tmp/check-blip'],
        ['g++','-O3','-std=c++11','-I/lab/opendmr','-I/lab/opendmr/encoder','-I/lab/opendmr/decoder',
         '/bank/d3b/check.cpp',str(ROOT/'libopendmr.a'),'-lm','-o','/tmp/check-open'],
        ['g++','-O3','-std=c++11','-Wall','-fPIC','-I/lab/opendmr',str(ROOT/'dmr_codec.cpp'),
         '/bank/c6/tap.cpp',str(ROOT/'libopendmr.a'),'-Wl,--wrap=mbe_floattoshort','-lm','-o','/tmp/cli-tap']]
    for cmd in commands:
        run(cmd)
    return commands,lib


def verify(route, stream, records):
    left = run(['/tmp/check-open'], stream).decode().splitlines()
    right = run(['/tmp/check-blip'], stream).decode().splitlines()
    assert len(left) == len(right) == 1000
    with (OUT/(route+'-bits.jsonl')).open('w') as log:
        for i,(op,bl) in enumerate(zip(left,right)):
            open49, rebuilt, loop = op.split()
            blip49, errors, equal = bl.split()
            frame = stream[i*9:(i+1)*9].hex()
            ok = (len(open49)==49 and open49==blip49==loop and rebuilt==frame and
                  errors=='0' and equal=='true' and (route!='TX' or open49==records[i]['adaptedInput49']))
            row = dict(i=i,local72=frame,open49=open49,blip49=blip49,
                       blipFecErrors=int(errors),openReencoded=rebuilt,blipReencodeEqual=equal,ok=ok)
            log.write(json.dumps(row)+'\n')
            if not ok:
                raise ValueError(f'Format mismatch: {route} frame {i}, see bit trace')


def kits():
    for listener,order in [('L1',['RX','TX']),('L2',['TX','RX'])]:
        with zipfile.ZipFile(OUT/(listener+'.zip'),'w',zipfile.ZIP_DEFLATED) as z:
            z.write(BANK/'d3b/listener.txt','Instrucciones.txt')
            for i,route in enumerate(order,1):
                z.writestr(f'Pista-{i}.wav',(OUT/(route+'.wav')).read_bytes())


def main():
    c5 = json.loads((BANK/'evidence/c5/manifest.json').read_bytes())
    c6 = json.loads((BANK/'evidence/c6/manifest.json').read_bytes())
    revisions = {}
    for path,expected in [(ROOT,c5['upstream']),(Path('/lab/blip25'),'d1762813b7142c021f4105c832bf7f060d1249fa')]:
        rev = run(['git','-c','safe.directory='+str(path),'-C',path,'rev-parse','HEAD']).decode().strip()
        assert rev == expected
        revisions[path.name] = rev
    with wave.open('/lab/speech.wav','rb') as src:
        assert (src.getnchannels(),src.getsampwidth(),src.getframerate()) == (1,2,8000)
        pcm = src.readframes(160000)
    assert sha(pcm) == c5['inputPcmSha256']
    trace = (BANK/'evidence/c5/frames.jsonl').read_bytes()
    assert sha(trace) == c5['traceSha256']
    rows = [json.loads(line) for line in trace.splitlines()]
    assert [r['i'] for r in rows] == list(range(1000))
    tx = b''.join(bytes.fromhex(r['adapted72']) for r in rows)
    assert sha(tx) == c6['inputFramesSha256']
    commands,lib = build()
    streams = dict(RX=worker('E',pcm,320,9), TX=tx)
    for route,data in streams.items():
        verify(route,data,rows)
    report = dict(revisions=revisions,image=c6['image'],commands=commands,source='Open Speech Repository, OSR_us_000_0010_8k.wav, first 20 s',
                  inputPcmSha256=sha(pcm),inputMetrics=stats(struct.unpack('<160000h',pcm)),
                  c5TraceSha256=sha(trace),keySha256=sha((BANK/'d3b/coordinator.md').read_bytes()),
                  components={str(p):sha(p.read_bytes()) for p in [WORKER,lib,ROOT/'libopendmr.a',BANK/'c6/tap.cpp',
                              BANK/'c5/pack.cpp',BANK/'d3b/check.cpp',BANK/'d3b/check.rs']},routes={})
    for route,data in streams.items():
        true_clips = None
        if route == 'RX':
            Path('/tmp/rx.ambe').write_bytes(data)
            log = run(['/tmp/cli-tap','decode','/tmp/rx.ambe','/tmp/original.raw']).decode().strip()
            floats = struct.unpack('<160000f',Path('/tmp/pre.f32le').read_bytes())
            assert all(map(math.isfinite,floats))
            true_clips = sum(abs(x)>LIMIT for x in floats)
            samples = convert(floats)
            audio = struct.pack('<160000h',*samples)
        else:
            audio = worker('D',data,9,320)
            samples = struct.unpack('<160000h',audio)
            log = '1000 valid 320-byte PCM replies, exit 0'
        assert len(audio)==320000
        wav_hash = write_wav(route+'.wav',audio)
        report['routes'][route] = dict(frames=1000,samples=160000,sampleRate=8000,channels=1,seconds=20,
            errors=0,frameFormatMatches=1000,blipFecErrors=0,decoderLog=log,
            outputMetrics=stats(samples),unityLimitClips=true_clips,
            int16Rails=sum(x in (-32768,32767) for x in samples),pcmSha256=sha(audio),
            bitstreamSha256=sha(data),wavSha256=wav_hash,traceSha256=sha((OUT/(route+'-bits.jsonl')).read_bytes()),
            humanResult='pending')
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    kits()


if __name__=='__main__':
    main()
