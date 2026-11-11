import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

INFO = 'f801a99f8ce080'
SLOT = 'b9e881526173002a6b'
GO_SHA = '7226736c2339719cda28fbf3a54d71aa63bcefe376e98cef00034268dab24840'
DMR = Path('/tmp/dmrgo')
OPEN = Path('/lab/opendmr')


def command(args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def revision(path, expected):
    git = ['git','-c',f'safe.directory={path}','-C',str(path)]
    assert command(git+['rev-parse','HEAD']) == expected
    assert command(git+['diff','HEAD','--']) == ''
    return expected


def bits(hexadecimal):
    return format(int(hexadecimal,16), f'0{4*len(hexadecimal)}b')


def as_hex(binary):
    return format(int(binary,2), f'0{(len(binary)+3)//4}x')


def main():
    upstream = revision(OPEN, 'd28164b39ba4d91ad5948ff22707937f8944f70f')
    external = 'f78e033e90559995213498973fe9d75e9bd45b93'
    repository = ['git','-c','safe.directory=/dmrgo','-C','/dmrgo']
    assert command(repository+['rev-parse','HEAD']) == external
    DMR.mkdir()
    # Build from committed objects, independent of Windows checkout line endings/modes.
    with subprocess.Popen(repository+['archive',external],stdout=subprocess.PIPE) as src:
        subprocess.run(['tar','-x','-C',DMR],stdin=src.stdout,check=True)
        assert src.wait() == 0
    archive = '/go.tgz'
    assert sha(archive) == GO_SHA
    subprocess.run(['tar','-xzf',archive,'-C','/tmp'],check=True)
    env = dict(os.environ, GOTOOLCHAIN='local', GOPROXY='off', GOSUMDB='off', GOCACHE='/tmp/cache',
               GOPATH='/tmp/gopath', CGO_ENABLED='0', GOFLAGS='-mod=readonly')
    go = '/tmp/go/bin/go'
    go_build = [go,'build','-trimpath','-buildvcs=false','-o','/tmp/ref','/d2a/main.go']
    subprocess.run(go_build, env=env, cwd=DMR/'v2',check=True)
    cpp_build = ['g++','-O3','-std=c++11','-Wall','-fPIC','-I/lab/opendmr',
                 '-I/lab/opendmr/encoder','-I/lab/opendmr/decoder','/d2a/native.cpp',
                 '/lab/opendmr/libopendmr.a','-lm','-o','/tmp/native']
    subprocess.run(cpp_build, check=True)
    mapping = [4*(k%18)+k//18 for k in range(72)]
    inverse = [18*(j%4)+j//4 for j in range(72)]
    assert sorted(mapping) == sorted(inverse) == list(range(72))
    assert all(inverse[j] == k for k,j in enumerate(mapping))
    tables = DMR/'v2/internal/fecref/ambe/tables_gen.go'
    published = []
    for field, width in [('a',24),('b',23),('c',25)]:
        row = re.search(r'var '+field+r'Table = \[\d+\]int\{([\d, ]+)\}',tables.read_text())
        indices = list(map(int,row[1].split(',')))
        assert len(indices) == width
        published.extend(indices)
    assert published == mapping
    info, pad = bits(INFO)[:49], bits(INFO)[49:]
    assert pad == '0000000'
    wire = bits(SLOT)
    external_local = ''.join(wire[j] for j in mapping)
    native, local_loop, recovered = command(['/tmp/native',info,as_hex(external_local)]).split()
    protected = bits(native)
    interleaved = ''.join(protected[k] for k in inverse)
    ref = json.loads(command(['/tmp/ref',INFO,SLOT]))
    comparisons = {}
    def compare(label, observed, expected):
        assert len(observed) == len(expected)
        delta = [i for i,(a,b) in enumerate(zip(observed,expected)) if a != b]
        comparisons[label] = dict(bits=len(observed), differentBits=delta,
                                  firstDifference=delta[0] if delta else None)
    compare('nativeA',protected[:24],external_local[:24])
    compare('nativeMaskedB',protected[24:47],external_local[24:47])
    compare('nativeC',protected[47:],external_local[47:])
    compare('nativeSlotVsLiteral',interleaved,wire)
    compare('nativeInfoFromLiteral',recovered,info)
    compare('goSlotVsLiteral',bits(ref['encodedSlot']),wire)
    compare('goInfoFromLiteral',bits(ref['decodedInfo'])[:49],info)
    compare('goPadding',bits(ref['decodedInfo'])[49:],pad)
    ok = (not any(v['differentBits'] for v in comparisons.values())
          and ref['publishedInfoMatches'] and ref['publishedSlotMatches']
          and ref['status'] == dict(BitsChecked=47,ErrorsCorrected=0,Uncorrectable=False))
    files = [OPEN/'libopendmr.a',OPEN/'opendmr.cpp',Path('/c5/pack.cpp'),tables,
             DMR/'v2/internal/fec/ambe/ambe.go',DMR/'v2/vocoder/frame.go',DMR/'v2/go.mod',
             Path('/d2a/run.py'),Path('/d2a/main.go'),Path('/d2a/native.cpp'),
             Path('/tmp/native'),Path('/tmp/ref')]
    report = dict(passAll=ok, openDMR=upstream, dmrgo=external, image='sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab',
                  environment=dict(platform=platform.platform(), python=sys.version,go=command([go,'version'],env=env),
                                   cpp=command(['g++','-dumpfullversion']),goArchiveSha256=GO_SHA),
                  builds=[go_build,cpp_build],sha256={str(f):sha(f) for f in files},
                  inputInfo=INFO,input49=info,padding=pad,inputSlot=SLOT,
                  localToChannel=mapping,channelToLocal=inverse,agreesWithPublished72Indices=True,
                  deinterleavedLiteral=as_hex(external_local),nativeProtected=native,
                  nativeInterleaved=as_hex(interleaved),nativeInfoFromExternal=as_hex(recovered+pad),
                  nativeInfo49=recovered,nativeLocalLoop49=local_loop,dmrgoOutputs=ref,
                  comparisons=comparisons)
    Path('/results/manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([ok,native,as_hex(interleaved),as_hex(recovered+pad),ref]))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
