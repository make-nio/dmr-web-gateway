"""Paired clean-frame experiment. Run in the pinned offline spike image."""
import collections
import hashlib
import json
import math
import re
import statistics
import struct
import subprocess
import wave
from pathlib import Path

OUT = Path('/results')
ROOT = Path('/lab/opendmr')
CLI = ROOT/'dmr_codec'
ROUTES = ('control', 'variant')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def metrics(pcm):
    s = struct.unpack(f'<{len(pcm)//2}h', pcm)
    def jumps(values):
        ordered = sorted(values)
        return dict(n=len(ordered), max=ordered[-1], p95=ordered[math.ceil(.95*len(ordered))-1],
                    above12000=sum(v > 12000 for v in ordered))
    return dict(samples=len(s), rms=math.sqrt(statistics.mean(x*x for x in s)),
                dc=statistics.mean(s), peak=max(map(abs, s)), min=min(s), max=max(s),
                int16Rails=sum(x in (-32768, 32767) for x in s),
                atOpenDmrLimit=sum(abs(x) == 31128 for x in s),
                frameBoundary=jumps(abs(s[i]-s[i-1]) for i in range(160, len(s), 160)),
                withinFrame=jumps(abs(s[i]-s[i-1]) for i in range(1, len(s)) if i % 160))


def param_values(bits, positions):
    return [int(''.join(bits[i] for i in row), 2) for row in positions]


def compare(mode, pcm, positions):
    count = 4096 if mode == 'sweep' else len(pcm)//320
    lines = subprocess.check_output(['/tmp/c4', mode], input=pcm).decode().splitlines()
    assert len(lines) == count
    streams = {r:bytearray() for r in ROUTES}
    correct = collections.Counter()
    delta_counts = collections.Counter()
    param_changes = [0]*9
    rows = []
    for i, line in enumerate(lines):
        expected, ctl, rec_ctl, var, rec_var = line.split()
        assert all(len(x) == 49 for x in (expected, rec_ctl, rec_var))
        assert len(ctl) == len(var) == 18
        if mode == 'sweep':
            assert int(expected[12:24], 2) == i
        word_diff = int(ctl, 16) ^ int(var, 16)
        assert word_diff & ~(0x7fffff << 25) == 0
        assert rec_ctl[:12] == expected[:12] and rec_ctl[24:] == expected[24:]
        assert rec_var == expected
        correct['controlB'] += rec_ctl[12:24] == expected[12:24]
        correct['variantB'] += 1
        bit_diff = [j for j in range(49) if rec_ctl[j] != rec_var[j]]
        assert all(12 <= j < 24 for j in bit_diff)
        delta_counts['differentWireBits'] += word_diff.bit_count()
        delta_counts['differentInformationBits'] += len(bit_diff)
        delta_counts['differentWireFrames'] += bool(word_diff)
        if mode == 'speech':
            p, q = (param_values(bits, positions) for bits in (rec_ctl, rec_var))
            for j in range(9):
                param_changes[j] += p[j] != q[j]
            rows.append(dict(i=i, input49=expected, control72=ctl, variant72=var,
                             xor72=f'{word_diff:018x}', control49=rec_ctl, variant49=rec_var,
                             infoDifferences=bit_diff, controlDecoderParams=p, variantDecoderParams=q))
            for route, frame in zip(ROUTES, (ctl, var)):
                streams[route].extend(bytes.fromhex(frame))
    if rows:
        (OUT/'frames.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary = dict(frames=count, wireAandCEqual=count, recoveredAandCMatchInput=count,
                   **correct, **delta_counts)
    if rows:
        summary['decoderParameterChanges'] = param_changes
    return summary, streams


def main():
    rev = subprocess.check_output(['git', '-c','safe.directory=/lab/opendmr','-C',ROOT,'rev-parse','HEAD'], text=True).strip()
    assert rev == 'd28164b39ba4d91ad5948ff22707937f8944f70f'
    argv = ['g++','-O3','-std=c++11','-Wall','-fPIC','-I/lab/opendmr','-I/lab/opendmr/encoder',
            '-I/lab/opendmr/decoder','/c4/pack.cpp',str(ROOT/'libopendmr.a'),'-lm','-o','/tmp/c4']
    subprocess.run(argv, check=True)
    c2 = json.loads(Path('/c2/trace.json').read_text(encoding='utf-8-sig'))
    positions = c2['decoderPositions']
    assert sorted(j for row in positions for j in row) == list(range(49))
    sweep, _ = compare('sweep', b'', positions)
    assert sweep['controlB'] == 2 and sweep['variantB'] == 4096
    with wave.open('/lab/speech.wav','rb') as source:
        assert (source.getframerate(), source.getsampwidth(), source.getnchannels()) == (8000,2,1)
        pcm = source.readframes(160000)
    assert sha(pcm) == '677d09d1c91e7cae74c0a5dc3e5e3bcd3ded3634ed471bcbca6dd65ea82e2279'
    speech, streams = compare('speech', pcm, positions)
    assert sha(streams['control']) == '60cbd71393bf36ed274e48908007289c3a529d8399574569e7763717c2ff2717'
    manifest = dict(upstream=rev, image='sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab',
                    build=argv, compiler=subprocess.check_output(['g++','-dumpfullversion'],text=True).strip(),
                    corpus='Open Speech Repository, OSR_us_000_0010_8k.wav, first 20 seconds',
                    wavFormat='8 kHz mono signed 16-bit PCM', inputPcmSha256=sha(pcm),
                    inputMetrics=metrics(pcm), sweep=sweep, speech=speech, audio={},
                    fileHashes={str(p):sha(p.read_bytes()) for p in
                                [CLI, ROOT/'libopendmr.a', ROOT/'opendmr.cpp', Path('/lab/speech.wav'),
                                 Path('/c4/pack.cpp'), Path('/c4/run.py'), Path('/c2/trace.json')]})
    for route, name in [('control','Muestra-02.wav'), ('variant','Muestra-01.wav')]:
        encoded = Path('/tmp')/(route+'.ambe')
        raw = Path('/tmp')/(route+'.pcm')
        encoded.write_bytes(streams[route])
        subprocess.run([CLI, 'decode', encoded, raw], check=True)
        data = raw.read_bytes()
        assert len(data) == len(pcm)
        with wave.open(str(OUT/name), 'wb') as sink:
            sink.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
            sink.writeframes(data)
        manifest['audio'][route] = dict(wav=name, wavSha256=sha((OUT/name).read_bytes()),
                                       pcmSha256=sha(data), framesSha256=sha(streams[route]),
                                       metrics=metrics(data))
    manifest['framesJsonlSha256'] = sha((OUT/'frames.jsonl').read_bytes())
    (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    main()
