"""Four archived clean frames first, then one independent channel flip at a time."""
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, '/d2a')
from run import as_hex, bits, command, revision, sha

OUT = Path('/results')
C5 = Path('/ref5')
OLD = json.loads(Path('/ref2a/manifest.json').read_bytes())


def build():
    revision(Path('/lab/opendmr'), OLD['openDMR'])
    repo = ['git','-c','safe.directory=/dmrgo','-C','/dmrgo']
    assert command(repo+['rev-parse','HEAD']) == OLD['dmrgo']
    target = Path('/tmp/dmrgo')
    target.mkdir()
    with subprocess.Popen(repo+['archive',OLD['dmrgo']], stdout=subprocess.PIPE) as src:
        subprocess.run(['tar','-x','-C',target], stdin=src.stdout, check=True)
        assert src.wait() == 0
    assert sha('/go.tgz') == OLD['environment']['goArchiveSha256']
    subprocess.run(['tar','-xzf','/go.tgz','-C','/tmp'],check=True)
    env = dict(os.environ, GOTOOLCHAIN='local', GOPROXY='off', GOSUMDB='off',
               GOCACHE='/tmp/cache', GOPATH='/tmp/gopath', CGO_ENABLED='0', GOFLAGS='-mod=readonly')
    go, cpp = OLD['builds']
    subprocess.run(go,cwd=target/'v2',env=env,check=True)
    subprocess.run(cpp,check=True)
    hashes = {p:sha(p) for p in OLD['sha256']}
    assert hashes == OLD['sha256'], 'D2a source or executable hash mismatch'
    return dict(go=command(['/tmp/go/bin/go','version'],env=env),cpp=command(['g++','-dumpfullversion']),
                python=sys.version, platform=platform.platform(),sha256=hashes)


def test(f, pos, mapping, inverse):
    original = f['adaptedInput49']
    canonical = bits(f['adapted72'])
    clean = ''.join(canonical[k] for k in inverse)
    channel = list(clean)
    expected = list(original)
    local = region = info_bit = None
    if pos is not None:
        channel[pos] = '0' if channel[pos] == '1' else '1'
        local = inverse[pos]
        region = 'A' if local < 24 else 'B' if local < 47 else 'C'
        if region == 'C':
            info_bit = 24 + local - 47
            expected[info_bit] = '0' if original[info_bit] == '1' else '1'
    slot = ''.join(channel)
    local_hex = as_hex(''.join(slot[j] for j in mapping))
    padded = as_hex(original+'0000000')
    native, loop, recovered = command(['/tmp/native',original,local_hex]).split()
    go = json.loads(command(['/tmp/ref',padded,as_hex(slot)]))
    go_bits = bits(go['decodedInfo'])
    encoded = ''.join(bits(native)[k] for k in inverse)
    expected = ''.join(expected)
    checks = dict(nativeEncodingMatchesArchive=native == f['adapted72'],
                  nativeLocalLoop=loop == original,
                  goEncodingMatchesNative=go['encodedSlot'] == as_hex(encoded),
                  wireMatchesClean=encoded == clean,
                  nativeDecode=recovered == expected, goDecode=go_bits[:49] == expected,
                  goPadding=go_bits[49:] == '0000000',
                  goStatus=go['status'] == dict(BitsChecked=47,ErrorsCorrected=int(region in ('A','B')),
                                                Uncorrectable=False))
    return dict(frame=f['i'],channelBit=pos,localBit=local,region=region,
                inputInfo49=original,cleanSlot=as_hex(clean),inputSlot=as_hex(slot),
                nativeInput72=local_hex, expectedInfoBitChanged=info_bit,expected49=expected,
                nativeEncodedSlot=as_hex(encoded),goEncodedSlot=go['encodedSlot'],
                nativeRecovered49=recovered,goRecovered49=go_bits[:49],goStatus=go['status'],
                nativeChangedInfoBits=[j for j in range(49) if original[j]!=recovered[j]],
                goChangedInfoBits=[j for j in range(49) if original[j]!=go_bits[j]],
                checks=checks,firstFailedCheck=next((k for k,v in checks.items() if not v),None))


def main():
    env = build()
    m = json.loads((C5/'manifest.json').read_bytes())
    trace = C5/'frames.jsonl'
    assert sha(trace) == m['traceSha256'] == '263371c9be6f9ec41ede2316e161cec6e51f8f78c22651e4eb4bc0375a363a54'
    with trace.open() as src:
        frames = [json.loads(next(src)) for _ in range(4)]
    assert [f['i'] for f in frames] == list(range(4))
    mapping, inverse = OLD['localToChannel'], OLD['channelToLocal']
    assert sorted(mapping) == list(range(72)) and all(inverse[j]==k for k,j in enumerate(mapping))
    counts = dict(clean=0,A=0,B=0,C=0)
    failed = None
    cases = [(f,None) for f in frames] + [(f,p) for f in frames for p in range(72)]
    evidence = OUT/'cases.jsonl'
    with evidence.open('w') as out:
        for frame,pos in cases:
            row = test(frame,pos,mapping,inverse)
            out.write(json.dumps(row)+'\n')
            if row['firstFailedCheck']:
                failed = row
                break
            counts[row['region'] or 'clean'] += 1
    frame_hashes = [dict(index=f['i'],info49=f['adaptedInput49'],adapted72=f['adapted72'],
                         sha256=hashlib.sha256(bytes.fromhex(f['adapted72'])).hexdigest()) for f in frames]
    ok = failed is None and counts == dict(clean=4,A=96,B=92,C=100)
    report = dict(passAll=ok,passed=counts,firstDivergence=failed,attempted=sum(counts.values())+int(failed is not None),
                  caseTraceSha256=sha(evidence),frames=frame_hashes,C5commit='e21200f411cefcef3ba4ac09bfbf26a881882714',
                  C5traceSha256=sha(trace),C5manifestSha256=sha(C5/'manifest.json'),
                  D2acommit='02d69d99c7bb1a740c58c9144654437f45ee7757',D2amanifestSha256=sha('/ref2a/manifest.json'),
                  runnerSha256=sha(__file__),builds=OLD['builds'],image=OLD['image'],environment=env,
                  openDMR=OLD['openDMR'],dmrgo=OLD['dmrgo'],goArchiveSha256=OLD['environment']['goArchiveSha256'])
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passAll=ok,counts=counts,firstDivergence=failed)))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
