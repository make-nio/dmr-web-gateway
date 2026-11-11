import { readFileSync as read, readdirSync, readlinkSync, writeFileSync, appendFileSync } from 'node:fs';
import { performance } from 'node:perf_hooks';
import { setTimeout as sleep } from 'node:timers/promises';
import assert from 'node:assert/strict';
import { configure } from '/tmp/js/config.js';
import { PCM, LOCAL } from '/tmp/js/contract.js';

const name = process.argv[2];
assert(['opendmr','blip25'].includes(name));
const mode = process.argv[3] ?? 'duplex';
assert(['encode','decode','duplex'].includes(mode));
const out = '/results/'+name;
const factory = configure(name,1000);
const pcm = read('/tmp/d4.s16le');
const refs = JSON.parse(read('/repo/experiments/vocoder/evidence/d3b/manifest.json'));
const rx = name === 'opendmr' ? 'RX' : 'TX';
const frames = read('/repo/experiments/vocoder/evidence/d3b/'+rx+'-bits.jsonl','utf8').trim().split('\n')
    .map(line=>Buffer.from(JSON.parse(line).local72,'hex'));
assert.equal(frames.length,1000);
const now = () => performance.now();
const cg = key => read('/sys/fs/cgroup/'+key,'utf8').trim();
const fields = key => Object.fromEntries(cg(key).split('\n').map(s=>{const [k,v]=s.split(' ');return [k,Number(v)];}));
const executable = name==='opendmr'?'/tmp/d4-open':'/lab/rust-worker/target/release/vocoder-spike-worker';
function snapshot(){
  const workers=[];
  let rss=0,processes=0;
  for(const pid of readdirSync('/proc').filter(v=>/^\d+$/.test(v))){
    try {
      const status=read('/proc/'+pid+'/status','utf8');
      const kb=Number(status.match(/^VmRSS:\s+(\d+)/m)?.[1]??0);
      processes++;
      rss+=kb*1024;
      if(readlinkSync('/proc/'+pid+'/exe')===executable) workers.push({pid:Number(pid),rss:kb*1024});
    } catch(e){if(!['ENOENT','EACCES','ESRCH'].includes(e.code))throw e;}
  }
  return {t:now(),cpu:fields('cpu.stat'),mem:Number(cg('memory.current')),events:fields('memory.events'),
    processes,rss,workerCount:workers.length,workerRSS:workers.reduce((s,w)=>s+w.rss,0),workers};
}
const q=(values,p)=>values.length?values[Math.ceil(values.length*p)-1]:null;
function summary(values){
  values.sort((a,b)=>a-b);
  return {n:values.length,p50:q(values,.50),p95:q(values,.95),p99:q(values,.99),max:values.at(-1)??null};
}
function packet(i){const j=i%1000;return {format:PCM,bytes:pcm.subarray(j*320,j*320+320)};}
function channel(i){return {format:LOCAL,bytes:frames[i%1000]};}
async function waitUntil(target){
  while(target-now()>0.05) await sleep(Math.max(1,Math.floor(target-now())));
}
async function recovery(){
  const a=await factory.createSession();
  const pid=snapshot().workers[0].pid;
  const b=await factory.createSession();
  let replacement;
  try {
    await Promise.all([a.encode(packet(0)),b.encode(packet(0))]);
    const t=now();
    process.kill(pid,'SIGKILL');
    let code;
    try {await a.encode(packet(1));} catch(e){code=e.code;}
    assert.equal(code,'WORKER');
    const detectedMs=now()-t;
    assert.equal((await b.decode(channel(1))).bytes.length,320);
    await a.close();
    replacement=await factory.createSession();
    const f=await replacement.encode(packet(0));
    assert.equal(f.bytes.length,9);
    return {failure:code,detectedMs,timeToFreshFrameMs:now()-t,siblingContinued:true};
  } finally {
    await Promise.all([a.close(),b.close(),replacement?.close()]);
  }
}
async function stage(n){
  const ss=[], pending=new Map(), errs=[];
  const lat={encodeFromTick:[],decodeFromDispatch:[],duplexFromTick:[],decodeFromTick:[],dispatchLag:[]};
  let done=0,late=0,encLate=0,decLate=0,drops=0,errors=0,reason=null;
  const start=now();
  try {
    for(let i=0;i<n;i++) ss.push(await factory.createSession());
    const startupMs=now()-start;
    const base=snapshot();
    assert.equal(base.workerCount,n);
    const t0=now();
    let last=t0,prev=base,lastBad=0,lastErrors=0,lastSlots=0,severe=0,next=0;
    let maxRSS=base.rss,maxMem=base.mem,maxWorkerRSS=base.workerRSS,maxProcs=base.processes;
    function sample(){
      const s=snapshot(),t=now();
      const bad=late+drops,slots=next*n;
      const ratio=(bad-lastBad)/Math.max(1,slots-lastSlots);
      severe=ratio>=.10?severe+1:0;
      if(s.events.oom>base.events.oom || s.events.oom_kill>base.events.oom_kill)reason='cgroup OOM';
      else if(errors-lastErrors>=3 || errors>=5)reason='sustained errors';
      else if(severe>=5)reason='five consecutive samples >=10% missed';
      maxRSS=Math.max(maxRSS,s.rss);maxMem=Math.max(maxMem,s.mem);
      maxWorkerRSS=Math.max(maxWorkerRSS,s.workerRSS);maxProcs=Math.max(maxProcs,s.processes);
      appendFileSync(out+'-samples.jsonl',JSON.stringify({n,seconds:(t-t0)/1000,slots,done,drops,late,errors,
        intervalMissRatio:ratio,cpuPct:100*(s.cpu.usage_usec-prev.cpu.usage_usec)/(1000*(s.t-prev.t)),
        throttledUsec:s.cpu.throttled_usec-prev.cpu.throttled_usec,mem:s.mem,rss:s.rss,workerRSS:s.workerRSS,
        processes:s.processes,workers:s.workerCount,events:s.events})+'\n');
      lastBad=bad;lastErrors=errors;lastSlots=slots;prev=s;last=t;
    }
    while(next<6000 && !reason){
      await waitUntil(t0+next*20);
      const tick=Math.min(5999,Math.floor((now()-t0)/20));
      if(tick<next)continue;
      drops+=(tick-next)*n;
      next=tick+1;
      const due=t0+tick*20;
      for(let i=0;i<n;i++){
        if(pending.has(i)){drops++;continue;}
        const input=tick+37*i;
        const task=(async()=>{
          lat.dispatchLag.push(now()-due);
          let end;
          if(mode !== 'decode'){
            await ss[i].encode(packet(input));
            end=now();
            lat.encodeFromTick.push(end-due);
            if(end-due>20)encLate++;
          }
          if(mode !== 'encode'){
            const dispatch=end??now();
            await ss[i].decode(channel(input+251));
            end=now();
            lat.decodeFromDispatch.push(end-dispatch);
            if(end-dispatch>20)decLate++;
            if(mode==='duplex')lat.duplexFromTick.push(end-due);
            else lat.decodeFromTick.push(end-due);
          }
          if(end-due>20)late++;
          done++;
        })().catch(e=>{errors++;if(errs.length<8)errs.push({tick,i,code:e.code??e.message});})
            .finally(()=>pending.delete(i));
        pending.set(i,task);
      }
      if(now()-last>=1000)sample();
    }
    await Promise.all([...pending.values()]);
    if(!reason) await waitUntil(t0+120000);
    const end=now(); sample();
    const final=prev;
    const closeStart=now();
    await Promise.all(ss.map(s=>s.close()));
    const closeMs=now()-closeStart, remaining=snapshot().workerCount;
    assert.equal(remaining,0);
    assert.equal(next*n,done+errors+drops);
    return {n,plannedTicks:6000,scheduledTicks:next,scheduledFrames:next*n,done,drops,late,encLate,decLate,errors,errs,
      missed:late+drops+errors,reason,seconds:(end-t0)/1000,startupMs,closeMs,remaining,
      avgCpuPct:100*(final.cpu.usage_usec-base.cpu.usage_usec)/((final.t-base.t)*1000),
      throttledUsec:final.cpu.throttled_usec-base.cpu.throttled_usec,maxMem,maxRSS,maxWorkerRSS,maxProcs,
      latencyMs:Object.fromEntries(Object.entries(lat).map(([k,v])=>[k,summary(v)]))};
  } finally { await Promise.allSettled(ss.map(s=>s.close())); }
}
const report={provider:name,mode,node:process.version,cpuMax:cg('cpu.max'),memoryMax:cg('memory.max'),
  swapMax:cg('memory.swap.max'),decoderFixtureHash:refs.routes[rx].bitstreamSha256,started:new Date().toISOString(),stages:[]};
assert.equal(report.memoryMax,String(512*1024*1024));
const [quota,period]=report.cpuMax.split(' ').map(Number);
assert.equal(quota/period,1);
writeFileSync(out+'-samples.jsonl','');
const save=()=>writeFileSync(out+'.json',JSON.stringify(report,null,2)+'\n');
report.recovery=await recovery();save();
for(const n of [1,2,5,10,15,20,25]){
  console.log('START',name,mode,n,new Date().toISOString());
  const result=await stage(n);
  report.stages.push(result);save();
  console.log('END',name,n,result.seconds,result.missed,result.reason);
  if(result.reason)break;
}
report.finished=new Date().toISOString();save();
