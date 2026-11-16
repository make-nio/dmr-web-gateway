# Línea base reproducible del PR #10 (borrador, 16-nov-2026)

Base: commit `3a7deaf54f4d0ebddb45bae444e3cf9867515379` (HEAD del PR #10, banco AMBE+2 y D4).
Rama de trabajo: `dev/linea-base-pr10`. No se modificó ningún fixture: `git diff` sobre
`experiments/vocoder/evidence/` vacío.

Estado: **PARCIAL**. Lo que no se corrió está listado al final y no se da por probado.

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
```

Resultado medido: `npm ci` sin errores; `npm test` **9/9** (0 fallos, 0 cancelados, 0 omitidos),
igual que el traspaso.

## Verificación de hashes de los fixtures (script en Python, sólo lectura)

Todo hash del manifiesto que corresponde a un archivo versionado coincide:

- `evidence/d3b/manifest.json`: `RX.wav`, `TX.wav`, `RX-bits.jsonl`, `TX-bits.jsonl`,
  `c5/frames.jsonl`, `d3b/coordinator.md` y las 4 fuentes de `bank/` (`tap.cpp`, `pack.cpp`,
  `check.cpp`, `check.rs`). Además, `pcmSha256` de RX y TX coincide con los datos PCM
  (44 bytes de cabecera descartados) de cada WAV.
- `evidence/d3c/manifest.json`: `Rosario-01.wav`, `Rosario-02.wav`, `RX-bits.jsonl`,
  `TX-bits.jsonl`, y `outputPcmSha256` de RX y TX contra los datos de cada WAV.

No verificables desde este repo (no son archivos versionados): `inputPcmSha256` de d3b y d3c,
`bitstreamSha256` de d3b, `framesSha256` de d3c, `sourceSha256` y `sourceWavSha256` de d3c
(son entradas externas o derivadas) y los tres binarios compilados de d3b (`vocoder-spike-worker`,
`libblip25_vocoder-*.rlib`, `libopendmr.a`).

`evidence/d4/offline-validation.txt` no contiene hashes SHA-256: es el log de 12 casos
(12 ok, 0 fallos). Los fixtures D3b los verifican los propios casos 11 y 12 al correr D4.

## Lo que NO se corrió (no se da por probado)

- `npm run soak` y `python3 scripts/validate-docker.py` (con y sin `--soak`).
- `bash experiments/vocoder/d4/validate.sh` (12 casos, latencias, CLI de los tres proveedores).
- El banco original del vocoder (`experiments/vocoder`, `bench.py`).

Este documento se completa con tiempos y problemas de arranque cuando esas corridas se hagan.
