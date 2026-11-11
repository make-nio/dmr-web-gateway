"""Temporary local worker, fixture and JS runtime assets. No binary publication."""
import hashlib
import json
import subprocess
import wave
from pathlib import Path

bank = Path('/repo/experiments/vocoder')
c5 = json.loads((bank/'evidence/c5/manifest.json').read_bytes())
d3b = json.loads((bank/'evidence/d3b/manifest.json').read_bytes())
for key, revision in d3b['revisions'].items():
    folder = '/lab/'+key
    assert subprocess.check_output(['git','-c','safe.directory='+folder,'-C',folder,'rev-parse','HEAD'],
                                   text=True).strip() == revision
for source in ['/lab/opendmr/libopendmr.a', '/lab/rust-worker/target/release/vocoder-spike-worker']:
    assert hashlib.sha256(Path(source).read_bytes()).hexdigest() == d3b['components'][source]
positions = c5['destinationsMSBFirst']
flat = [pos for row in positions for pos in row]
assert sorted(flat) == list(range(49))
def declaration(name, values):
    return 'constexpr int '+name+'[] = {'+', '.join(map(str,values))+'};\n'
Path('/tmp/layout.hpp').write_text(declaration('widths',map(len,positions))+declaration('destinations',flat))
subprocess.run(['g++','-O2','-std=c++17','-I/tmp','-I/lab/opendmr',
                '-I/lab/opendmr/encoder','-I/lab/opendmr/decoder',
                '/lab/opendmr-worker.cpp',str(bank/'d4/native.cpp'),'/lab/opendmr/libopendmr.a',
                '-Wl,--wrap=opendmr_encode','-Wl,--wrap=mbe_floattoshort','-lm','-o','/tmp/d4-open'],check=True)
with wave.open('/lab/speech.wav','rb') as source:
    pcm = source.readframes(160000)
assert hashlib.sha256(pcm).hexdigest() == d3b['inputPcmSha256']
Path('/tmp/d4.s16le').write_bytes(pcm)
