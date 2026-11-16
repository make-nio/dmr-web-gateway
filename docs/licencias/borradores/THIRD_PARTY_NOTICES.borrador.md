# Avisos de terceros (BORRADOR)

Borrador a revisar antes de publicar. Cada entrada se verificó el 16-nov-2026 contra la
fuente enlazada; ver `docs/licencias/inventario.md` para el estado y los conflictos.

## Audio

### Open Speech Repository (Telchemy)
Archivos `OSR_us_000_*_8k.wav` y sus derivados en `experiments/vocoder/evidence/`
(C4–C7, D3b, L1/L2).
Fuente: https://www.voiptroubleshooter.com/open_speech/
Condiciones: uso, copia, modificación y publicación libres; se exige identificar la fuente
como **«Open Speech Repository»**. Los derivados de este repositorio pasaron por los
codecs AMBE+2 y se recortaron a 8 kHz mono.

### «Rosario (Argentina) Parte 1» — Gabriel Quagliano (2011)
Origen de `experiments/vocoder/evidence/d3c/Rosario-01.wav` y `Rosario-02.wav`.
Fuente y créditos: https://commons.wikimedia.org/wiki/File:Es-Rosario_(Argentina)_Parte_1-article.ogg
Texto: colaboradores de Wikipedia en español, https://es.wikipedia.org/wiki/Rosario_(Argentina)
Licencia: Creative Commons Atribución-CompartirIgual 3.0 Unported,
https://creativecommons.org/licenses/by-sa/3.0/
Cambios: fragmento [00:15, 00:35), conversión a PCM mono s16le a 8 kHz y paso por dos pares
encoder/decoder. Estas adaptaciones se distribuyen bajo la misma licencia (CC BY-SA 3.0) y
**no** están cubiertas por la licencia del código.

## Motores de vocoder (no incluidos; se descargan al construir el banco)

### OpenDMR — commit d28164b39ba4d91ad5948ff22707937f8944f70f
https://github.com/MW0MWZ/OpenDMR — GPL-2.0 (raíz); GPL-3.0-or-later (`encoder/encode.cc`);
GPL-2.0-or-later (`decoder/mbelib.c`). Incluye trabajo de mbelib (Pavel Yazev, 2010),
mbelib-neo (arancormonk, 2023-2025), el encoder MBE de OP25 (Max H. Parke KA1RBI, 2013-2019),
el IMBE de Pavel Yazev (2009) y PFFFT/FFTPACK (Julien Pommier 2013; NCAR/UCAR 2004).
Aviso FFTPACK: se conservan los avisos de copyright, la lista de condiciones y el descargo
del texto original; no se usan los nombres de NCAR ni de UCAR para promocionar.
**Conflicto abierto:** las licencias GPL-2.0 y GPL-3.0-or-later del conjunto no están
reconciliadas por el proyecto original. No distribuir ejecutables sin resolverlo.

### BLIP25 vocoder — commit d1762813b7142c021f4105c832bf7f060d1249fa
https://github.com/OpenBLIP25/blip25-vocoder — MIT, Copyright (c) 2026 Chance Lindsey.
Su propio `PATENT_NOTICE.md` y `ATTRIBUTION.md` indican que el motor de síntesis y análisis
se recuperó por ingeniería inversa de un vocoder de referencia compilado, que está sujeto a
patentes y que se ofrece sólo para investigación e interoperabilidad.

## Referencias de prueba (no incluidas)

### dmrgo — commit f78e033e90559995213498973fe9d75e9bd45b93
https://github.com/USA-RedDragon/dmrgo — MIT, Copyright 2023-2026 Jacob McSwain.
Usado como referencia de lectura por `experiments/vocoder/d2a/main.go`.

### MMDVMHost (g4klx)
Origen declarado de la constante de silencio AMBE usada como vector de prueba
(https://github.com/g4klx/MMDVM-Host). **Licencia sin determinar**; pendiente de revisión.

## Dependencias de desarrollo (npm)
- typescript 5.9.3 — Apache-2.0
- @types/node 22.20.5 — MIT
- undici-types 6.21.0 — MIT
Sólo se usan para compilar y probar; no se distribuyen.
