# D5 · Resultados de carga encode

Escalones consecutivos por motor. Una sesión y un worker por canal. Latencias en ms; percentiles sobre tareas completadas. CPU en % de un núcleo. Máximos de memoria muestreados en MiB.

## opendmr

| Canales | s | Completados / previstos¹ | Tarde / omitidos / errores | Miss % | Encode desde tick p50/p95/p99 | Decode desde despacho p50/p95/p99 | Trabajo desde tick p50/p95/p99 |
|---:|---:|---:|---:|---:|---|---|---|
| 1 | 120.00 | 6000/6000 | 0/0/0 | 0.000 | 0.91/1.50/2.20 | — | 0.91/1.50/2.20 |
| 2 | 120.00 | 12000/12000 | 0/0/0 | 0.000 | 1.04/1.65/2.33 | — | 1.04/1.65/2.33 |
| 5 | 120.00 | 30000/30000 | 0/0/0 | 0.000 | 1.10/1.73/2.24 | — | 1.10/1.73/2.24 |
| 10 | 120.00 | 60000/60000 | 0/0/0 | 0.000 | 1.18/1.75/2.36 | — | 1.18/1.75/2.36 |
| 15 | 120.00 | 90000/90000 | 0/0/0 | 0.000 | 1.30/2.00/2.66 | — | 1.30/2.00/2.66 |
| 20 | 120.00 | 120000/120000 | 0/0/0 | 0.000 | 1.43/2.08/2.81 | — | 1.43/2.08/2.81 |
| 25 | 120.00 | 150000/150000 | 0/0/0 | 0.000 | 1.55/2.25/2.94 | — | 1.55/2.25/2.94 |

¹ Oportunidades hasta el corte; las no programadas después de una parada quedan fuera.

| Canales | CPU media | RSS workers / total | Memoria cgroup | Procesos máx. | Arranque / cierre ms |
|---:|---:|---:|---:|---:|---:|
| 1 | 2.77 | 1.9 / 65.4 | 151.1 | 2 | 0.78 / 0.80 |
| 2 | 4.88 | 3.8 / 68.2 | 150.6 | 3 | 1.75 / 0.74 |
| 5 | 12.80 | 9.5 / 76.1 | 147.8 | 6 | 3.49 / 0.96 |
| 10 | 24.93 | 18.9 / 88.5 | 152.1 | 11 | 6.21 / 0.82 |
| 15 | 40.69 | 28.4 / 101.4 | 158.3 | 16 | 8.47 / 1.00 |
| 20 | 55.07 | 37.0 / 109.7 | 161.2 | 21 | 16.44 / 1.72 |
| 25 | 67.33 | 53.8 / 128.0 | 166.0 | 26 | 111.81 / 2.38 |

Escalones completos: [1, 2, 5, 10, 15, 20, 25]. Completos con cero incumplimientos: [1, 2, 5, 10, 15, 20, 25].
Último motivo de corte: None. Docker exit=0, OOMKilled=False.
Fallo inducido: WORKER en 0.83 ms; hermano operativo, 2.23 ms hasta primer encode de reemplazo.

## blip25

| Canales | s | Completados / previstos¹ | Tarde / omitidos / errores | Miss % | Encode desde tick p50/p95/p99 | Decode desde despacho p50/p95/p99 | Trabajo desde tick p50/p95/p99 |
|---:|---:|---:|---:|---:|---|---|---|
| 1 | 120.00 | 6000/6000 | 0/0/0 | 0.000 | 0.71/1.25/2.21 | — | 0.71/1.25/2.21 |
| 2 | 120.00 | 12000/12000 | 0/0/0 | 0.000 | 0.75/1.24/2.05 | — | 0.75/1.24/2.05 |
| 5 | 120.00 | 30000/30000 | 0/0/0 | 0.000 | 0.77/1.32/2.17 | — | 0.77/1.32/2.17 |
| 10 | 120.00 | 60000/60000 | 0/0/0 | 0.000 | 0.91/1.43/2.48 | — | 0.91/1.43/2.48 |
| 15 | 120.00 | 90000/90000 | 0/0/0 | 0.000 | 1.13/1.54/2.68 | — | 1.13/1.54/2.68 |
| 20 | 120.00 | 120000/120000 | 0/0/0 | 0.000 | 1.28/1.71/2.80 | — | 1.28/1.71/2.80 |
| 25 | 120.00 | 150000/150000 | 0/0/0 | 0.000 | 1.02/1.79/2.62 | — | 1.02/1.79/2.62 |

¹ Oportunidades hasta el corte; las no programadas después de una parada quedan fuera.

| Canales | CPU media | RSS workers / total | Memoria cgroup | Procesos máx. | Arranque / cierre ms |
|---:|---:|---:|---:|---:|---:|
| 1 | 1.55 | 1.2 / 65.3 | 204.2 | 2 | 1.06 / 2.20 |
| 2 | 2.16 | 3.0 / 68.7 | 160.9 | 3 | 4.49 / 0.56 |
| 5 | 4.65 | 9.1 / 74.0 | 149.6 | 6 | 6.22 / 1.75 |
| 10 | 9.14 | 21.3 / 93.7 | 159.9 | 11 | 14.98 / 0.72 |
| 15 | 12.69 | 18.2 / 94.3 | 165.2 | 16 | 8.85 / 2.11 |
| 20 | 16.56 | 33.8 / 107.5 | 164.6 | 21 | 19.22 / 1.18 |
| 25 | 19.46 | 29.7 / 110.4 | 170.1 | 26 | 68.19 / 1.32 |

Escalones completos: [1, 2, 5, 10, 15, 20, 25]. Completos con cero incumplimientos: [1, 2, 5, 10, 15, 20, 25].
Último motivo de corte: None. Docker exit=0, OOMKilled=False.
Fallo inducido: WORKER en 1.34 ms; hermano operativo, 2.47 ms hasta primer encode de reemplazo.

