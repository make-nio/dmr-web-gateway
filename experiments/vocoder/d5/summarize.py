"""Audit the saved measurements; no Docker or vocoder execution."""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
mode = root.name if root.name in ('encode','decode') else 'duplex'
lines = ['# D5 · Resultados de carga '+mode,'',
         'Escalones consecutivos por motor. Una sesión y un worker por canal. '
         'Latencias en ms; percentiles sobre tareas completadas. CPU en % de un núcleo. '
         'Máximos de memoria muestreados en MiB.','']
for name in ('opendmr','blip25'):
    report = json.loads((root/(name+'.json')).read_text(encoding='utf-8-sig'))
    state = json.loads((root/(name+'-container.json')).read_text(encoding='utf-8-sig'))
    samples = [json.loads(line) for line in (root/(name+'-samples.jsonl')).read_text().splitlines()]
    stages = report['stages']
    assert [s['n'] for s in stages] == [1,2,5,10,15,20,25][:len(stages)]
    assert report['memoryMax']=='536870912' and report['swapMax']=='0'
    lines += ['## '+name, '', '| Canales | s | Completados / previstos¹ | Tarde / omitidos / errores | '
              'Miss % | Encode desde tick p50/p95/p99 | Decode desde despacho p50/p95/p99 | Trabajo desde tick p50/p95/p99 |',
              '|---:|---:|---:|---:|---:|---|---|---|']
    for s in stages:
        n=s['n']
        count=s['scheduledFrames']
        assert s['done']+s['drops']+s['errors']==count
        assert s['missed']==s['late']+s['drops']+s['errors']
        total_key = {'duplex':'duplexFromTick','encode':'encodeFromTick','decode':'decodeFromTick'}[mode]
        assert s['remaining']==0 and s['latencyMs'][total_key]['n']==s['done']
        rows=[r for r in samples if r['n']==n]
        assert rows and rows[-1]['done']==s['done']
        if s['reason'] is None:
            assert s['seconds'] >= 119.999 and count==n*6000
            assert all(r['workers']==n for r in rows)
        def lat(key):
            if not s['latencyMs'][key]['n']:
                return '—'
            return '/'.join(f'{s["latencyMs"][key][p]:.2f}' for p in ('p50','p95','p99'))
        lines.append(f'| {n} | {s["seconds"]:.2f} | {s["done"]}/{count} | '
                     f'{s["late"]}/{s["drops"]}/{s["errors"]} | {100*s["missed"]/count:.3f} | '
                     f'{lat("encodeFromTick")} | {lat("decodeFromDispatch")} | {lat(total_key)} |')
    lines += ['','¹ Oportunidades hasta el corte; las no programadas después de una parada quedan fuera.',
              '', '| Canales | CPU media | RSS workers / total | Memoria cgroup | Procesos máx. | Arranque / cierre ms |',
              '|---:|---:|---:|---:|---:|---:|']
    for s in stages:
        lines.append(f'| {s["n"]} | {s["avgCpuPct"]:.2f} | {s["maxWorkerRSS"]/2**20:.1f} / '
                     f'{s["maxRSS"]/2**20:.1f} | {s["maxMem"]/2**20:.1f} | {s["maxProcs"]} | '
                     f'{s["startupMs"]:.2f} / {s["closeMs"]:.2f} |')
    clean=[s['n'] for s in stages if s['reason'] is None and s['missed']==0]
    complete=[s['n'] for s in stages if s['reason'] is None]
    r=report['recovery']
    lines+=['',f'Escalones completos: {complete}. Completos con cero incumplimientos: {clean}.',
            f'Último motivo de corte: {stages[-1]["reason"] if stages else "sin escalón finalizado"}. '
            f'Docker exit={state["ExitCode"]}, OOMKilled={state["OOMKilled"]}.',
            f'Fallo inducido: {r["failure"]} en {r["detectedMs"]:.2f} ms; hermano operativo, '
            f'{r["timeToFreshFrameMs"]:.2f} ms hasta primer encode de reemplazo.', '']
(root/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
