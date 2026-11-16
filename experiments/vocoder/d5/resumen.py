#!/usr/bin/env python3
"""Resume los JSON de una corrida de D5 en una tabla Markdown (solo lectura).

    python3 experiments/vocoder/d5/resumen.py experiments/vocoder/evidence/d5/runs
"""
import json
import re
import sys
from pathlib import Path

ORDEN = {"rx": 0, "tx": 1, "duplex": 2}


def clave(r):
    return (r["provider"], ORDEN[r["mode"]], r["channels"], r["_rep"])


def main(carpeta):
    filas = []
    for f in Path(carpeta).glob("*.json"):
        r = json.loads(f.read_text())
        m = re.search(r"-rep(\d+)\.json$", f.name)
        r["_rep"] = int(m.group(1)) if m else 0
        filas.append(r)
    filas.sort(key=clave)
    print("| motor | modo | canales | corrida | enc p50/p95/p99 ms | dec p50/p95/p99 ms | entrega p95/p99 ms | fuera de plazo | CPU % de 1 núcleo | mem Δ MiB | procesos | arranque máx ms | cierre máx ms | fallos | parada |")
    print("|---|---|--:|--|--|--|--|--:|--:|--:|--:|--:|--:|--:|--|")

    def tri(s):
        return "-" if not s["count"] else f'{s["p50"]:.2f}/{s["p95"]:.2f}/{s["p99"]:.2f}'

    for r in filas:
        l = r["latencyMs"]
        corrida = "rep%d" % r["_rep"] if r["_rep"] else ("base" if r["channels"] == 10 else "")
        cpu = "-" if r["cpuPercentOfOneCpu"] is None else "%.0f" % r["cpuPercentOfOneCpu"]
        mem = "-" if r["memDeltaMaxMiB"] is None else "%.0f" % r["memDeltaMaxMiB"]
        print(f'| {r["provider"]} | {r["mode"]} | {r["channels"]} | {corrida} | {tri(l["encode"])} | {tri(l["decode"])} | '
              f'{l["delivery"]["p95"]:.2f}/{l["delivery"]["p99"]:.2f} | {r["lateFrames"]}/{r["framesDelivered"]} | {cpu} | {mem} | '
              f'{r["pidsMax"]} | {r["startupMs"]["max"]:.0f} | {r["closeMs"]["max"]:.0f} | {r["failures"]} | {r["stopReason"] or ""} |')
    # Variación entre las tres corridas del escalón repetido (mín–máx).
    grupos = {}
    for r in filas:
        if r["channels"] == 10 and any(x["_rep"] for x in filas if x["provider"] == r["provider"] and x["mode"] == r["mode"] and x["channels"] == 10):
            grupos.setdefault((r["provider"], r["mode"]), []).append(r)
    if grupos:
        print("\nVariación en 10 canales (mín–máx entre corridas, ms; CPU en %):\n")
        print("| motor | modo | corridas | enc p95 | dec p95 | entrega p95 | entrega p99 | CPU % |")
        print("|---|---|--:|--|--|--|--|--|")

        def rango(valores):
            valores = [v for v in valores if v is not None and v == v]
            return "-" if not valores else f"{min(valores):.2f}–{max(valores):.2f}"

        for (p, m), rs in sorted(grupos.items(), key=lambda kv: (kv[0][0], ORDEN[kv[0][1]])):
            print(f'| {p} | {m} | {len(rs)} | {rango([r["latencyMs"]["encode"]["p95"] for r in rs])} | '
                  f'{rango([r["latencyMs"]["decode"]["p95"] for r in rs])} | {rango([r["latencyMs"]["delivery"]["p95"] for r in rs])} | '
                  f'{rango([r["latencyMs"]["delivery"]["p99"] for r in rs])} | {rango([r["cpuPercentOfOneCpu"] for r in rs])} |')
    print(f"\n{len(filas)} archivos,{sum(1 for r in filas if not r['_rep'])} mediciones base "
          f"+ {sum(1 for r in filas if r['_rep'])} repeticiones.")


if __name__ == "__main__":
    main(sys.argv[1])
