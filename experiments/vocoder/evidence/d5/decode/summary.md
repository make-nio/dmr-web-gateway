# D5 · Resultados de carga decode

Escalones consecutivos por motor. Una sesión y un worker por canal. Latencias en ms; percentiles sobre tareas completadas. CPU en % de un núcleo. Máximos de memoria muestreados en MiB.

## opendmr

| Canales | s | Completados / previstos¹ | Tarde / omitidos / errores | Miss % | Encode desde tick p50/p95/p99 | Decode desde despacho p50/p95/p99 | Trabajo desde tick p50/p95/p99 |
|---:|---:|---:|---:|---:|---|---|---|
| 1 | 120.00 | 6000/6000 | 0/0/0 | 0.000 | — | 0.15/0.24/1.43 | 0.71/1.18/2.11 |
| 2 | 120.00 | 12000/12000 | 0/0/0 | 0.000 | — | 0.12/0.22/1.49 | 0.68/1.17/2.20 |
| 5 | 120.00 | 30000/30000 | 0/0/0 | 0.000 | — | 0.13/0.29/1.56 | 0.71/1.21/2.32 |
| 10 | 120.00 | 60000/60000 | 0/0/0 | 0.000 | — | 0.20/0.45/1.70 | 0.84/1.35/2.42 |
| 15 | 120.00 | 90000/90000 | 0/0/0 | 0.000 | — | 0.28/0.50/1.72 | 0.94/1.41/2.46 |
| 20 | 120.00 | 120000/120000 | 0/0/0 | 0.000 | — | 0.36/0.67/1.82 | 1.17/1.64/2.67 |
| 25 | 120.00 | 150000/150000 | 0/0/0 | 0.000 | — | 0.43/0.75/1.94 | 1.28/1.79/2.79 |

¹ Oportunidades hasta el corte; las no programadas después de una parada quedan fuera.

| Canales | CPU media | RSS workers / total | Memoria cgroup | Procesos máx. | Arranque / cierre ms |
|---:|---:|---:|---:|---:|---:|
| 1 | 1.23 | 1.9 / 66.3 | 202.7 | 2 | 0.70 / 0.79 |
| 2 | 1.49 | 3.8 / 68.5 | 179.1 | 3 | 1.39 / 2.18 |
| 5 | 2.46 | 17.6 / 83.1 | 149.6 | 6 | 9.84 / 2.25 |
| 10 | 4.20 | 28.9 / 101.6 | 157.8 | 11 | 12.97 / 0.74 |
| 15 | 5.88 | 28.6 / 105.8 | 165.0 | 16 | 8.13 / 0.90 |
| 20 | 7.90 | 38.1 / 115.1 | 167.8 | 21 | 10.08 / 1.25 |
| 25 | 9.57 | 47.5 / 123.3 | 167.1 | 26 | 87.31 / 1.60 |

Escalones completos: [1, 2, 5, 10, 15, 20, 25]. Completos con cero incumplimientos: [1, 2, 5, 10, 15, 20, 25].
Último motivo de corte: None. Docker exit=0, OOMKilled=False.
Fallo inducido: WORKER en 1.36 ms; hermano operativo, 2.87 ms hasta primer encode de reemplazo.

## blip25

| Canales | s | Completados / previstos¹ | Tarde / omitidos / errores | Miss % | Encode desde tick p50/p95/p99 | Decode desde despacho p50/p95/p99 | Trabajo desde tick p50/p95/p99 |
|---:|---:|---:|---:|---:|---|---|---|
| 1 | 120.00 | 6000/6000 | 0/0/0 | 0.000 | — | 0.16/0.29/1.56 | 0.73/1.21/2.24 |
| 2 | 120.00 | 12000/12000 | 0/0/0 | 0.000 | — | 0.14/0.26/1.54 | 0.71/1.19/2.18 |
| 5 | 120.00 | 30000/30000 | 0/0/0 | 0.000 | — | 0.14/0.30/1.53 | 0.75/1.23/2.29 |
| 10 | 120.00 | 60000/60000 | 0/0/0 | 0.000 | — | 0.20/0.41/1.68 | 0.86/1.34/2.51 |
| 15 | 120.00 | 90000/90000 | 0/0/0 | 0.000 | — | 0.29/0.55/1.82 | 0.95/1.44/2.57 |
| 20 | 120.00 | 120000/120000 | 0/0/0 | 0.000 | — | 0.36/0.61/1.82 | 1.17/1.67/2.71 |
| 25 | 120.00 | 150000/150000 | 0/0/0 | 0.000 | — | 0.44/0.78/1.91 | 1.48/1.87/2.99 |

¹ Oportunidades hasta el corte; las no programadas después de una parada quedan fuera.

| Canales | CPU media | RSS workers / total | Memoria cgroup | Procesos máx. | Arranque / cierre ms |
|---:|---:|---:|---:|---:|---:|
| 1 | 1.32 | 1.2 / 65.7 | 157.6 | 2 | 0.74 / 0.61 |
| 2 | 1.76 | 2.5 / 68.3 | 159.1 | 3 | 1.43 / 0.68 |
| 5 | 3.01 | 6.1 / 78.6 | 167.2 | 6 | 3.04 / 0.80 |
| 10 | 4.98 | 12.1 / 90.0 | 171.0 | 11 | 6.61 / 1.14 |
| 15 | 7.60 | 18.2 / 99.9 | 174.5 | 16 | 8.22 / 1.48 |
| 20 | 9.13 | 24.2 / 107.6 | 172.5 | 21 | 10.46 / 1.50 |
| 25 | 11.69 | 30.2 / 111.5 | 174.8 | 26 | 100.05 / 1.44 |

Escalones completos: [1, 2, 5, 10, 15, 20, 25]. Completos con cero incumplimientos: [1, 2, 5, 10, 15, 20, 25].
Último motivo de corte: None. Docker exit=0, OOMKilled=False.
Fallo inducido: WORKER en 1.13 ms; hermano operativo, 2.63 ms hasta primer encode de reemplazo.

