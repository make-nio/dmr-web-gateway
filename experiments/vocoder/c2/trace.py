"""Trace the first four consecutive C1 frames using the pinned local image."""
import hashlib
import json
import platform
import re
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path('/lab/opendmr')
C1 = Path('/c1/frames.jsonl')
COUNT = 4


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    assert sys.byteorder == 'little'
    commit = subprocess.check_output(['git', '-c', 'safe.directory=/lab/opendmr', '-C', ROOT,
                                      'rev-parse', 'HEAD'], text=True).strip()
    assert commit == 'd28164b39ba4d91ad5948ff22707937f8944f70f'
    with wave.open('/lab/speech.wav', 'rb') as source:
        assert (source.getframerate(), source.getnchannels(), source.getsampwidth()) == (8000, 1, 2)
        pcm = source.readframes(160 * COUNT)
    with C1.open() as source:
        reference = [json.loads(next(source)) for _ in range(COUNT)]

    widths = [7, 5, 5, 9, 7, 5, 4, 4, 3]
    offsets = []
    for i, width in enumerate(widths):
        start = sum(widths[:i])
        offsets.append(list(range(start, start + width)))
    decoder_source = (ROOT/'decoder/ambe3600x2450.c').read_text()
    reads = re.findall(r'b([0-8]) \|= ambe_d\[(\d+)\](?: << (\d+))?;', decoder_source)
    decoder = [[None] * width for width in widths]
    for param, index, shift in reads:
        decoder[int(param)][widths[int(param)] - 1 - int(shift or 0)] = int(index)
    assert len(reads) == 49 and sorted(i for row in decoder for i in row) == list(range(49))

    build = ['g++', '-O3', '-std=c++11', '-Wall', '-fPIC', '-I/lab/opendmr',
             '-I/lab/opendmr/encoder', '-I/lab/opendmr/decoder', '/c2/probe.cpp',
             '/lab/opendmr/libopendmr.a', '-lm', '-o', '/tmp/c2-probe']
    subprocess.run(build, check=True)
    lines = subprocess.check_output(['/tmp/c2-probe'], input=pcm).decode().splitlines()
    assert len(lines) == COUNT
    frames = []
    for index, line in enumerate(lines):
        *fields, hex72, recovered = line.split()
        original = list(map(int, fields))
        assert len(original) == 9 and all(0 <= b < 2**w for b, w in zip(original, widths))
        assert len(recovered) == 49 and set(recovered) <= {'0', '1'}
        pcm_hash = sha(pcm[index*320:(index+1)*320])
        ref = reference[index]
        assert index == ref['frameZeroBased'] and pcm_hash == ref['pcmSha256']
        assert hex72 == ref['cli-1'] and len(hex72) == 18
        packed = ''.join(format(b, f'0{w}b') for b, w in zip(original, widths))
        protected = format(int(hex72, 16), '072b')
        def interpret(mapping):
            return [int(''.join(recovered[i] for i in positions), 2) for positions in mapping]
        contiguous = interpret(offsets)
        decoded = interpret(decoder)
        frames.append(dict(index=index, pcmSha256=pcm_hash, original=original,
                           packed49FromWidths=packed, frameHex=hex72, frameBits=protected,
                           blocksABC=[protected[:24], protected[24:47], protected[47:]],
                           recovered49=recovered, contiguous=contiguous, decoderIndices=decoded,
                           changedInfoBits=[i for i in range(49) if packed[i] != recovered[i]],
                           differentParameters=[i for i in range(9) if decoded[i] != original[i]]))
    report = dict(commit=commit, build=build, platform=platform.platform(),
                  compiler=subprocess.check_output(['g++', '-dumpfullversion'], text=True).strip(),
                  pcmSha256=sha(pcm), sourceHashes={str(p): sha(p.read_bytes()) for p in
                      [ROOT/'opendmr.cpp', ROOT/'decoder/ambe3600x2450.c', ROOT/'libopendmr.a',
                       Path('/c2/probe.cpp')]}, encoderPositions=offsets, decoderPositions=decoder,
                  frames=frames)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
