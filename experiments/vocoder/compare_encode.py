import hashlib
import json
import platform
import struct
import subprocess
import sys
import wave
from pathlib import Path


OUT = Path('/results')
CLI = '/lab/opendmr/dmr_codec'
WORKER = '/lab/opendmr-worker'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT).strip()


def compare(left, right):
    assert len(left) == len(right) and len(left) % 9 == 0
    differing = [i for i, (a, b) in enumerate(zip(left, right)) if a != b]
    bits = sum((a ^ b).bit_count() for a, b in zip(left, right))
    first = differing[0] if differing else None
    return {
        'equal': not differing, 'bytesCompared': len(left),
        'bitsCompared': len(left) * 8, 'differentBytes': len(differing),
        'differentBits': bits,
        'differentFrames': len({i // 9 for i in differing}),
        'firstDifferentFrameZeroBased': first // 9 if first is not None else None,
        'firstDifferentByteZeroBased': first,
        'firstDifferentBitZeroBasedMSB': next(
            (i * 8 + j for i in differing for j in range(8)
             if (left[i] ^ right[i]) & (1 << (7-j))), None),
    }


def main():
    OUT.mkdir(exist_ok=True)
    assert sys.byteorder == 'little' and platform.machine() == 'x86_64'
    source = Path('/lab/speech.wav')
    assert sha(source.read_bytes()) == 'a4bf9becd046d7aedb6d05b6e12347a6294a44f74d263089c636fb0a2b1e6561'
    with wave.open(str(source), 'rb') as wav:
        assert (wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getcomptype()) == (8000, 1, 2, 'NONE')
        pcm = wav.readframes(160000)
    assert len(pcm) == 320000
    (OUT / 'input.s16le').write_bytes(pcm)
    request = ''.join('E ' + pcm[i:i+320].hex() + '\n' for i in range(0, len(pcm), 320))
    report = {
        'scope': 'C1 encode only; fresh process per run; no reset commands',
        'environment': {
            'platform': platform.platform(), 'byteorder': sys.byteorder,
            'python': platform.python_version(), 'g++': command(['g++', '--version']),
            'gcc': command(['gcc', '--version']),
            'upstreamCommit': command(['git', '-c', 'safe.directory=/lab/opendmr', '-C', '/lab/opendmr', 'rev-parse', 'HEAD']),
            'upstreamTrackedDiff': command(['git', '-c', 'safe.directory=/lab/opendmr', '-C', '/lab/opendmr', 'diff', 'HEAD', '--']),
            'cliLdd': command(['ldd', CLI]), 'workerLdd': command(['ldd', WORKER]),
            'makefile': Path('/lab/opendmr/Makefile').read_text(),
        },
        'files': {p: sha(Path(p).read_bytes()) for p in [CLI, WORKER, '/lab/opendmr/libopendmr.a', '/lab/opendmr-worker.cpp', '/lab/opendmr/opendmr.cpp']},
        'input': {'source': 'Open Speech Repository, OSR_us_000_0010_8k.wav',
                  'wavSha256': sha(source.read_bytes()), 'pcmSha256': sha(pcm),
                  'format': '8000 Hz mono s16le', 'seconds': 20, 'bytes': len(pcm),
                  'frames': len(pcm)//320, 'minSample': min(struct.unpack('<160000h', pcm)),
                  'maxSample': max(struct.unpack('<160000h', pcm))},
        'runs': [], 'comparisons': {},
    }
    assert report['environment']['upstreamCommit'] == 'd28164b39ba4d91ad5948ff22707937f8944f70f'
    assert report['environment']['upstreamTrackedDiff'] == ''
    outputs = {}
    for repetition in (1, 2):
        name = f'cli-{repetition}'
        args = [CLI, 'encode', str(OUT/'input.s16le'), str(OUT/(name+'.ambe'))]
        result = subprocess.run(args, capture_output=True, timeout=60, check=True)
        (OUT/(name+'.stdout')).write_bytes(result.stdout)
        (OUT/(name+'.stderr')).write_bytes(result.stderr)
        outputs[name] = (OUT/(name+'.ambe')).read_bytes()
        report['runs'].append({'name': name, 'command': args, 'exitCode': result.returncode, 'sha256': sha(outputs[name])})
        name = f'wrapper-{repetition}'
        result = subprocess.run([WORKER], input=request.encode(), capture_output=True, timeout=60, check=True)
        (OUT/(name+'.stdout')).write_bytes(result.stdout)
        (OUT/(name+'.stderr')).write_bytes(result.stderr)
        lines = result.stdout.decode().splitlines()
        assert len(lines) == len(pcm)//320
        frames = []
        for line in lines:
            nanos, hexframe = line.split()
            assert int(nanos) >= 0
            frame = bytes.fromhex(hexframe)
            assert len(frame) == 9
            frames.append(frame)
        outputs[name] = b''.join(frames)
        (OUT/(name+'.ambe')).write_bytes(outputs[name])
        report['runs'].append({'name': name, 'command': [WORKER], 'stdin': '1000 E hex-PCM lines, then EOF; no D/R', 'exitCode': result.returncode, 'sha256': sha(outputs[name])})
    for output in outputs.values():
        assert len(output) == len(pcm)//320*9
    for left, right in [('cli-1', 'wrapper-1'), ('cli-2', 'wrapper-2'), ('cli-1', 'cli-2'), ('wrapper-1', 'wrapper-2')]:
        report['comparisons'][left+' vs '+right] = compare(outputs[left], outputs[right])
    with (OUT/'frames.jsonl').open('w') as evidence:
        for i in range(len(pcm)//320):
            row = {'frameZeroBased': i, 'pcmSha256': sha(pcm[i*320:(i+1)*320])}
            row.update({name: data[i*9:(i+1)*9].hex() for name, data in outputs.items()})
            evidence.write(json.dumps(row)+'\n')
    (OUT/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'input': report['input'], 'comparisons': report['comparisons']}, indent=2))


if __name__ == '__main__':
    main()
