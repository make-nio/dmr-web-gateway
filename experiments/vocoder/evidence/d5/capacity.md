# D5 · Capacidad observada

Un CPU, 512 MiB y 20 ms por tick. Cada fila corresponde a una escalera independiente. El límite superior configurado fue 25. Un escalón completo puede haber incumplido deadlines.

| Motor | Modo | Mayor completo | Mayor completo con cero misses | Misses / oportunidades en mayor completo | p99 extremo a extremo ms¹ | CPU media %¹ |
|---|---|---:|---:|---:|---:|---:|
| opendmr | duplex | 25 | 25 | 0 / 150000 | 3.66 | 73.32 |
| blip25 | duplex | 25 | 25 | 0 / 150000 | 3.86 | 32.21 |
| opendmr | encode | 25 | 25 | 0 / 150000 | 2.94 | 67.33 |
| blip25 | encode | 25 | 25 | 0 / 150000 | 2.62 | 19.46 |
| opendmr | decode | 25 | 25 | 0 / 150000 | 2.79 | 9.57 |
| blip25 | decode | 25 | 25 | 0 / 150000 | 2.99 | 11.69 |

¹ Métricas del mayor escalón completo. Misses incluyen omisiones, fallos y trabajos tardíos. Un resultado de cero misses describe únicamente los 120 s observados en ese escalón.

## Cortes y cobertura

- opendmr, duplex: 7 escalones ensayados, 0 errores de operación, 0 incumplimientos acumulados. Corte: sin activación de guarda. Escalones inhibidos: [].
- blip25, duplex: 7 escalones ensayados, 0 errores de operación, 0 incumplimientos acumulados. Corte: sin activación de guarda. Escalones inhibidos: [].
- opendmr, encode: 7 escalones ensayados, 0 errores de operación, 0 incumplimientos acumulados. Corte: sin activación de guarda. Escalones inhibidos: [].
- blip25, encode: 7 escalones ensayados, 0 errores de operación, 0 incumplimientos acumulados. Corte: sin activación de guarda. Escalones inhibidos: [].
- opendmr, decode: 7 escalones ensayados, 0 errores de operación, 0 incumplimientos acumulados. Corte: sin activación de guarda. Escalones inhibidos: [].
- blip25, decode: 7 escalones ensayados, 0 errores de operación, 0 incumplimientos acumulados. Corte: sin activación de guarda. Escalones inhibidos: [].

## Evidencia

[Dúplex](summary.md) · [Solo encode](encode/summary.md) · [Solo decode](decode/summary.md) · [Entorno](environment.json) · [Método y reproducción](../../d5/README.md).

Los JSON de cada motor incluyen tiempos de arranque/cierre y recuperación. Los JSONL incluyen CPU, RSS, memoria cgroup, procesos, throttling y eventos OOM por ventana. El fallo inducido se midió fuera del escalón cronometrado. El número de canales observado en esta máquina WSL2 no garantiza capacidad RF, de red o de producción.
