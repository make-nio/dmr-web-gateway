# Sprint 1 / Fase C — checkpoint parcial

Estado: investigación offline autorizada; **Fase C incompleta**. Checkpoint
solicitado por el usuario para preservar avances antes del límite de saldo.
Continuar en `spike/sprint-1-ambe-vocoder`, PR #10 OPEN/DRAFT.

## Alcance y evidencia

Los resultados medidos y la escucha previa están en
[Fase B](sprint-1-vocoder-results.md). No son pruebas nuevas de Fase C.
Este checkpoint contiene inspección de fuentes y preparación de referencias.
**No se ejecutaron aún las comparaciones CLI/wrapper, el corpus ampliado ni
el diagnóstico instrumental de saturación. No hay corrección implementada.**

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
wrapper: `-O2 -std=c++17`, enlazando la misma biblioteca. Falta registrar versión
de compilador para la nueva corrida.

Próxima prueba sin editar upstream:

1. Extraer el mismo PCM mono 8 kHz/int16 LE y registrar SHA-256.
2. Ejecutar CLI y wrapper en procesos nuevos; comparar todas las tramas byte/bit,
   primera divergencia y diferencias posteriores, separando información/FEC/padding.
3. Decodificar ambas secuencias con ambos candidatos desde estado inicial nuevo.
4. Construir harness mínimo que observe b[9], bits49 y trama72 con las funciones
   originales. Localizar dónde se pierde el significado de los parámetros.
   No generar audio con un packing corregido ni reescribir upstream.

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

- Implementar A/B con evidencia por trama, comandos, hashes y entorno.
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
