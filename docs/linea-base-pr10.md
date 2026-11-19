# Línea base reproducible del PR #10 (16-nov-2026)

Base: commit `3a7deaf54f4d0ebddb45bae444e3cf9867515379` (HEAD del PR #10, banco AMBE+2 y D4).
Rama de trabajo: `dev/linea-base-pr10`. No se modificó ningún fixture: `git diff` sobre
`experiments/vocoder/evidence/` vacío.

Estado: **final** (16-nov-2026). Lo que no se corrió está listado al final y no se da por probado.

## Entorno donde se midió

| Componente | Versión |
|---|---|
| Node.js | 22.22.1 |
| npm | 10.9.4 |
| Docker Engine / Compose (Linux, WSL2) | 29.0.0 / v2.40.3 |
| Python (WSL2) | 3.12.3 |

El Node de WSL2 es 20.x y no sirve para el proyecto (pide Node 22): hay que usar un Node 22.

## Receta: control Homebrew contra mock

```bash
git clone https://github.com/make-nio/dmr-web-gateway.git
cd dmr-web-gateway
git fetch origin pull/10/head:review-pr10
git checkout review-pr10
git rev-parse HEAD        # debe dar 3a7deaf54f4d0ebddb45bae444e3cf9867515379
npm ci                    # ~10 s
npm test                  # compila y corre la suite: ~4 s
npm run build
python3 scripts/verify-evidence-hashes.py   # hashes de los fixtures (ver más abajo)
```

Resultado medido: `npm ci` sin errores; `npm test` **9/9** (0 fallos, 0 cancelados, 0 omitidos),
igual que el traspaso.

## Verificación de hashes de los fixtures

```bash
python3 scripts/verify-evidence-hashes.py     # sólo lectura; sale 1 si algún hash no coincide
```

Resultado medido: **19/19** hashes verificados, 0 fallos, 10 no verificables. Cubre los
manifiestos `evidence/d3b` y `evidence/d3c`: los WAV (archivo y datos PCM, sin los 44 bytes de
cabecera), las trazas `*-bits.jsonl`, `c5/frames.jsonl`, `d3b/coordinator.md`, las 4 fuentes de
`bank/` y el PCM de entrada de d3b (`evidence/c7/Par-01-B.wav`). Se comprobó que el script
falla (salida 1) si se altera un archivo.

No verificables desde este repo (no son archivos versionados), y el script los lista como tales:
`inputPcmSha256`, `sourceSha256` y `sourceWavSha256` de d3c (entradas externas), los
`bitstreamSha256` de d3b y los `framesSha256` de d3c (derivados) y los tres binarios compilados
de d3b (`vocoder-spike-worker`, `libblip25_vocoder-*.rlib`, `libopendmr.a`).

`evidence/d4/offline-validation.txt` no contiene hashes SHA-256: es el log de 12 casos
(12 ok, 0 fallos). Los fixtures D3b los verifican los propios casos 11 y 12 al correr D4.

## Build y D4 en WSL2 (Linux)

Se corren de a un comando, desde Git Bash en Windows. El `</dev/null` va **afuera** de las
comillas: sin él, el comando de WSL2 no termina.

```bash
wsl -e bash -lc 'cd <ruta-del-clon> && npm run build' </dev/null
wsl -e bash -lc 'cd <ruta-del-clon> && bash experiments/vocoder/d4/validate.sh' </dev/null
```

| Paso | Resultado medido | Tiempo |
|---|---|---|
| `npm run build` (`tsc`) | salida 0, sin cambios en git | 3 s |
| `validate.sh` de D4 | salida 0; **12/12** casos (0 fallos, 0 omitidos); `bench CLI simulated/opendmr/blip25: 9 bytes` | 11 s |

D4 usa el Docker de WSL2 con dos imágenes que ya deben estar **localmente**, fijadas por
digest en el script: `dmr-vocoder-spike` (`sha256:30e7ca9f…7edab`) y `node:22`
(`sha256:363e1587…2d7`). Corre sin red, de sólo lectura y sin privilegios. No hizo falta
ningún cambio de configuración de git.

Latencias de D4 en esta máquina (p95 total, ms; 1.000 tramas por motor, 1 CPU y 512 MiB):

| Motor | encode | decode |
|---|---|---|
| OpenDMR | 0,585 (traspaso: 0,510) | 0,213 (traspaso: 0,169) |
| BLIP25 | 0,273 (traspaso: 0,231) | 0,213 (traspaso: 0,187) |

Son entre 10 % y 26 % más altas que las del traspaso, en otro equipo. Son latencias de banco,
no capacidad de 25 canales.

### Problemas de arranque encontrados

- El WSL2 trae Node 20 y el proyecto pide Node 22. El build (`tsc`) y D4 funcionan igual,
  porque D4 corre con el `node` de la imagen `node:22`. Para `npm ci` y `npm test` se usó
  Node 22.22.1 en Windows.
- `validate.sh` no corre en una máquina sin las dos imágenes locales (usa `--pull never`).
- Desde Git Bash hay que cerrar la entrada estándar del comando de WSL2 (`</dev/null`).

## Suite Docker y soak (imagen base cargada localmente por digest)

Con `node:22-alpine` ya presente por digest (`sha256:0e175475…af8202`), en WSL2:

```bash
wsl -e bash -lc 'cd <ruta-del-clon> && python3 scripts/validate-docker.py' </dev/null
wsl -e bash -lc 'cd <ruta-del-clon> && python3 scripts/validate-docker.py --soak' </dev/null
```

| Paso | Resultado medido | Tiempo |
|---|---|---|
| `validate-docker.py` | salida 0; uid/capacidades/red/solo lectura/secreto PASS (gateway y simulador); arranque sano; pérdida del master: proceso sano y readiness caída; reconexión sana; sin marcadores en logs; SIGTERM con salida 0 | 67 s |
| `validate-docker.py --soak` (600 s) | salida 0; `passed: true`; 0 reconexiones inesperadas; 60 muestras; memoria máx. gateway 50,3 MiB y simulador 37,2 MiB; CPU máx. 1,12 % y 0,83 % | ~11 min |

El soak reescribe `docs/docker-soak.json` (archivo versionado): se restauró con `git restore`
y `git diff` sobre `evidence/` sigue vacío. El build corre `npm ci` dentro de Docker, por lo
que necesita acceso al registro de npm.

## Lo que NO se corrió (no se da por probado)

- `npm run soak` por separado.
- El banco original del vocoder (`experiments/vocoder`, `bench.py`).
