import hashlib
import json
import platform
import subprocess
from pathlib import Path

root = Path('/lab/opendmr')
fixture = Path('/c2/trace.json')
prior = json.loads(fixture.read_bytes().decode('utf-8-sig'))
revision = subprocess.check_output(['git', '-c', 'safe.directory=/lab/opendmr', '-C', root,
                                    'rev-parse', 'HEAD'], text=True).strip()
assert revision == prior['commit'] == 'd28164b39ba4d91ad5948ff22707937f8944f70f'
build = ['g++', '-O3', '-std=c++11', '-Wall', '-fPIC', '-I/lab/opendmr',
         '-I/lab/opendmr/encoder', '-I/lab/opendmr/decoder', '/c3/probe.cpp',
         '/lab/opendmr/libopendmr.a', '-lm', '-o', '/tmp/c3']
subprocess.run(build, check=True)
frames = prior['frames']
assert [f['index'] for f in frames] == list(range(4))
inputs = []
for f in frames:
    bits = f['packed49FromWidths']
    inputs.append(f"{int(bits[:12], 2)} {int(bits[12:24], 2)} {f['frameHex']}")
lines = subprocess.check_output(['/tmp/c3'], input='\n'.join(inputs)+'\n', text=True).splitlines()
assert len(lines) == 5
counts = dict(zip(['rawEqualsCanonicalShiftedLeft', 'canonicalRoundTrips', 'rawNeeds24Bits',
                   'distinctLow23Words', 'upstreamLow23RoundTrips'], map(int, lines[0].split())))
rows = []
for f, line in zip(frames, lines[1:]):
    raw, canonical, a24, rxA, txMask, rxMask, masked, wire, received, out, native, control = map(int, line.split())
    bits = f['packed49FromWidths']
    b = int(bits[12:24], 2)
    assert format(wire, '023b') == f['blocksABC'][1]
    assert out == native == int(f['recovered49'][12:24], 2)
    rows.append(dict(index=f['index'], frameHex=f['frameHex'], aInput=bits[:12],
                     a24=format(a24, '024b'), aRecovered=format(rxA, '012b'),
                     bInput=bits[12:24], canonical23=format(canonical, '023b'),
                     golayReturn24=format(raw, '024b'), txMask23=format(txMask, '023b'),
                     afterXor24=format(masked, '024b'), wire23=format(wire, '023b'),
                     rxMask23=format(rxMask, '023b'), descrambled23=format(received, '023b'),
                     decoder12=format(out, '012b'), originalUnpack12=format(native, '012b'),
                     canonicalControl12=format(control, '012b'),
                     wireMatchesLow23=(masked & 0x7fffff) == wire,
                     maskCancels=(raw & 0x7fffff) == received,
                     matchedInput=out == b))
sources = [fixture, root/'opendmr.cpp', root/'encoder/cgolay24128.cpp', root/'libopendmr.a',
           Path('/c3/probe.cpp'), Path('/c3/trace.py')]
report = dict(upstream=revision, platform=platform.platform(), build=build,
              compiler=subprocess.check_output(['g++', '-dumpfullversion'], text=True).strip(),
              sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
              exhaustiveInputs=4096, counts=counts, frames=rows)
print(json.dumps(report, indent=2))
