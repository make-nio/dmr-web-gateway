import json
import os
import subprocess
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.chdir(root)
compose = ['docker','compose','-p','dmr-pr9-validation']
def run(args):
    return subprocess.check_output(args, text=True).strip()
def status(identifier):
    return json.loads(run(['docker','inspect',identifier]))[0]
def wait_health(identifier, expected):
    deadline = time.monotonic() + 85
    while time.monotonic() < deadline:
        if status(identifier)['State']['Health']['Status'] == expected:
            return
        time.sleep(2)
    raise AssertionError('health timeout: ' + expected)

secret = root / 'offline.secret'
assert not run(compose + ['ps','-a','-q']), 'Validation project already has containers'
assert not secret.exists(), 'Refusing to overwrite existing marker'
secret.write_bytes(os.urandom(32))
simulator = None
try:
    subprocess.run(compose + ['up','-d','--build','--wait','--wait-timeout','90'],check=True)
    gateway = run(compose + ['ps','-q','gateway'])
    simulator = run(compose + ['ps','-q','simulator'])
    for identifier, cpu, memory in [(gateway,750000000,384*1024**2),(simulator,250000000,128*1024**2)]:
        info = status(identifier)
        host = info['HostConfig']
        assert info['Config']['User'] == '1000:1000'
        assert host['ReadonlyRootfs'] and host['NanoCpus'] == cpu and host['Memory'] == memory
        assert host['CapDrop'] == ['ALL'] and 'no-new-privileges:true' in host['SecurityOpt']
        assert not host['PortBindings'] and not info['NetworkSettings']['Ports']
        assert host['PidsLimit'] == 64
        script = "const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os');assert.equal(process.getuid(),1000);assert.deepEqual(Object.keys(os.networkInterfaces()),['lo']);assert.match(fs.readFileSync('/proc/self/status','utf8'),/CapEff:\\s+0+\\n/);assert.match(fs.readFileSync('/proc/self/status','utf8'),/NoNewPrivs:\\s+1/);assert.throws(()=>fs.writeFileSync('/app/write-probe','x'));assert.equal(fs.readFileSync('/run/secrets/dmr_password').length,32);console.log('uid/capabilities/network/readonly/secret: PASS');"
        print(run(['docker','exec',identifier,'node','-e',script]),flush=True)
        print(json.dumps({'container':info['Name'],'cpu':cpu/1e9,'memoryMiB':memory/1024**2,'network':host['NetworkMode'],'readonly':host['ReadonlyRootfs']}),flush=True)
    assert status(simulator)['HostConfig']['NetworkMode'] == 'none'
    assert status(gateway)['HostConfig']['NetworkMode'] == 'container:' + simulator
    print('startup health: PASS; pausing simulator',flush=True)
    run(['docker','pause',simulator])
    wait_health(gateway,'unhealthy')
    print('loss detected: unhealthy PASS',flush=True)
    run(['docker','unpause',simulator])
    wait_health(gateway,'healthy')
    print('reconnected: healthy PASS',flush=True)
    output = run(compose + ['logs','--no-color'])
    assert secret.read_bytes().hex() not in output
    print('logs: no marker hex; successful recovery',flush=True)
    run(compose + ['stop','gateway'])
    assert status(gateway)['State']['ExitCode'] == 0
    print('SIGTERM exit 0: PASS',flush=True)
finally:
    if simulator:
        subprocess.run(['docker','unpause',simulator],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(compose + ['down'],check=True)
    secret.unlink(missing_ok=True)
