#!/usr/bin/env python3
"""Contrasta la escalera dúplex reportada por Codex con (a) su repetición con su propio comando y
(b) el banco independiente, en una tabla Markdown. Solo lectura.

    python3 experiments/vocoder/d5-independiente/contraste.py
"""
import json
from pathlib import Path

V = Path(__file__).resolve().parents[1]
CODEX = V / "evidence/d5"
REPRO = V / "evidence/d5-independiente/repro-codex"
MIO = V / "evidence/d5-independiente/runs"
PASOS = [1, 2, 5, 10, 15, 20, 25]


def etapas(path):
    return {s["n"]: s for s in json.loads(path.read_text())["stages"]}


def f(x):
    return f"{x:.2f}"


print("Entrega dúplex desde el tick (p95 / p99 ms), tramas fuera de plazo y CPU media (% de 1 núcleo).")
print("«Codex» = reportada (commit e7ba4f0); «Repetición» = su comando sin modificar, corrido por el dev; "
      "«Independiente» = banco D5-independiente (RX/TX/dúplex propios, pacing con setTimeout).\n")
for motor in ("opendmr", "blip25"):
    c, r = etapas(CODEX / f"{motor}.json"), etapas(REPRO / f"{motor}.json")
    print(f"### {motor}\n")
    print("| canales | Codex p95/p99 | Repetición p95/p99 | Independiente p95/p99 | tarde+omitidas Codex / Repet. / Indep. | CPU Codex / Repet. / Indep. |")
    print("|--:|--|--|--|--|--|")
    for n in PASOS:
        m = json.loads((MIO / f"{motor}-duplex-{n}ch.json").read_text())
        d = lambda s: f'{f(s["latencyMs"]["duplexFromTick"]["p95"])}/{f(s["latencyMs"]["duplexFromTick"]["p99"])}'
        miss = lambda s: f'{s["late"]}+{s["drops"]}'
        print(f'| {n} | {d(c[n])} | {d(r[n])} | {f(m["latencyMs"]["delivery"]["p95"])}/{f(m["latencyMs"]["delivery"]["p99"])} | '
              f'{miss(c[n])} / {miss(r[n])} / {m["lateFrames"]}+0 | '
              f'{c[n]["avgCpuPct"]:.1f} / {r[n]["avgCpuPct"]:.1f} / {m["cpuPercentOfOneCpu"]:.1f} |')
    print()
