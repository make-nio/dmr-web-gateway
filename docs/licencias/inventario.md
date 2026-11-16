# Inventario de licencias y terceros (borrador, 16-nov-2026)

Base: PR #10, commit `3a7deaf54f4d0ebddb45bae444e3cf9867515379`. **Esto no es asesoramiento
legal ni decide sobre patentes**: deja los datos para que el titular del repositorio decida
qué se publica y con qué licencia. Nada de lo que sigue permite presentar el proyecto como
«libre de restricciones».

El SBOM (CycloneDX 1.5) se regenera con un comando y sale idéntico cada vez:

```bash
python3 scripts/generate-sbom.py          # escribe docs/licencias/sbom.cdx.json
python3 scripts/generate-sbom.py --check  # falla si el archivo escrito difiere
```

La tabla de terceros que no están en los lockfiles vive en `terceros.json` (fuente única del
SBOM). El script avisa si una dependencia de `package-lock.json` o `Cargo.lock` no figura.

## 1. Código propio

| Qué | Licencia | Estado |
|---|---|---|
| Todo el código y los documentos propios (`src/`, `test/`, `scripts/`, `experiments/vocoder/**` salvo terceros, `docs/`) | **ninguna elegida** | No existen `LICENSE`, `NOTICE` ni `THIRD_PARTY_NOTICES` en la rama base (verificado en la base del PR #10), y los archivos no llevan encabezado SPDX. Sin licencia explícita, el código queda con todos los derechos reservados aunque el repositorio sea público. |

## 2. Dependencias de lockfile (cobertura 100 %)

| Paquete | Versión | Licencia | Alcance |
|---|---|---|---|
| typescript | 5.9.3 | Apache-2.0 | desarrollo (no se distribuye) |
| @types/node | 22.20.5 | MIT | desarrollo |
| undici-types | 6.21.0 | MIT | desarrollo |
| blip25-vocoder (Cargo, dependencia de ruta) | 1.0.0 | MIT (declarada) | build del banco; ver §3 |
| vocoder-spike-worker (Cargo, propio) | 0.1.0 | sin determinar (código propio) | build del banco |

`Cargo.lock` no trae ningún crate del registro: BLIP25 se compila sin dependencias (su
característica opcional `serde` está apagada). Los tres paquetes de npm son sólo de
desarrollo; el servicio compilado no los incluye.

## 3. Terceros que se descargan en el build o se referencian

| Tercero | Referencia fijada | Licencia declarada | Verificado contra | Estado |
|---|---|---|---|---|
| OpenDMR | `d28164b` | GPL-2.0 (raíz), GPL-3.0-or-later (encoder), GPL-2.0-or-later (decoder) | LICENSE, CREDITS, encabezados | **Conflicto interno** (ver §4) |
| mbelib-neo (decoder de OpenDMR) | dentro de OpenDMR | GPL-2.0-or-later («partes originalmente ISC») | SPDX de `decoder/mbelib.c` | verificada |
| Encoder OP25 / IMBE (Yazev) | dentro de OpenDMR | GPL-3.0-or-later en `encode.cc`; el CREDITS dice GPL-2.0 | `encoder/encode.cc`, `encoder/CREDITS` | **Contradicción** |
| PFFFT / FFTPACK | dentro de OpenDMR | licencia tipo BSD de UCAR/NCAR | encabezados de `pffft.h` y `fftpack.h` | verificada |
| BLIP25 | `d176281` | MIT (© 2026 Chance Lindsey) | `Cargo.toml`, `LICENSE`, `PATENT_NOTICE.md`, `ATTRIBUTION.md` | MIT verificada; **procedencia y patentes abiertas** |
| dmrgo | `f78e033` | MIT (© 2023-2026 Jacob McSwain) | `LICENSE` | verificada; sólo referencia de lectura |
| Constante de silencio de MMDVMHost | referida en docs | no leída | — | **sin determinar** |
| OSR (Telchemy), `OSR_us_000_*_8k` | SHA-256 del 0010 en `terceros.json` | condiciones propias: uso y modificación libres, citar «Open Speech Repository» | página del OSR | verificada |
| «Rosario (Argentina)» (G. Quagliano, 2011) | SHA-1 del OGG | CC BY-SA 3.0 | página de Wikimedia Commons | verificada |
| FFmpeg 6.1.1-3ubuntu5 | — | LGPL-2.1+ o GPL-2.0+ según el build | no inspeccionado | **sin determinar** |
| Imagen `node:22-alpine` | digest `0e17…2af8202` | agregada | no inventariada | **sin determinar** |
| Imagen `rust:1.85-bookworm` (+ python3 de Debian) | digest `e51d…c0bc4` | agregada | no inventariada | **sin determinar** |

El repo **no copia** fuentes ni binarios de OpenDMR ni de BLIP25 (el `README` del banco lo
dice y el árbol lo confirma): se descargan al construir la imagen del banco. Lo que sí está
en el repo y tiene licencia de terceros son los WAV, ZIP y trazas de `evidence/`.

## 4. Incompatibilidades y riesgos (para decidir)

1. **OpenDMR no es coherente consigo mismo.** La raíz y los `CREDITS` dicen GPL-2.0, pero el
   encoder (`encode.cc`) está bajo GPL-3.0-or-later. GPL-2.0 *solo* y GPL-3.0 no se pueden
   combinar en un binario distribuible; sólo cierra si todo el conjunto es «o posterior»
   (entonces el resultado efectivo es GPL-3.0-or-later). `opendmr.cpp` y `dmr_codec.cpp` no
   traen encabezado, así que no se sabe si son «solo» u «o posterior». **Sin determinar.**
2. **El código propio se compila junto con OpenDMR.** `experiments/vocoder/d4/native.cpp`
   hace `#include "opendmr.cpp"` y `opendmr-worker.cpp` se enlaza con `libopendmr.a`. Un
   worker o una imagen así construidos es una obra combinada: distribuirlo obliga a que el
   conjunto, incluido nuestro código, sea GPL compatible. **Publicar el código fuente propio
   bajo una licencia permisiva (MIT/Apache) es una cosa; distribuir workers o imágenes
   compilados con OpenDMR es otra**, y esa segunda no se puede hacer bajo la licencia
   permisiva. El README de D4 ya dice que no se publican workers; este documento lo respalda.
3. **BLIP25 es MIT sólo de palabra.** Su propio aviso dice que el motor se recuperó por
   ingeniería inversa de un vocoder de referencia compilado, que es «derivado» de él y que
   está «patent-encumbered». Una licencia MIT del código no concede derechos de patente ni
   resuelve esa procedencia. **No lo decide esta historia.**
4. **Patentes de AMBE+2 (ambos motores).** Fuera de alcance: lo decide el titular. El aviso de
   BLIP25 cita US8359197 como activa hasta 2028-05-20; **no lo verifiqué**. Aplica a OpenDMR y
   a BLIP25 por igual.
5. **Corpus en español (CC BY-SA 3.0, share-alike).** `Rosario-01.wav` y `Rosario-02.wav` son
   adaptaciones: deben seguir bajo CC BY-SA 3.0, con crédito, enlace y aviso de cambios
   (ya están en `evidence/d3c/LEEME.md`). No se pueden relicenciar con la licencia del código;
   conviene dejarlos señalados aparte, con su propio aviso. El texto leído es de colaboradores
   de Wikipedia: su licencia no se verificó.
6. **Corpus en inglés (OSR).** Se puede modificar y publicar «sin restricción», con una única
   obligación: citar «Open Speech Repository». Hoy la cita está en README y manifiestos, no en
   un aviso de licencia: ver el borrador de `THIRD_PARTY_NOTICES`.
7. **El resto de los WAV de `evidence/` (C4–C7, D3b, L1/L2)** son derivados del OSR 0010 y de
   otros archivos OSR; no se revisó el origen de cada clip más allá de lo que dicen sus
   scripts (`c7/run.py` toma `OSR_us_000_{id}_8k`).
8. **Vector de silencio de MMDVMHost.** Es una constante corta; MMDVMHost declara GPL-2.0 (no
   leída). Si se la considera copiable, arrastra una atribución. Sin determinar.

## 5. Qué hay que decidir (resumen)

| Decisión | Opciones y consecuencia |
|---|---|
| Licencia del código propio | MIT o Apache-2.0 (permisivas; compatibles con BLIP25 MIT y con las dependencias de desarrollo). GPL-3.0-or-later (única que cierra con todo OpenDMR si se va a distribuir un binario combinado). |
| Publicar workers e imágenes | Con OpenDMR: sólo bajo GPL y sujeto a los puntos 1 y 2. Con BLIP25: sujeto a patentes y procedencia. Hoy no se recomienda. |
| Publicar los WAV de evidencia | Posible con aviso OSR (inglés) y CC BY-SA 3.0 (español); falta revisar el origen de cada clip y los ZIP. |
| Patentes AMBE+2 | Evaluación legal por jurisdicción, fuera de esta historia. |

## Lo que no se pudo revisar

- Inventario por paquete de las imágenes base (Debian, Alpine) y del paquete FFmpeg de Ubuntu.
- Licencia del texto de Wikipedia leído en la grabación y de la constante de MMDVMHost.
- Cada archivo de OpenDMR por separado (se leyeron la raíz, los `CREDITS` y los encabezados de
  seis archivos: `mbelib.c`, `encode.cc`, `pffft.h`, `fftpack.h`, `opendmr.cpp`, `dmr_codec.cpp`).
- Las patentes, que quedan fuera de esta tarea.
