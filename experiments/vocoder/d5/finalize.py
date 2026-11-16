"""Finalize a complete matrix (including ladder stops). Read only archived measurements."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

root = Path(sys.argv[1])
bank = Path(__file__).resolve().parent
text = ['# D5 · Capacidad observada','',
        'Un CPU, 512 MiB y 20 ms por tick. Cada fila corresponde a una escalera independiente. '
        'El límite superior configurado fue 25. Un escalón completo puede haber incumplido deadlines.',
        '', '| Motor | Modo | Mayor completo | Mayor completo con cero misses | '
        'Misses / oportunidades en mayor completo | p99 extremo a extremo ms¹ | CPU media %¹ |',
        '|---|---|---:|---:|---:|---:|---:|']
records = []
last = None
for mode, folder in [('duplex',root),('encode',root/'encode'),('decode',root/'decode')]:
    subprocess.run([sys.executable, str(bank/'summarize.py'), str(folder)],check=True)
    for name in ('opendmr','blip25'):
        r=json.loads((folder/(name+'.json')).read_text())
        start=datetime.fromisoformat(r['started'].replace('Z','+00:00'))
        end=datetime.fromisoformat(r['finished'].replace('Z','+00:00'))
        assert last is None or start >= last, 'overlapping measured ladders'
        last=end
        assert r.get('mode','duplex')==mode
        final=r['stages'][-1]
        assert final['n']==25 or final['reason']
        complete=[s for s in r['stages'] if s['reason'] is None]
        zero=[s['n'] for s in complete if s['missed']==0]
        key={'duplex':'duplexFromTick','encode':'encodeFromTick','decode':'decodeFromTick'}[mode]
        if complete:
            top=complete[-1]
            text.append(f'| {name} | {mode} | {top["n"]} | {max(zero,default="—")} | '
                        f'{top["missed"]} / {top["scheduledFrames"]} | '
                        f'{top["latencyMs"][key]["p99"]:.2f} | {top["avgCpuPct"]:.2f} |')
        else:
            text.append(f'| {name} | {mode} | — | — | — | — | — |')
        records.append(dict(provider=name,mode=mode,completed=[s['n'] for s in complete],
                            zeroMissSteps=zero,guard=final['reason'],attemptedTop=final['n'],
                            inhibited=[n for n in (1,2,5,10,15,20,25) if n>final['n']],
                            missed=sum(s['missed'] for s in r['stages']),
                            errors=sum(s['errors'] for s in r['stages']),stages=len(r['stages'])))
text+=['','¹ Métricas del mayor escalón completo. Misses incluyen omisiones, fallos y trabajos tardíos. '
       'Un resultado de cero misses describe únicamente los 120 s observados en ese escalón.',
       '', '## Cortes y cobertura','']
for r in records:
    text.append(f'- {r["provider"]}, {r["mode"]}: {r["stages"]} escalones ensayados, '
                f'{r["errors"]} errores de operación, {r["missed"]} incumplimientos acumulados. '
                f'Corte: {r["guard"] or "sin activación de guarda"}. Escalones inhibidos: {r["inhibited"]}.')
text+=['','## Evidencia','',
       '[Dúplex](summary.md) · [Solo encode](encode/summary.md) · [Solo decode](decode/summary.md) · '
       '[Entorno](environment.json) · [Método y reproducción](../../d5/README.md).',
       '', 'Los JSON de cada motor incluyen tiempos de arranque/cierre y recuperación. '
       'Los JSONL incluyen CPU, RSS, memoria cgroup, procesos, throttling y eventos OOM por ventana. '
       'El fallo inducido se midió fuera del escalón cronometrado. '
       'El número de canales observado en esta máquina WSL2 no garantiza capacidad RF, de red o de producción.']
(root/'capacity.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
files = sorted(p for p in root.rglob('*') if p.is_file() and p.name!='manifest.json')
(root/'manifest.json').write_text(json.dumps(dict(ladders=records,
    filesSha256={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}),
    indent=2)+'\n',encoding='utf-8')
