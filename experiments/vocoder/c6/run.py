"""C6: replay the archived adapted C5 stream once, then fork its final conversion."""
import gzip
import hashlib
import json
import math
import platform
import struct
import subprocess
import sys
import wave
from pathlib import Path

OUT = Path('/results')
ROOT = Path('/lab/opendmr')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def f32(number):
    return struct.unpack('<f', struct.pack('<f', number))[0]


LIMIT = f32(32767 * f32(0.95))


def rms(samples):
    return math.sqrt(math.fsum(x*x for x in samples) / len(samples))


def quantiles(samples):
    values = sorted(samples)
    return {f'p{p}': values[math.ceil(len(values)*p/100)-1] for p in (50, 90, 95, 99, 100)}


def stats(samples):
    def jumps(boundary):
        values = [abs(samples[i]-samples[i-1]) for i in range(1,len(samples))
                  if (i % 160 == 0) == boundary]
        return dict(n=len(values), above12000=sum(x > 12000 for x in values), **quantiles(values))
    return dict(n=len(samples), rms=rms(samples), min=min(samples), max=max(samples),
                absAmplitude=quantiles(list(map(abs,samples))),
                abovePositiveLimit=sum(x > LIMIT for x in samples),
                belowNegativeLimit=sum(x < -LIMIT for x in samples),
                atIntLimit=sum(abs(x) == 31128 for x in samples),
                boundaryJumps=jumps(True), withinJumps=jumps(False))


def convert(samples):
    return [int(max(-LIMIT, min(LIMIT, x))) for x in samples]


def write_wav(name, pcm):
    path = OUT/name
    with wave.open(str(path), 'wb') as sink:
        sink.setparams((1,2,8000,0,'NONE','not compressed'))
        sink.writeframes(pcm)
    return sha(path.read_bytes())


def main():
    assert sys.byteorder == 'little' and platform.machine() == 'x86_64'
    c5 = json.loads(Path('/ref/manifest.json').read_bytes())
    ref = c5['audio']['adapted']
    records = Path('/ref/frames.jsonl').read_bytes()
    assert sha(records) == c5['traceSha256']
    rows = [json.loads(line) for line in records.splitlines()]
    assert [r['i'] for r in rows] == list(range(1000))
    stream = b''.join(bytes.fromhex(r['adapted72']) for r in rows)
    assert len(stream) == 9000 and sha(stream) == ref['framesSha256']
    assert sha(Path('/ref/Clip-B.wav').read_bytes()) == ref['wavSha256']
    lib = ROOT/'libopendmr.a'
    assert sha(lib.read_bytes()) == c5['hashes'][str(lib)]
    revision = subprocess.check_output(['git','-c','safe.directory=/lab/opendmr','-C',ROOT,
                                        'rev-parse','HEAD'], text=True).strip()
    assert revision == c5['upstream']
    build = ['g++','-O3','-std=c++11','-Wall','-fPIC','-I/lab/opendmr',
             str(ROOT/'dmr_codec.cpp'),'/c6/tap.cpp',str(lib),'-Wl,--wrap=mbe_floattoshort',
             '-lm','-o','/tmp/cli-tap']
    subprocess.run(build, check=True)
    encoded = Path('/tmp/input.ambe')
    encoded.write_bytes(stream)
    subprocess.run(['/tmp/cli-tap','decode',encoded,'/tmp/original.raw'],check=True)
    raw = Path('/tmp/original.raw').read_bytes()
    capture = Path('/tmp/pre.f32le').read_bytes()
    assert len(capture) == 640000 and len(raw) == 320000 and sha(raw) == ref['pcmSha256']
    control_hash = write_wav('Toma-02.wav',raw)
    assert control_hash == ref['wavSha256']
    floats = struct.unpack('<160000f',capture)
    assert all(map(math.isfinite,floats))
    x8 = [x*8 for x in floats]
    original = list(struct.unpack('<160000h',raw))
    assert convert(x8) == original
    unity = convert(floats)
    raw1 = struct.pack('<160000h',*unity)
    unity_hash = write_wav('Toma-01.wav',raw1)
    clipped8 = [max(-LIMIT,min(LIMIT,x)) for x in x8]
    excess = [x-y for x,y in zip(x8,clipped8)]
    report = dict(image=c5['image'], upstream=revision, build=build, platform=platform.platform(),
                  corpus=c5['corpus'], sampleFormat='8 kHz mono, 160000 samples', limitF32=LIMIT,
                  preThresholdAtGain8=LIMIT/8, inputFramesSha256=sha(stream), preFloatSha256=sha(capture),
                  c5ClipBExact=True, allSamplesMatchModeledX8=True,
                  stages=dict(preFloat=stats(floats), scaledX8BeforeLimit=stats(x8),
                              controlInt16=stats(original), unityInt16=stats(unity)),
                  limiterErrorAtX8=dict(rms=rms(excess), peak=max(map(abs,excess)),
                                         rmsRelativeToUnclipped=rms(excess)/rms(x8)),
                  truncationErrorAtX8Rms=rms([a-b for a,b in zip(clipped8,original)]),
                  trueClipsX8=sum(abs(x)>LIMIT for x in x8),
                  trueClipsUnity=sum(abs(x)>LIMIT for x in floats),
                  files={'control':dict(wav='Toma-02.wav',wavSha256=control_hash,pcmSha256=sha(raw)),
                         'unity':dict(wav='Toma-01.wav',wavSha256=unity_hash,pcmSha256=sha(raw1))},
                  hashes={str(p):sha(p.read_bytes()) for p in [lib,ROOT/'decoder/mbelib.c',
                          ROOT/'dmr_codec.cpp',Path('/c6/tap.cpp'),Path('/c6/run.py')]})
    (OUT/'pre.f32le.gz').write_bytes(gzip.compress(capture, mtime=0))
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
