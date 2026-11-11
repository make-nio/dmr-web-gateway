"""Replay D3b on a single approved 20-second Rioplatense passage."""
import json
import math
import struct
import sys
import wave
from pathlib import Path

sys.path.insert(0, '/bank/d3b')
from experiment import BANK, OUT, ROOT, WORKER, LIMIT, build, convert, run, sha, stats, verify, worker, write_wav


def main():
    base = json.loads((BANK/'evidence/d3b/manifest.json').read_bytes())
    c5 = json.loads((BANK/'evidence/c5/manifest.json').read_bytes())
    for path, key in [(ROOT,'opendmr'),(Path('/lab/blip25'),'blip25')]:
        revision = run(['git','-c','safe.directory='+str(path),'-C',path,'rev-parse','HEAD']).decode().strip()
        assert revision == base['revisions'][key]
    for path, digest in base['components'].items():
        assert sha(Path(path).read_bytes()) == digest
    with wave.open('/input.wav','rb') as src:
        assert (src.getnchannels(),src.getsampwidth(),src.getframerate(),src.getnframes()) == (1,2,8000,160000)
        pcm = src.readframes(160000)
    commands,_ = build()
    cmd = ['g++','-O3','-std=c++11','-I/lab/opendmr','-I/lab/opendmr/encoder','-I/lab/opendmr/decoder',
           '/bank/c5/pack.cpp',str(ROOT/'libopendmr.a'),'-lm','-o','/tmp/enc']
    run(cmd)
    positions = [i for row in c5['destinationsMSBFirst'] for i in row]
    Path('/tmp/layout').write_text(' '.join(map(str,positions)))
    records, tx = [], bytearray()
    for line in run(['/tmp/enc'],pcm).decode().splitlines():
        *_, adapted, control72, control49, frame, recovered = line.split()
        assert recovered == adapted
        records.append({'adaptedInput49':adapted})
        tx.extend(bytes.fromhex(frame))
    assert len(records)==1000 and len(tx)==9000
    streams = dict(RX=worker('E',pcm,320,9),TX=bytes(tx))
    for route,data in streams.items():
        verify(route,data,records)
    manifest = dict(source='Es-Rosario (Argentina) Parte 1-article.ogg',reader='Gabriel Quagliano',
                    license='CC BY-SA 3.0',sourceSha256='3dc79a7f99002ec5a922aa89f91da486d0a7a00e740795e8fb0e6c7dfd7b0165',
                    intervalSeconds=[15,35],sourceWavSha256=sha(Path('/input.wav').read_bytes()),
                    inputPcmSha256=sha(pcm),inputMetrics=stats(struct.unpack('<160000h',pcm)),
                    revisions=base['revisions'],image=base['image'],builds=commands+[cmd],routes={})
    for route,name in [('RX','Rosario-01.wav'),('TX','Rosario-02.wav')]:
        data=streams[route]
        clips=None
        if route=='RX':
            Path('/tmp/rx.ambe').write_bytes(data)
            run(['/tmp/cli-tap','decode','/tmp/rx.ambe','/tmp/raw'])
            pre=struct.unpack('<160000f',Path('/tmp/pre.f32le').read_bytes())
            assert all(map(math.isfinite,pre))
            clips=sum(abs(x)>LIMIT for x in pre)
            samples=convert(pre)
            audio=struct.pack('<160000h',*samples)
        else:
            audio=worker('D',data,9,320)
            samples=struct.unpack('<160000h',audio)
        manifest['routes'][route]=dict(wav=name,wavSha256=write_wav(name,audio),
            framesSha256=sha(data),outputPcmSha256=sha(audio),traceSha256=sha((OUT/(route+'-bits.jsonl')).read_bytes()),
            frames=1000,sampleRate=8000,channels=1,samples=len(samples),durationSeconds=20,
            formatMatches=1000,blipFecErrors=0,executionErrors=0,outputMetrics=stats(samples),
            outputInt16Rails=sum(x in (-32768,32767) for x in samples),unityClips=clips,exploratoryListening='pending')
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    main()
