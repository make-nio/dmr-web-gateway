import json
import os
import subprocess
import time
import sys
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

def readiness(identifier):
    return subprocess.run(['docker','exec',identifier,'node','dist/src/healthcheck.js','--ready'],stdout=subprocess.DEVNULL).returncode == 0

def wait_ready(identifier, expected):
    deadline = time.monotonic() + 85
    while time.monotonic() < deadline:
        if readiness(identifier) == expected:
            return
        time.sleep(2)
    raise AssertionError('readiness timeout')

secret = root / 'offline.secret'
assert not run(compose + ['ps','-a','-q']), 'Validation project already has containers'
assert not secret.exists(), 'Refusing to overwrite existing marker'
secret.write_bytes(os.urandom(32))
simulator = None
soak_result = None
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
    wait_ready(gateway,True)
    if '--soak' in sys.argv:
        started = time.monotonic()
        log_start = str(int(time.time()) + 1)
        samples = []
        previous = {}
        probe = "const fs=require('node:fs');const cpu=fs.readFileSync('/sys/fs/cgroup/cpu.stat','utf8').match(/usage_usec (\\d+)/)[1];console.log(JSON.stringify({memory:Number(fs.readFileSync('/sys/fs/cgroup/memory.current','utf8')),cpu:Number(cpu)}));"
        while True:
            sample = {'seconds':round(time.monotonic()-started,3)}
            for name,identifier in [('gateway',gateway),('simulator',simulator)]:
                info = status(identifier)
                assert info['State']['Health']['Status'] == 'healthy'
                assert info['RestartCount'] == 0 and not info['State']['OOMKilled']
                resource = json.loads(run(['docker','exec',identifier,'node','-e',probe]))
                measured = time.monotonic()
                resource['cpuPercent'] = 0 if name not in previous else (resource['cpu']-previous[name][0])/(measured-previous[name][1])/10000
                previous[name] = (resource['cpu'],measured)
                sample[name] = resource
            assert readiness(gateway)
            samples.append(sample)
            print(json.dumps({'event':'docker_soak','seconds':sample['seconds'],'healthy':True}),flush=True)
            if time.monotonic()-started >= 600:
                break
            time.sleep(10)
        logs = run(['docker','logs','--since',log_start,gateway])
        assert '"state":"retry"' not in logs and '"state":"login"' not in logs
        soak_result = {'passed':True,'elapsedSeconds':round(time.monotonic()-started,3),'unexpectedReconnects':0,'samples':samples}
        print(json.dumps({'event':'docker_soak_pass','elapsedSeconds':soak_result['elapsedSeconds'],'samples':len(samples)}),flush=True)
    print('startup health: PASS; pausing simulator',flush=True)
    run(['docker','pause',simulator])
    wait_ready(gateway,False)
    time.sleep(35)
    assert status(gateway)['State']['Health']['Status'] == 'healthy'
    assert not readiness(gateway)
    print('master loss: process healthy, readiness failed PASS',flush=True)
    run(['docker','unpause',simulator])
    wait_health(gateway,'healthy')
    wait_ready(gateway,True)
    print('reconnected: healthy PASS',flush=True)
    output = run(compose + ['logs','--no-color'])
    assert secret.read_bytes().hex() not in output
    print('logs: no marker hex; successful recovery',flush=True)
    run(compose + ['stop','gateway'])
    assert status(gateway)['State']['ExitCode'] == 0
    print('SIGTERM exit 0: PASS',flush=True)
    if soak_result:
        (root/'docs/docker-soak.json').write_text(json.dumps(soak_result,indent=2)+'\n')
finally:
    if simulator:
        subprocess.run(['docker','unpause',simulator],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(compose + ['down'],check=True)
    secret.unlink(missing_ok=True)
