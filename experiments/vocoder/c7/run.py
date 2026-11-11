"""Offline C7 stimulus preparation, replay, parameter checks and paired WAVs."""
import json
import math
import platform
import struct
import subprocess
import sys
import wave
from pathlib import Path

BANK = Path('/bank')
sys.path.insert(0, str(BANK/'c6'))
from run import LIMIT, ROOT, OUT, convert, rms, sha, stats, write_wav


def archive(phase):
    return json.loads((BANK/'evidence'/phase/'manifest.json').read_bytes())


def read_voice(path, digest):
    assert sha(path.read_bytes()) == digest
    with wave.open(str(path), 'rb') as wav:
        assert (wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getcomptype()) == (8000,1,2,'NONE')
        return struct.unpack('<160000h', wav.readframes(160000))


def build():
    enc = ['g++','-O3','-std=c++11','-Wall','-fPIC','-I/lab/opendmr',
           '-I/lab/opendmr/decoder','-I/lab/opendmr/encoder',str(BANK/'c5/pack.cpp'),
           str(ROOT/'libopendmr.a'),'-lm','-o','/tmp/enc']
    dec = ['g++','-O3','-std=c++11','-Wall','-fPIC','-I/lab/opendmr',str(ROOT/'dmr_codec.cpp'),
           str(BANK/'c6/tap.cpp'),str(ROOT/'libopendmr.a'),'-Wl,--wrap=mbe_floattoshort',
           '-lm','-o','/tmp/dec']
    for command in (enc, dec):
        subprocess.run(command, check=True)
    return [enc, dec]


def run_case(label, source, gain, positions):
    scaled = [round(x*gain) for x in source]
    input_clips = sum(not -32768 <= x <= 32767 for x in scaled)
    stimulus = [max(-32768,min(32767,x)) for x in scaled]
    pcm = struct.pack(f'<{len(stimulus)}h', *stimulus)
    count = len(stimulus)//160
    lines = subprocess.check_output(['/tmp/enc'], input=pcm).decode().splitlines()
    assert len(lines) == count and count*160 == len(stimulus)
    stream = bytearray()
    for i, line in enumerate(lines):
        *params, _, adapted, _, _, frame, recovered = line.split()
        received = [int(''.join(recovered[j] for j in row), 2) for row in positions]
        if list(map(int, params)) != received or adapted != recovered:
            raise ValueError(f'{label}: parameter mismatch in frame {i}')
        stream.extend(bytes.fromhex(frame))
    assert len(stream) == count*9
    Path('/tmp/input.ambe').write_bytes(stream)
    subprocess.run(['/tmp/dec','decode','/tmp/input.ambe','/tmp/control.raw'], check=True)
    floats = struct.unpack(f'<{len(stimulus)}f', Path('/tmp/pre.f32le').read_bytes())
    assert all(map(math.isfinite, floats))
    output = convert(floats)
    result = struct.pack(f'<{len(output)}h', *output)
    # Neutral filenames; alternate which member of each pair is the stimulus.
    name_in, name_out = [f'{label}-{x}.wav' for x in ('A','B')]
    if int(label[-2:]) % 2:
        name_in, name_out = name_out, name_in
    report = dict(gain=gain, durationSeconds=len(stimulus)/8000, frames=count,
                  matchingParameterVectors=count, exceptions=[], inputPreparationClips=input_clips,
                  inputRails=sum(x in (-32768,32767) for x in stimulus),
                  outputTrueClips=sum(abs(x)>LIMIT for x in floats), input=stats(stimulus),
                  output=stats(output), inputPcmSha256=sha(pcm), ambeSha256=sha(stream),
                  outputPcmSha256=sha(result), inputWav=name_in, outputWav=name_out,
                  inputWavSha256=write_wav(name_in,pcm), outputWavSha256=write_wav(name_out,result))
    return report, output


def main():
    c5, c6 = archive('c5'), archive('c6')
    revision = subprocess.check_output(['git','-c','safe.directory=/lab/opendmr','-C',ROOT,
                                        'rev-parse','HEAD'],text=True).strip()
    assert revision == c5['upstream'] == c6['upstream']
    for file, key, record in [(BANK/'c5/pack.cpp','/c5/pack.cpp',c5),
                              (BANK/'c6/tap.cpp','/c6/tap.cpp',c6),
                              (BANK/'c6/run.py','/c6/run.py',c6),
                              (ROOT/'libopendmr.a',str(ROOT/'libopendmr.a'),c6)]:
        assert sha(file.read_bytes()) == record['hashes'][key]
    layout = c5['destinationsMSBFirst']
    flat = [x for row in layout for x in row]
    assert sorted(flat) == list(range(49))
    Path('/tmp/layout').write_text(' '.join(map(str,flat)))
    builds = build()
    hashes = {'0010':'a4bf9becd046d7aedb6d05b6e12347a6294a44f74d263089c636fb0a2b1e6561',
              '0030':'d3e1cfba98a44ddfc6e99508e663794c8dc41bdb2baced224f779c453143b622'}
    voices = {key:read_voice(path,hashes[key]) for key,path in
              [('0010',Path('/lab/speech.wav')),('0030',Path('/second.wav'))]}
    cases = [('0010',1),('0030',.25),('0010',2),('0030',1),('0010',.25),('0030',2),
             ('silence',1),('transition',1)]
    manifest = dict(upstream=revision, image=c6['image'], platform=platform.platform(),
                    builds=builds, source='Open Speech Repository, OSR_us_000_{id}_8k.wav',
                    sourceWavSha256=hashes, format='mono PCM s16le 8000 Hz',
                    state='new encoder and decoder processes for every case; continuous within case',
                    rounding='nearest integer, ties to even; clamp signed int16 after scaling',
                    initialization='first 20 s from sample 0 for each full voice case', cases={})
    for number,(key,gain) in enumerate(cases,1):
        label = f'Par-{number:02d}'
        if key == 'silence':
            samples = [0]*8000
        elif key == 'transition':
            voice = voices['0030']
            samples = voice[16000:32000] + (0,)*8000 + voice[32000:48000]
        else:
            samples = voices[key]
        case, output = run_case(label,samples,gain,layout)
        case['stimulus'] = key
        if number == 1:
            assert case['inputPcmSha256'] == c5['inputPcmSha256']
            assert case['ambeSha256'] == c6['inputFramesSha256']
            assert case['outputWavSha256'] == c6['files']['unity']['wavSha256']
            case['referenceC6Exact'] = True
        if key == 'transition':
            case['segments'] = []
            for start,end,kind in [(0,16000,'0030 [2,4) s'),(16000,24000,'silence'),
                                   (24000,40000,'0030 [4,6) s')]:
                case['segments'].append(dict(startSample=start,endExclusive=end,source=kind,
                                             inputRms=rms(samples[start:end]),outputRms=rms(output[start:end]),
                                             outputPeak=max(map(abs,output[start:end]))))
            case['joinAbsoluteJumps'] = [{'atSample':j,'input':abs(samples[j]-samples[j-1]),
                                          'output':abs(output[j]-output[j-1])} for j in (16000,24000)]
        manifest['cases'][label] = case
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__ == '__main__':
    main()
