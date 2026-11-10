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

- C1 de A completada; queda pendiente la traza de parámetros y el diagnóstico B.
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
