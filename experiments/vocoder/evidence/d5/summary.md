# D5 · Resultados de carga duplex

Escalones consecutivos por motor. Una sesión y un worker por canal. Latencias en ms; percentiles sobre tareas completadas. CPU en % de un núcleo. Máximos de memoria muestreados en MiB.

## opendmr

| Canales | s | Completados / previstos¹ | Tarde / omitidos / errores | Miss % | Encode desde tick p50/p95/p99 | Decode desde despacho p50/p95/p99 | Trabajo desde tick p50/p95/p99 |
|---:|---:|---:|---:|---:|---|---|---|
| 1 | 120.00 | 6000/6000 | 0/0/0 | 0.000 | 1.02/1.54/2.08 | 0.12/0.18/0.25 | 1.14/1.68/2.22 |
| 2 | 120.00 | 12000/12000 | 0/0/0 | 0.000 | 1.04/1.62/2.18 | 0.11/0.18/0.25 | 1.16/1.75/2.29 |
| 5 | 120.00 | 30000/30000 | 0/0/0 | 0.000 | 1.19/1.83/2.26 | 0.11/0.19/0.29 | 1.31/1.95/2.41 |
| 10 | 120.00 | 60000/60000 | 0/0/0 | 0.000 | 1.24/1.92/2.56 | 0.12/0.27/0.38 | 1.38/2.07/2.86 |
| 15 | 120.00 | 90000/90000 | 0/0/0 | 0.000 | 1.48/2.22/2.90 | 0.14/0.34/0.49 | 1.64/2.38/3.27 |
| 20 | 120.00 | 120000/120000 | 0/0/0 | 0.000 | 1.75/2.54/3.07 | 0.22/0.58/0.81 | 2.01/2.78/3.56 |
| 25 | 120.00 | 150000/150000 | 0/0/0 | 0.000 | 1.72/2.65/3.15 | 0.27/0.72/0.98 | 2.04/2.95/3.66 |

¹ Oportunidades hasta el corte; las no programadas después de una parada quedan fuera.

| Canales | CPU media | RSS workers / total | Memoria cgroup | Procesos máx. | Arranque / cierre ms |
|---:|---:|---:|---:|---:|---:|
| 1 | 3.40 | 1.9 / 65.2 | 196.0 | 2 | 0.67 / 0.59 |
| 2 | 6.17 | 3.7 / 67.3 | 181.8 | 3 | 1.68 / 0.62 |
| 5 | 16.04 | 9.2 / 78.0 | 159.0 | 6 | 7.32 / 0.77 |
| 10 | 31.36 | 18.4 / 87.8 | 161.7 | 11 | 5.23 / 1.17 |
| 15 | 50.97 | 28.0 / 100.1 | 167.7 | 16 | 7.36 / 0.86 |
| 20 | 63.85 | 37.0 / 117.3 | 170.3 | 21 | 10.48 / 1.20 |
| 25 | 73.32 | 46.7 / 128.5 | 174.0 | 26 | 96.94 / 1.63 |

Escalones completos: [1, 2, 5, 10, 15, 20, 25]. Completos con cero incumplimientos: [1, 2, 5, 10, 15, 20, 25].
Último motivo de corte: None. Docker exit=0, OOMKilled=False.
Fallo inducido: WORKER en 1.06 ms; hermano operativo, 2.99 ms hasta primer encode de reemplazo.

## blip25

| Canales | s | Completados / previstos¹ | Tarde / omitidos / errores | Miss % | Encode desde tick p50/p95/p99 | Decode desde despacho p50/p95/p99 | Trabajo desde tick p50/p95/p99 |
|---:|---:|---:|---:|---:|---|---|---|
| 1 | 120.00 | 6000/6000 | 0/0/0 | 0.000 | 0.78/1.24/2.12 | 0.14/0.22/0.27 | 0.92/1.40/2.27 |
| 2 | 120.00 | 12000/12000 | 0/0/0 | 0.000 | 0.83/1.27/2.25 | 0.12/0.21/0.27 | 0.96/1.42/2.38 |
| 5 | 120.00 | 30000/30000 | 0/0/0 | 0.000 | 0.80/1.37/2.29 | 0.13/0.24/0.35 | 0.95/1.52/2.43 |
| 10 | 120.00 | 60000/60000 | 0/0/0 | 0.000 | 1.20/1.69/2.68 | 0.17/0.38/0.46 | 1.40/1.87/2.92 |
| 15 | 120.00 | 90000/90000 | 0/0/0 | 0.000 | 1.24/1.92/2.76 | 0.24/0.45/0.59 | 1.49/2.13/3.13 |
| 20 | 120.00 | 120000/120000 | 0/0/0 | 0.000 | 1.51/2.25/3.00 | 0.31/0.61/0.77 | 1.84/2.48/3.47 |
| 25 | 120.00 | 150000/150000 | 0/0/0 | 0.000 | 1.74/2.56/3.27 | 0.40/0.77/0.89 | 2.16/2.82/3.86 |

¹ Oportunidades hasta el corte; las no programadas después de una parada quedan fuera.

| Canales | CPU media | RSS workers / total | Memoria cgroup | Procesos máx. | Arranque / cierre ms |
|---:|---:|---:|---:|---:|---:|
| 1 | 2.36 | 1.2 / 63.9 | 202.4 | 2 | 0.66 / 0.64 |
| 2 | 3.63 | 2.4 / 68.4 | 188.2 | 3 | 2.80 / 0.84 |
| 5 | 7.45 | 5.8 / 75.6 | 195.7 | 6 | 4.33 / 0.98 |
| 10 | 13.39 | 11.7 / 85.5 | 190.3 | 11 | 6.58 / 0.91 |
| 15 | 19.50 | 20.1 / 94.5 | 178.9 | 16 | 8.08 / 0.76 |
| 20 | 25.13 | 23.5 / 103.1 | 180.2 | 21 | 9.39 / 1.33 |
| 25 | 32.21 | 29.1 / 109.6 | 181.3 | 26 | 80.39 / 1.32 |

Escalones completos: [1, 2, 5, 10, 15, 20, 25]. Completos con cero incumplimientos: [1, 2, 5, 10, 15, 20, 25].
Último motivo de corte: None. Docker exit=0, OOMKilled=False.
Fallo inducido: WORKER en 1.03 ms; hermano operativo, 2.04 ms hasta primer encode de reemplazo.

