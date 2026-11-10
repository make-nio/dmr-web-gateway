"""Run with the local C4 image and its C2/C4 evidence mounted read-only."""
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, '/c4')
from run import CLI, OUT, ROOT, metrics, param_values, sha


def main():
    c2 = json.loads(Path('/ref2/trace.json').read_text(encoding='utf-8-sig'))
    c4 = json.loads(Path('/ref4/manifest.json').read_text())
    fixture = Path('/ref4/frames.jsonl').read_bytes()
    assert sha(fixture) == c4['framesJsonlSha256']
    prior = [json.loads(line) for line in fixture.splitlines()]
    git = ['git', '-c', 'safe.directory=/lab/opendmr', '-C', str(ROOT)]
    revision = subprocess.check_output(git + ['rev-parse', 'HEAD'], text=True).strip()
    assert revision == c4['upstream'] == c2['commit']
    assert sha(CLI.read_bytes()) == c4['fileHashes'][str(CLI)]
    positions = c2['decoderPositions']
    flat = [i for row in positions for i in row]
    widths = [7, 5, 5, 9, 7, 5, 4, 4, 3]
    assert list(map(len, positions)) == widths and sorted(flat) == list(range(49))
    # Verify the archived map against the actual decoder source used for the build.
    source = ROOT/'decoder/ambe3600x2450.c'
    reads = re.findall(r'b([0-8]) \|= ambe_d\[(\d+)\](?: << (\d+))?;', source.read_text())
    assert len(reads) == 49
    for p, bit, shift in reads:
        p = int(p)
        assert positions[p][widths[p]-1-int(shift or 0)] == int(bit)
    Path('/tmp/layout').write_text(' '.join(map(str, flat)))
    build = ['g++','-O3','-std=c++11','-Wall','-fPIC','-I/lab/opendmr',
             '-I/lab/opendmr/encoder','-I/lab/opendmr/decoder','/c5/pack.cpp',
             str(ROOT/'libopendmr.a'),'-lm','-o','/tmp/c5']
    subprocess.run(build, check=True)
    with wave.open('/lab/speech.wav', 'rb') as wav:
        assert (wav.getframerate(), wav.getsampwidth(), wav.getnchannels()) == (8000,2,1)
        pcm = wav.readframes(160000)
    assert sha(pcm) == c4['inputPcmSha256']
    lines = subprocess.check_output(['/tmp/c5'], input=pcm).decode().splitlines()
    assert len(lines) == len(prior) == 1000
    streams = {'control':bytearray(), 'adapted':bytearray()}
    exceptions = []
    control_matches = [0]*9
    whole_control = 0
    wire_changes = 0
    info_changes = 0
    b_matches = dict.fromkeys(streams, 0)
    with (OUT/'frames.jsonl').open('w') as evidence:
        for i, (line, ref) in enumerate(zip(lines, prior)):
            *values, original, adapted, ctrl72, ctrl49, exp72, exp49 = line.split()
            params = list(map(int, values))
            assert i == ref['i'] and ctrl72 == ref['variant72'] and original == ref['input49']
            assert ''.join(format(v, f'0{w}b') for v,w in zip(params,widths)) == original
            assert ''.join(adapted[j] for j in flat) == original
            left, right = param_values(ctrl49, positions), param_values(exp49, positions)
            for j in range(9):
                control_matches[j] += left[j] == params[j]
            whole_control += left == params
            if right != params or adapted != exp49 or original != ctrl49:
                exceptions.append(i)
            xor = int(ctrl72,16) ^ int(exp72,16)
            wire_changes += xor.bit_count()
            changed = [j for j in range(49) if ctrl49[j] != exp49[j]]
            info_changes += len(changed)
            for route, expected, recovered, frame in [('control', original, ctrl49, ctrl72),
                                                      ('adapted', adapted, exp49, exp72)]:
                b_matches[route] += recovered[12:24] == expected[12:24]
                streams[route].extend(bytes.fromhex(frame))
            evidence.write(json.dumps(dict(i=i, params=params, control49=ctrl49, adapted49=exp49,
                                           adaptedInput49=adapted, control72=ctrl72, adapted72=exp72,
                                           xor72=f'{xor:018x}', changedInfo=changed,
                                           controlParams=left, adaptedParams=right))+'\n')
    if exceptions or min(b_matches.values()) != 1000:
        raise ValueError(f'Pre-audio verification failed: {exceptions}, B={b_matches}')
    assert sha(streams['control']) == c4['audio']['variant']['framesSha256']
    report = dict(upstream=revision, image=c4['image'], build=build, inputPcmSha256=sha(pcm),
                  corpus=c4['corpus'], format=c4['wavFormat'], controlsFrom='C4 variant',
                  frames=len(lines), destinationsMSBFirst=positions, BMatches=b_matches,
                  controlAllNine=whole_control, controlMatchesByParameter=control_matches,
                  adaptedAllNine=len(lines), exceptions=exceptions, changedWireBits=wire_changes,
                  changedInfoBits=info_changes, inputMetrics=metrics(pcm), audio={},
                  traceSha256=sha((OUT/'frames.jsonl').read_bytes()),
                  hashes={str(p):sha(p.read_bytes()) for p in [source, CLI, ROOT/'libopendmr.a',
                          Path('/c5/pack.cpp'), Path('/c5/experiment.py'), Path('/c4/run.py')]})
    for route, name in [('control','Clip-A.wav'), ('adapted','Clip-B.wav')]:
        encoded = Path('/tmp')/(route+'.ambe')
        raw = Path('/tmp')/(route+'.pcm')
        encoded.write_bytes(streams[route])
        subprocess.run([CLI,'decode',encoded,raw], check=True)
        data = raw.read_bytes()
        assert len(data) == len(pcm)
        with wave.open(str(OUT/name),'wb') as sink:
            sink.setparams((1,2,8000,0,'NONE','not compressed'))
            sink.writeframes(data)
        wav_hash = sha((OUT/name).read_bytes())
        if route == 'control':
            assert wav_hash == c4['audio']['variant']['wavSha256']
        report['audio'][route] = dict(wav=name, wavSha256=wav_hash, pcmSha256=sha(data),
                                      framesSha256=sha(streams[route]), metrics=metrics(data))
    (OUT/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
