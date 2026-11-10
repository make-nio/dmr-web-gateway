# Sprint 1 / Fase C — checkpoint parcial

Estado: investigación offline autorizada; **Fase C incompleta**. Checkpoint
solicitado por el usuario para preservar avances antes del límite de saldo.
Continuar en `spike/sprint-1-ambe-vocoder`, PR #10 OPEN/DRAFT.

## Alcance y evidencia

Los resultados medidos y la escucha previa están en
[Fase B](sprint-1-vocoder-results.md). No son pruebas nuevas de Fase C.
El checkpoint inicial contenía inspección de fuentes y preparación de referencias.
**Actualización 2026-11-10: C1 (encode CLI/wrapper) ejecutada**, con resultados
abajo. El corpus ampliado y el diagnóstico instrumental de saturación siguen
sin ejecutarse. No hay corrección implementada. Fase C completa sigue pendiente.

Revisiones inspeccionadas:

- OpenDMR: `d28164b39ba4d91ad5948ff22707937f8944f70f`.
- BLIP25: `d1762813b7142c021f4105c832bf7f060d1249fa`.
- Referencia candidata dmrgo: `f78e033e90559995213498973fe9d75e9bd45b93`.

## A. Encode OpenDMR: inconsistencia interna en fuente

En [opendmr.cpp](https://github.com/MW0MWZ/OpenDMR/blob/d28164b39ba4d91ad5948ff22707937f8944f70f/opendmr.cpp),
`encode_ambe_frame` concatena nueve parámetros con anchos
`[7,5,5,9,7,5,4,4,3]`, MSB primero, antes de FEC. `decode_ambe_frame`
recupera 49 bits en ese orden de bloques protegidos/no protegidos.

Sin embargo, [ambe3600x2450.c](https://github.com/MW0MWZ/OpenDMR/blob/d28164b39ba4d91ad5948ff22707937f8944f70f/decoder/ambe3600x2450.c)
interpreta b0 desde posiciones `[0,1,2,3,37,38,39]`, y b1 desde
`[4,5,6,7,35]`; no consume parámetros simplemente concatenados.
Es una inconsistencia interna y una hipótesis fuerte para el fallo audible,
**no una causa raíz demostrada con trazas ni prueba del orden normativo DMR**.

El CLI `dmr_codec encode` llama a la misma API `opendmr_encode` que el wrapper,
con bloques de 160 muestras int16. Linux x86-64 little-endian ofrece una ruta
directamente comparable. Makefile upstream: C++ `-O3 -std=c++11 -Wall -fPIC`;
wrapper: `-O2 -std=c++17`, enlazando la misma biblioteca. La versión del
compilador y los hashes de C1 se registran abajo.

Secuencia experimental original (solo pasos 1/2 ejecutados en C1):

1. Extraer el mismo PCM mono 8 kHz/int16 LE y registrar SHA-256.
2. Ejecutar CLI y wrapper en procesos nuevos; comparar todas las tramas byte/bit,
   primera divergencia y diferencias posteriores, separando información/FEC/padding.
3. Decodificar ambas secuencias con ambos candidatos desde estado inicial nuevo.
4. Construir harness mínimo que observe b[9], bits49 y trama72 con las funciones
   originales. Localizar dónde se pierde el significado de los parámetros.
   No generar audio con un packing corregido ni reescribir upstream.

## C1 — Comparación encode ejecutada, 2026-11-10

**Resultado: coincidencia exacta en esta muestra y compilación.** Dos ejecuciones
del CLI original y dos del wrapper, cada una en un proceso nuevo, produjeron
idénticas 1000 tramas: 9000 bytes / 72000 bits por salida. Cero bytes, bits o
tramas diferentes tanto entre caminos como entre repeticiones; primera
divergencia: ninguna (`null` en evidencia). Los cuatro procesos terminaron con
exit 0 y stderr vacío. CLI: `Encoded 1000 frames (20.00 seconds)`.

Entrada: primeros 20 segundos del WAV existente OSR_us_000_0010_8k.wav, extraídos
con `wave.readframes(160000)`, sin resampling, escalado ni normalización.
PCM mono 8000 Hz s16le: 160000 muestras, 320000 bytes, extremos -7651 / 10751.
SHA-256 PCM:
`677d09d1c91e7cae74c0a5dc3e5e3bcd3ded3634ed471bcbca6dd65ea82e2279`.
SHA-256 común de las cuatro secuencias AMBE:
`60cbd71393bf36ed274e48908007289c3a529d8399574569e7763717c2ff2717`.
Hash del WAV completo conservado en sección C y evidencia.

### Equivalencia de caminos y estado

CLI: `dmr_codec encode input.s16le output.ambe`, lectura nativa de 160 int16
por llamada a `opendmr_encode`. Wrapper existente: mismo PCM, 1000 líneas `E`
con 320 bytes hex cada una, llamadas a la misma API y conversión explícita LE.
Host Linux x86-64 little-endian verificado. Se compara solo el hex de la trama,
excluyendo el tiempo que añade el protocolo del worker. EOF al terminar.
Sin comandos `R`/`D`, sin warmup ni actividad previa en los procesos. Se mantiene
estado entre las 1000 tramas de cada ejecución. El wrapper crea además su objeto
decoder al iniciar, pero no lo usa; esa diferencia de inicialización no cambió
la salida en esta prueba. No se investigó decode.

Ambos usan `libopendmr.a` del build fijado de OpenDMR; CLI con `-O3 -std=c++11
-Wall -fPIC`, wrapper con `-O2 -std=c++17`. GCC/G++ instalado: Debian
12.2.0-14, versión 12.2.0. Flags proceden de Makefile/Dockerfile; no se recompiló
hoy. Hash de biblioteca:
`ae3b85afe75f77e222eec9114a874dd00f70ee2416dd6ad74bf357f908399590`.
Se registraron hashes de binarios, fuentes, dependencias dinámicas y revisión
upstream; `git diff HEAD` de fuentes upstream vacío. La fuente del wrapper en
la imagen coincide por SHA-256 con la del repositorio:
`68100b4d2476ec03dcc265dba0cf42354194bb673133bd09f2ec56fee954edd0`.

Los nueve bytes canónicos completos se comparan mediante XOR/popcount y offsets
MSB-first. La igualdad cubre todos los bits emitidos, incluidos los de protección;
no valida su significado, FEC ni padding/packing normativo. No hubo una
divergencia que requiriera clasificar bits por campo.

### Ejecución y evidencia reproducible

Se reutilizó imagen local (sin build/pull):
`sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab`.
Docker en WSL2 Ubuntu-24.04; runtime sin red, read-only, uid/gid1000, 1 CPU,
512 MiB, sin capacidades/puertos, no-new-privileges. Exit 0, sin OOM.
Solo volumen de resultados escribible; script montado read-only.

Comando ejecutado desde PowerShell, raíz del repo (las variables siguientes
abrevían las rutas absolutas usadas como argumentos de los dos mounts):

```powershell
$repoWsl = '/mnt/c/Users/maria/Documents/Codex/2026-11-09/referenced-chatgpt-conversation-this-is-an-4/work/dmr-web-gateway'
$imageC1 = 'sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab'
New-Item -ItemType Directory -Force experiments/vocoder/results/c1 | Out-Null
wsl -d Ubuntu-24.04 -- docker run --name dmr-vocoder-c1 --network none --read-only --user 1000:1000 --cap-drop ALL --security-opt no-new-privileges --cpus 1 --memory 512m --mount "type=bind,src=$repoWsl/experiments/vocoder/compare_encode.py,dst=/lab/compare_encode.py,readonly" --mount "type=bind,src=$repoWsl/experiments/vocoder/results/c1,dst=/results" $imageC1 python3 /lab/compare_encode.py
wsl -d Ubuntu-24.04 -- docker inspect dmr-vocoder-c1
wsl -d Ubuntu-24.04 -- docker rm dmr-vocoder-c1
```

El contenedor terminó y fue retirado después de guardar inspección selectiva.
El script [compare_encode.py](../../experiments/vocoder/compare_encode.py)
incluye las invocaciones exactas de los cuatro procesos y las comprobaciones de
entrada, longitud y comparación. No necesita dependencias Python externas.

Evidencia publicada en [evidence/c1](../../experiments/vocoder/evidence/c1):

- `results.json`: hashes, entorno, comandos, cuatro resultados y comparaciones.
- `frames.jsonl`: hash PCM por trama y los cuatro hex de salida, índice desde 0.
- `container.json`: estado final y aislamiento aplicado.
- `local-artifacts.json`: hashes/tamaños de archivos crudos locales, incluidos
  PCM, AMBE, stdout/stderr y JSON original.

Los archivos crudos permanecen en `experiments/vocoder/results/c1/` (ignorado).
El `results.json` publicado omite únicamente el texto del Makefile upstream
presente en el JSON local; por eso sus hashes difieren. No se publican binarios
ni fuentes upstream. El corpus conserva atribución a Open Speech Repository.

### Conclusión y límites de C1

El wrapper **no introduce una diferencia de encode en esta muestra, imagen y
estado inicial**. El CLI original reproduce la misma secuencia de bits usada
por el wrapper. No demuestra calidad audible, corrección del encoder, causa raíz
del ruido, igualdad para cualquier entrada/arquitectura ni interoperabilidad DMR.
No se ejecutaron decode, pruebas de ganancia, corpus BLIP25, dmrgo o soaks.
No se modificaron upstream, protocolo o gateway.

Próxima microtarea recomendada, sujeta a autorización: trazar b[9] → bits49 →
trama72 con funciones originales para comprobar la hipótesis de orden de
parámetros, sin corregir packing ni algoritmo. C1 no autoriza iniciarla.

## C2 — Traza de parámetros (tramas 0–3 de C1)

**Se confirma una incompatibilidad interna de orden.** En la trama 0, los siete
bits que empaquetó el encoder para b0 representan 90. Se recuperan intactos.
Al leer las posiciones que especifica el decoder para b0, el valor es 91.
Aparece además una discrepancia durante el recorrido de protección y
recuperación del bloque B, antes de interpretar los parámetros.

**Muestra.** Se eligió el prefijo consecutivo de cuatro tramas para conservar
el estado inicial de C1 sin procesar sus 1000 tramas. Son 80 ms, 1280 bytes
PCM s16le, SHA-256 `d22334ef46cb58959b7c90e4d75ae4488bcd4ef768f5470563b13c0b2d3ddc43`.
Se comprobó por trama el hash del PCM y la igualdad de los nueve bytes
generados con la evidencia CLI guardada en C1.

**Empaquetado.** La sonda observa b[9] a la salida de `encode_dmr_params` y
llama a `encode_ambe_frame` y `decode_ambe_frame` originales. Para acceder a
estas funciones estáticas compila la unidad original dentro de la sonda.
En la traza, `packed49FromWidths` se calcula desde los b[9] observados según
los anchos y el bucle MSB primero de la fuente. `frameHex` y `recovered49`
son salidas directas de las dos funciones originales.

**Protección.** En la trama de 72 bits, A ocupa 0–23 (12 bits de información
con Golay), B ocupa 24–46 (12 con Golay y máscara derivada de A) y C ocupa
47–71 (25 sin protección). Tras recuperar los 49 bits, las cuatro tramas
preservan las posiciones 0–11 y 24–48. Todas presentan cambios exclusivamente
en 12–23, correspondientes a B. En la trama 0 difieren los índices
13, 15, 18, 19, 20, 21 y 22. El ensayo localiza la diferencia en el recorrido
de B sobre tramas limpias. Queda sin aislar la operación concreta que la causa.

**Interpretación.** Posiciones de información numeradas desde cero, de mayor a
menor peso dentro de cada parámetro. La columna del decoder proviene de las
asignaciones de `ambe_d` en `decoder/ambe3600x2450.c`, ordenadas según el
desplazamiento de destino. Se verificó la cobertura única de las 49 posiciones.

| Parámetro | Posiciones al empaquetar | Posiciones que lee el decoder | Original, trama 0 | Recuperado con posiciones del encoder | Interpretado con índices del decoder |
|---|---|---|---:|---:|---:|
| b0 | 0–6 | 0,1,2,3,37,38,39 | 90 | 90 | 91 |
| b1 | 7–11 | 4,5,6,7,35 | 0 | 0 | 8 |
| b2 | 12–16 | 8,9,10,11,36 | 6 | 12 | 0 |
| b3 | 17–25 | 12,13,14,15,16,17,18,19,40 | 87 | 175 | 197 |
| b4 | 26–32 | 20,21,22,23,41,42,43 | 78 | 78 | 91 |
| b5 | 33–37 | 24,25,26,27,44 | 8 | 8 | 28 |
| b6 | 38–41 | 28,29,30,45 | 14 | 14 | 7 |
| b7 | 42–45 | 31,32,33,46 | 13 | 13 | 8 |
| b8 | 46–48 | 34,47,48 | 1 | 1 | 5 |

| Trama de C1 | Salida original de 72 bits (hex) | Bits cambiados al recuperar 49 | Parámetros distintos al interpretar |
|---:|---|---:|---:|
| 0 | b4093082e209ce4769 | 7 | 9 |
| 1 | 94065878bc614e176f | 7 | 9 |
| 2 | 0d0d2426bc5b1b0019 | 5 | 8 |
| 3 | 0305aabd52be520001 | 8 | 8 |

En b0, tanto las posiciones emitidas como las leídas quedan fuera del bloque B.
Eso permite atribuir la diferencia 90 → 91 al orden de lectura incluso en
presencia de la discrepancia de B. La evidencia alcanza para confirmar el
desacuerdo entre ambos caminos de esta revisión. Su impacto audible y el orden
normativo DMR quedan fuera del experimento. Investigación detenida en este
punto para revisión arquitectónica.

### Reproducción offline

Desde la raíz del repositorio en WSL2, con la imagen de C1 disponible
localmente. Es la invocación realizada vía `wsl -d Ubuntu-24.04`, expresada
con rutas relativas al checkout para repetirla en otro equipo.

```sh
docker run --rm --pull never --network none --read-only --user 1000:1000 \
  --cap-drop ALL --security-opt no-new-privileges --cpus 1 --memory 512m \
  --tmpfs /tmp:rw,exec,size=32m \
  --mount "type=bind,src=$PWD/experiments/vocoder/c2,dst=/c2,readonly" \
  --mount "type=bind,src=$PWD/experiments/vocoder/evidence/c1,dst=/c1,readonly" \
  sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab \
  python3 /c2/trace.py
```

Linux x86-64 WSL2, G++ 12.2.0, OpenDMR `d28164b39ba4d91ad5948ff22707937f8944f70f`.
El [JSON de la corrida](../../experiments/vocoder/evidence/c2/trace.json)
registra la orden de compilación, hashes de fuentes y biblioteca, estado por
trama, bloques A/B/C en binario, posiciones de cada bit distinto y las dos
lecturas de los parámetros. La [sonda y el analizador](../../experiments/vocoder/c2)
solo producen trazas numéricas.

## C3 — Alineación Golay del bloque B

**La primera diferencia aparece al usar el retorno de `CGolay24128::encode23127(B)`
como palabra alineada a los 23 bits bajos.** La función devuelve directamente
`ENCODING_TABLE_23127[B]`. En las 4096 entradas posibles ese entero equivale
a la palabra que acepta el decoder desplazada un bit hacia la izquierda.
Los bits útiles ocupan 23…1. En `encode_ambe_frame`, el llamador aplica XOR
con una máscara alineada a 22…0 y el bucle de escritura lee exactamente
`(b_codeword >> (22 - i)) & 1` para i = 0…22. Esa selección transmite el
bit 0 de relleno y omite el bit 23. El primer límite incompatible es el
uso del valor de tabla en el llamador, antes de la máscara. El bucle
materializa la selección en la trama. El propio decoder entrega los valores
alterados al recuperar las tramas limpias.

**Aislamiento de la sonda.** Se tomaron los bits 12–23 del vector pre-FEC
de C2 y los nueve bytes ya registrados para cada trama. Para las cuatro,
el B en la trama coincide exactamente con los 23 bits bajos del XOR
calculado. El A original y el recuperado por Golay dan máscaras idénticas.
Al quitar la máscara se recuperan exactamente los 23 bits bajos de la tabla
en el mismo orden. La lectura MSB primero coincide con el bloque B publicado
en C2. Tanto la llamada directa a `decode23127` como `decode_ambe_frame`
original sobre los nueve bytes reproducen el resultado de C2. Esto sitúa la
discrepancia en la representación que intercambian las funciones upstream.
XOR, inversión del orden de transmisión y extracción por la sonda quedan
descartados como explicación en estas tramas.

| Trama | B antes de Golay | B recuperado por upstream | B recuperado en control de alineación |
|---:|---|---|---|
| 0 | 001100010101 | 011000101011 | 001100010101 |
| 1 | 001000010110 | 010000101101 | 001000010110 |
| 2 | 111101101000 | 111011010000 | 111101101000 |
| 3 | 010010000101 | 100100001010 | 010010000101 |

Por ejemplo, para la trama 2 el retorno de tabla es
`111101101000010000000000`. El valor descramblado que entra al decoder es
`11101101000010000000000`. Se ve la pérdida del 1 superior y la permanencia
del 0 inferior. La evidencia registra para cada trama las palabras binarias
de A/B, Golay, ambas máscaras, XOR, campo transmitido, campo recuperado y
salida final.

**Reversibilidad.** Se ensayaron todos los B de 0 a 4095 con las funciones
originales. Como control de representación se usó la convención del propio
`decode24128`, que llama a `decode23127(code >> 1)`. Denominando
`control23 = encode24128(B) >> 1`, se observaron estos conteos:

| Comprobación sobre 4096 valores de B | Resultado |
|---|---:|
| Retorno de encode23127 igual a control23 desplazado a la izquierda un bit | 4096 |
| Retorno de encode23127 con el bit 23 en 1 | 2048 |
| Palabras distintas al retener los 23 bits bajos del retorno | 4096 |
| decode23127 sobre esos 23 bits bajos devuelve B | 2 |
| decode23127 sobre control23 devuelve B | 4096 |

El mapeo limpio a los 23 bits bajos sigue siendo **inyectivo** en el dominio
de 12 bits. Sin embargo, el decoder actual solo preserva B para 2/4096
entradas. La alineación usada en el control basta para la ida y vuelta
numérica de las 4096 entradas. El control solo calcula enteros en la sonda.
La conformidad externa del código Golay, la corrección ante errores de canal
y el efecto audible quedan fuera de C3.

### Reproducir C3

Se reutilizó la imagen local de C1 en WSL2 x86-64, G++ 12.2.0 y OpenDMR
`d28164b39ba4d91ad5948ff22707937f8944f70f`. Comando equivalente desde la
raíz del checkout en WSL:

```sh
docker run --rm --pull never --network none --read-only --user 1000:1000 \
  --cap-drop ALL --security-opt no-new-privileges --cpus 1 --memory 512m \
  --tmpfs /tmp:rw,exec,size=32m \
  --mount "type=bind,src=$PWD/experiments/vocoder/c3,dst=/c3,readonly" \
  --mount "type=bind,src=$PWD/experiments/vocoder/evidence/c2,dst=/c2,readonly" \
  sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab \
  python3 /c3/trace.py
```

[Traza binaria, hashes SHA-256 y orden de compilación](../../experiments/vocoder/evidence/c3/trace.json)
y [sonda reproducible](../../experiments/vocoder/c3). El identificador
`canonical23` del JSON designa el control interno descrito arriba. Fuentes
de la revisión fijada: [tabla y funciones Golay](https://github.com/MW0MWZ/OpenDMR/blob/d28164b39ba4d91ad5948ff22707937f8944f70f/encoder/cgolay24128.cpp#L1072)
y [selección de bits de B](https://github.com/MW0MWZ/OpenDMR/blob/d28164b39ba4d91ad5948ff22707937f8944f70f/opendmr.cpp#L313).
Investigación detenida en el diagnóstico para revisión arquitectónica.

## C4 — Efecto aislado de la alineación de B sobre una muestra

La variante recuperó los 4096 valores B en tramas limpias. El control recuperó
2. Para cada B se usó un A y un C deterministas y variables. Se comprobó
igualdad de los bloques transmitidos A y C y de su información recuperada
respecto de la entrada en los 4096 casos, antes de procesar voz.

La sonda genera una única secuencia de parámetros desde el PCM. Para cada
trama bifurca los mismos nueve valores: el control llama al empaquetador
original y la variante copia esa trama y reemplaza exclusivamente sus posiciones
24–46 con los 23 bits de `(encode23127(B) >> 1) ^ máscara(A)`. Así ambos
caminos comparten exactamente el estado del encoder y el orden original de
los parámetros. Cada secuencia completa se decodificó en un proceso recién
iniciado del mismo CLI original, con estado continuo durante las 1000 tramas.
Se volcaron los PCM directamente a WAV mono s16le, 8000 Hz.

**Voz.** Se usaron los mismos 20 s de Open Speech Repository que en C1. El
hash del control coincide con la secuencia CLI publicada en C1. B se recuperó
en 0/1000 tramas del control y en 1000/1000 de la variante. Cambiaron 11478
bits transmitidos (todos en B) y 5992 bits de información (todos en 12–23).
A y C se preservaron en las 1000 tramas. Interpretando ambos vectores con los
índices del decoder documentados en C2, cambió b3 en 1000 tramas y b4 en 932.
Los otros siete parámetros interpretados coincidieron en todas. El XOR de
72 bits, las posiciones de información diferentes y los dos vectores de
parámetros interpretados se registran por trama.

| Medida (unidades PCM s16) | Entrada | Control | Variante |
|---|---:|---:|---:|
| RMS | 1570,76 | 5638,55 | 4823,29 |
| Pico absoluto | 10751 | 31128 | 31128 |
| Muestras en ±31128 (160000 en total) | 0 | 1740 | 843 |
| Muestras en extremos int16 | 0 | 0 | 0 |
| Saltos absolutos >12000 entre tramas (999 pares) | 0 | 78 | 54 |
| Saltos absolutos >12000 dentro de tramas (159000 pares) | 0 | 14097 | 9194 |
| Salto máximo entre tramas | 3455 | 62256 | 62256 |

Las muestras en ±31128 miden contactos con el límite interno del decoder.
El umbral de salto caracteriza diferencias entre muestras consecutivas. La
variante redujo RMS, contactos con el límite y frecuencia de saltos grandes
en esta muestra. La evaluación de inteligibilidad queda pendiente de escucha
humana posterior a la revisión. Continúa vigente la discrepancia de orden de C2.

### Artefactos y reproducción

[Manifiesto con hashes, correspondencia de nombres, entorno y métricas](../../experiments/vocoder/evidence/c4/manifest.json)
· [Evidencia por trama](../../experiments/vocoder/evidence/c4/frames.jsonl)
· [Muestra 01](../../experiments/vocoder/evidence/c4/Muestra-01.wav)
· [Muestra 02](../../experiments/vocoder/evidence/c4/Muestra-02.wav).
Fuente de voz: **Open Speech Repository**, OSR_us_000_0010_8k.wav.
El manifiesto registra los hashes SHA-256 del WAV fuente, PCM de entrada,
ambas secuencias codificadas, ambos PCM decodificados y ambos WAV. Se conservó
el nivel del decoder, sin posprocesar las muestras.

Desde la raíz del checkout en WSL2, con la imagen local de C1 disponible:

```sh
mkdir -p experiments/vocoder/results/c4
docker run --rm --pull never --network none --read-only --user 1000:1000 \
  --cap-drop ALL --security-opt no-new-privileges --cpus 1 --memory 512m \
  --tmpfs /tmp:rw,exec,size=32m \
  --mount "type=bind,src=$PWD/experiments/vocoder/c4,dst=/c4,readonly" \
  --mount "type=bind,src=$PWD/experiments/vocoder/evidence/c2,dst=/c2,readonly" \
  --mount "type=bind,src=$PWD/experiments/vocoder/results/c4,dst=/results" \
  sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab \
  python3 /c4/run.py
```

En la corrida publicada se montó `evidence/c4` como destino de resultados.
La variante y la instrumentación residen en el [banco C4](../../experiments/vocoder/c4).
OpenDMR `d28164b39ba4d91ad5948ff22707937f8944f70f`, G++ 12.2.0.

## B. Decode OpenDMR: ganancia y recorte

En [mbelib.c](https://github.com/MW0MWZ/OpenDMR/blob/d28164b39ba4d91ad5948ff22707937f8944f70f/decoder/mbelib.c),
`mbe_floattoshort` multiplica por 8 y limita a `32767 * 0.95`; al convertir a
int16 da aproximadamente ±31128. El detector de Fase B
(`abs(sample) >= 32767`) **no detecta ese recorte interno**.

Pendiente: comprobar conversión con floats conocidos; medir muestras en ±31128,
mesetas, picos, RMS, DC y saltos entre tramas frente a saltos intratrama;
comparar salida CLI/wrapper con procesos nuevos. Un salto aislado no demuestra
un artefacto audible. Ganancia y límite están en la fuente, pero no está probado
que expliquen todos los plops/ruido. No aplicar normalización, filtros o cambios
de ganancia como solución definitiva.

## C. Corpus adicional BLIP25

Fuentes: **Open Speech Repository**, Harvard sentences.
[Procedencia y condiciones](https://www.voiptroubleshooter.com/open_speech/american.html):
uso/copia/modificación para pruebas VoIP e investigación con atribución.
Conservar esa atribución en el paquete de escucha.

WAV completos descargados localmente, SHA-256:

| Archivo | SHA-256 |
| --- | --- |
| OSR_us_000_0010_8k.wav | `a4bf9becd046d7aedb6d05b6e12347a6294a44f74d263089c636fb0a2b1e6561` |
| OSR_us_000_0030_8k.wav | `d3e1cfba98a44ddfc6e99508e663794c8dc41bdb2baced224f779c453143b622` |

Pendiente: ambas voces, frases cortas/largas, niveles 0.25×/1×/2×, silencios y
transiciones abruptas. Registrar recorte introducido en el estímulo. Comparar
secuencias idénticas con/sin reset en límites explícitos. Conservar originales
y procesados sin normalización de salida; nombres neutrales A/B y manifiesto
separado con correspondencias, hashes, niveles y parámetros. No denominarlo
prueba ciega. Nueva escucha humana pendiente. Métricas no sustituyen percepción.

## D. Referencias independientes: búsqueda incompleta

Se clonó [dmrgo](https://github.com/USA-RedDragon/dmrgo/tree/f78e033e90559995213498973fe9d75e9bd45b93),
cuya [licencia](https://github.com/USA-RedDragon/dmrgo/blob/f78e033e90559995213498973fe9d75e9bd45b93/LICENSE)
declara MIT. `v2/vocoder/frame.go` atribuye su silencio a MMDVMHost;
`v2/vocoder/ambe72_test.go` espera `b9e881526173002a6b` como slot de 72 bits.
Es un formato intercalado para transmisión: no compararlo directamente con
los nueve bytes canónicos del banco experimental.

**No se ejecutó esa referencia ni se verificó su cadena de procedencia o
independencia respecto de los candidatos.** Incluso un silencio validado no
probaría parámetros de voz ni interoperabilidad bidireccional. No se agregaron
fuentes/binarios de terceros al repo. No hay aún oráculo independiente autorizado
PCM/AMBE de voz ni pruebas independientes ejecutadas de FEC/errores/packing DMR.

**INTEROPERABILIDAD NO DEMOSTRADA.** No congelar `VocoderProvider` de 49 bits.

## Reanudación y cierre

- C1, C2 y C3 completadas. La alineación del bloque B quedó localizada en C3.
- Implementar C con pruebas automatizadas y paquete WAV/manifiesto.
- Acotar D y registrar referencias descartadas y motivos.
- Actualizar informe/README/PR con resultados reales y omisiones explícitas.
- Separar funcionalidad, calidad audible, interoperabilidad y estabilidad.
- No repetir soaks de 600 s sin cambios materiales de estabilidad/rendimiento.
- Evaluación legal independiente: éxito técnico no autoriza redistribución ni
  resuelve licencias/procedencia/patentes. Fase A/B mantiene sus limitaciones.
- Si OpenDMR exige corrección extensa, documentar bloqueo upstream y proponer
  suspender esa línea, priorizando BLIP25 para investigación.
- Pedir revisión arquitectónica antes de integración o corrección extensa.

Runtime siguiente: Docker local sin red, usuario no root, filesystem de solo
lectura y resultados en volumen explícito. Sin BrandMeister, RF, credenciales,
pve-dev, Raspberry, cambios al gateway estable ni merge. Mantener PR Draft.
