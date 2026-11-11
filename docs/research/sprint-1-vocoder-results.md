# Sprint 1 — Fase B offline: resultados reales

2026-11-09. Rama spike/sprint-1-ambe-vocoder; continuación del PR #10 Draft.
No se modificó el gateway estable. Banco reproducible en
[experiments/vocoder](../../experiments/vocoder/README.md).

## Dictamen separado por dimensión

| Dimensión | OpenDMR | BLIP25 |
| --- | --- | --- |
| Build Linux x86-64 | Correcto desde commit fijado | Correcto desde commit fijado |
| Funcionalidad de API/stream | Encode/decode, roundtrip y cross-decode completados | Encode/decode, roundtrip y cross-decode completados |
| Estabilidad | 600.0019 s, 30001 frames/dirección, 0 fallos, 0 deadlines >20 ms | Misma duración y conteo, 0 fallos, 0 deadlines >20 ms |
| Rendimiento medido | Compatible con un canal de 50 frames/s en este host | Compatible con un canal de 50 frames/s en este host |
| Calidad audible | Rechazada en esta muestra cuando codifica; su decoder entiende BLIP25 con artefactos | Roundtrip valorado positivamente por el usuario en esta muestra |
| Interoperabilidad DMR | NO demostrada por referencia independiente | NO demostrada por referencia independiente |
| Redistribución/producción | NO autorizada por este estudio | NO autorizada por este estudio |

Estos resultados prueban viabilidad de ejecución de software; no convierten
salida PCM de longitud correcta en prueba de fidelidad ni de DMR interoperable.

## Fuentes y entorno

- OpenDMR d28164b39ba4d91ad5948ff22707937f8944f70f; make gcc/g++ con flags
  upstream O3, wrapper O2/C++17, link estático a libopendmr.a.
- BLIP25 d1762813b7142c021f4105c832bf7f060d1249fa; cargo release, Rust 1.85.1.
  Cargo.lock del adaptador sin dependencias runtime adicionales.
- Base rust:1.85-bookworm fijada al índice
  sha256:e51d0265072d2d9d5d320f6a44dde6b9ef13653b035098febd68cce8fa7c0bc4.
- GCC Debian 12.2.0-14; Python 3.11.2; Linux WSL2 5.15.167.4, x86-64;
  host AMD Ryzen 7 9800X3D. Docker local, runtime sin red, UID 1000,
  read-only, cap_drop ALL, no-new-privileges, 2 CPU/1 GiB total para el banco.
- Imagen ejecutada en el soak:
  sha256:9ca4d2a8e37c356132ca1c9dcf36f4e27d1bf0136a30d9cf75dbf436a4045761.
  Tras añadir lockfile/test de robustez, imagen del test final:
  sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab.
  Workers y benchmark no cambiaron entre ambas; cambió el empaquetado reproducible
  y se añadió test_workers.py. Docker confirmó exit 0, OOMKilled=false, RestartCount=0.
- Voz: Open Speech Repository, primeros 20 s del archivo OSR_us_000_0010_8k.wav,
  más 1 s de silencio, tono 440 Hz y ruido con semilla. Hash y permiso en README
  del banco. El WAV original no era saturado: RMS 1570.76, DC -0.31.

El build requirió corregir dos errores del banco, no de los candidatos: ruta
relativa del Cargo.toml y delimitador del comando reset. No hubo parche upstream.
No se hicieron cambios extensos para ocultar incompatibilidades de audio.

## Latencia nativa e IPC (soak a 50 frames/s)

Milisegundos, p99 / máximo; p50/p95 y conteos completos en results.json.

| Medición | OpenDMR | BLIP25 |
| --- | ---: | ---: |
| Encode dentro del worker | 0.722 / 0.961 | 0.179 / 0.541 |
| Decode dentro del worker | 0.030 / 0.307 | 0.051 / 0.463 |
| Encode incluyendo IPC | 0.855 / 1.109 | 0.323 / 1.211 |
| Decode incluyendo IPC | 0.320 / 0.652 | 0.357 / 0.935 |
| Demora de cola/scheduler desde tick | 0.752 / 2.020 | 1.160 / 2.922 |
| Roundtrip desde tick, cola + IPC | 1.534 / 2.921 | 1.545 / 3.606 |

Tiempo "nativo" incluye conversión PCM/FEC/packing de cada adaptador, no solo el
algoritmo. IPC incluye hex, pipes y planificación. Cola es la espera real desde
tick en este scheduler, con máximo una petición pendiente por worker y orden
alternado entre candidatos; no modela colas multicanal del gateway ni Node/N-API.
Ambos workers coejecutaron los mismos 600 s, cada uno a 50 frames/s. No son dos
mediciones con host exclusivo. No se descartaron frames atrasados.

Throughput sin pacing, separado: 1000 roundtrips de una trama de voz repetida,
tras 100 de warmup: OpenDMR **2346.1 frames/s**, BLIP25 **3185.9 frames/s**.
No extrapolar ese máximo observado a usuarios simultáneos ni a todas las señales.
El soak usó corpus variado y constituye la evidencia de tiempo real de un canal.

## Recursos y estabilidad

| Medición por worker | OpenDMR | BLIP25 |
| --- | ---: | ---: |
| Tiempo real | 600.0019 s | 600.0019 s |
| Encode y decode por dirección | 30001 | 30001 |
| CPU media respecto de un núcleo | 2.14% | 0.95% |
| Pico RSS muestreado | 1.87 MiB | 1.27 MiB |
| Fallos / deadlines incumplidos | 0 / 0 | 0 / 0 |

/proc cada 5 s, reloj monotónico. RSS inicial 1957888/1327104 bytes; final
970752/1044480 bytes. No se observa crecimiento sostenido; no equivale a prueba
de ausencia de fugas. CPU/RSS excluyen harness Python y caché de imagen; no son
el consumo total del contenedor. Ver muestras crudas para variabilidad.

## Funcionalidad, tramas dañadas y formatos

Por encoder: 50 frames de silencio, 50 tono, 50 ruido y 1000 de voz; cada secuencia
se decodificó con ambos candidatos. Todos devolvieron 9 bytes encode y 320 bytes
PCM/frame, sin errores del worker. El banco adicional rechazó 7 longitudes
inválidas por candidato, procesó 72 perturbaciones de un bit y 100 frames aleatorios
sin crash, y verificó reset/reanudación. No se afirmó corrección FEC de esos casos.

Canal experimental: code vectors canónicos 24/23/11/14 MSB-first. BLIP25 usa
encode_info/decode_info y FEC compartido, no encode_frame con interleave P25.
Esto demuestra que ambos adaptadores consumen el formato elegido, no que la
interpretación de parámetros sea la de una implementación independiente DMR.

**Contrato de 49 bits no congelado.** No se incorporó VocoderProvider al gateway.
Los fixtures independientes dvsi_gold.bin/engine_golden.bin no están en el checkout
de BLIP25. Su test de conformidad puede imprimir SKIP y terminar como éxito;
no se ejecutó/contó como aprobado. Los goldens públicos del propio códec no se
usaron como oráculo independiente. La búsqueda no obtuvo un vector redistribuible
independiente en las fuentes revisadas; no implica que no exista en otros lugares.

## Audio: diagnóstico objetivo y escucha del usuario

WAVs de 20 s generados: original, ambos roundtrips y ambos cruces. No se normalizó
ganancia, filtró ni editó para hacer pasar una prueba. Valores del corpus de voz:

| Encode → decode | RMS salida | Muestras en extremos int16 |
| --- | ---: | ---: |
| OpenDMR → OpenDMR | 5638.55 | 0 |
| OpenDMR → BLIP25 | 983.33 | 3 de 160000 |
| BLIP25 → OpenDMR | 11129.80 | 0 |
| BLIP25 → BLIP25 | 1659.75 | 0 |

Original RMS 1570.76. La misma secuencia de bits produce niveles muy distintos
según decoder; podría involucrar escalas de ganancia, síntesis, interpretación
de parámetros o combinación. No se atribuye una causa definitiva sin referencia.
El tono OpenDMR→OpenDMR arroja RMS 20215.92 frente a aproximadamente 4242.64 de
entrada, otra señal a investigar. No corregir ganancia arbitrariamente antes
de medir contra un vector independiente.

Silencio: RMS de salida entre 0.17 y 2.68 (unidades int16), sin saturación; valores
no cero pueden ser ruido de confort. Los extremos int16 son un detector limitado:
no detecta un limitador interno con techo menor ni toda distorsión. La proporción
de ceros, DC y RMS se registra, no se usa como sustituto de inteligibilidad.

### Evaluación humana recibida después del baseline

El usuario escuchó los WAVs entregados y reportó el 2026-11-09:

| Archivo / ruta | Observación del usuario |
| --- | --- |
| blip25-to-blip25-speech.wav | Percibido idéntico al original, calidad impecable y mismo volumen |
| blip25-to-opendmr-speech.wav | Voz comprensible, ganancia excesiva, saturación percibida, ruido de fondo y plops |
| opendmr-to-blip25-speech.wav | Ininteligible, ruido digital |
| opendmr-to-opendmr-speech.wav | Ininteligible, ruido digital |

Es una escucha subjetiva de un usuario sobre esta muestra, no una prueba ciega,
MOS ni igualdad de muestras PCM. Equipo, nivel de reproducción y condiciones no
se registraron. La observación de volumen igual no reemplaza el RMS medido.
Los resultados automáticos crudos conservan su estado original, anterior a esta
escucha; esta sección es la actualización humana, no una medición retrospectiva.

Interpretación: las dos rutas que fallan comparten el origen OpenDMR. Priorizar
revisión de su cadena de encode, preparación PCM y empaquetado/adaptador; no
atribuir todavía el defecto exclusivamente al códec upstream. Que su decoder
reproduzca BLIP25 inteligiblemente acota el problema, pero no valida todos sus
parámetros ni demuestra que bajar ganancia elimine los artefactos. No corregir
un fallo de codificación/formato mediante normalización de volumen.

BLIP25 pasa la evaluación audible informal de su roundtrip en esta muestra;
interoperabilidad independiente y evaluación legal permanecen sin resolver.

## Evaluación legal independiente

Ninguna métrica técnica elimina estas observaciones de Fase A:

- OpenDMR combina LICENSE/CREDITS que dicen GPL-2.0 con encoder/mbeenc.cpp y
  encoder/rand_gen.cc GPL-3.0-or-later y decoder GPL-2.0-or-later, más FFTPACK/PFFFT.
  Resolver versiones/compatibilidad y preservar avisos antes de redistribuir.
  rand_gen.cc contiene seed estático global: se eligió aislamiento por proceso;
  no se promueve un addon multicanal compartido sin auditoría de estado.
- BLIP25 declara MIT, pero ATTRIBUTION/PATENT_NOTICE describen núcleo y constantes
  recuperados de binario. El origen, derechos sobre datos y patentes requieren
  evaluación propia. Los permisos del código no conceden derechos de terceros.
- La observación preliminar sobre US8359197 y jurisdicciones del plan sigue abierta.
  Este spike no es clearance ni asesoramiento legal, ni presume exención por ser
  offline. No se publicaron imágenes ni ejecutables de los candidatos.
- Separar procesos facilita pruebas/aislamiento, pero NO constituye una solución
  automática de licencias o una autorización de redistribución conjunta.

Fuentes legales/técnicas: links por commit de [Fase A](sprint-1-vocoder-plan.md),
CREDITS/encabezados de OpenDMR y ATTRIBUTION.md/PATENT_NOTICE.md/Cargo.toml de BLIP25.

## Recomendación Sprint 1

Priorizar BLIP25 como candidato técnico para la siguiente investigación: tiene
margen de rendimiento y evaluación humana positiva del roundtrip de esta muestra.
OpenDMR queda bloqueado como candidato bidireccional hasta diagnosticar su cadena
de encode/adaptador; su build y soak exitosos no compensan voz ininteligible.
**No seleccionar todavía proveedor de producción ni integrar el gateway**:
conseguir oráculo independiente y resolver redistribución/procedencia por separado.

Siguiente paso acotado: diagnóstico de encode/packing OpenDMR y ampliar escucha
con más voces/muestras; vectores independientes
autorizados para validar parámetros/ganancia/FEC; pruebas de aislamiento y
sanitizers antes de un addon. Sanitizers y carga multicanal no ejecutados en este
baseline y no se presentan como aprobados. Mantener PR Draft para arquitectura.

## Evidencia y comandos

[results.json](../../experiments/vocoder/evidence/results.json),
[samples.jsonl](../../experiments/vocoder/evidence/samples.jsonl),
[worker-tests.json](../../experiments/vocoder/evidence/worker-tests.json).

Ejecutados: docker build del Dockerfile experimental; smoke `bench.py --soak 0`;
runtime sin red `bench.py --soak 600`; build final con lockfile y `test_workers.py`;
docker inspect confirmó exit 0, sin OOM/reinicios. La receta equivalente Compose
está documentada en experiments/vocoder/README.md. Los límites se aplicaron por
docker run en esta corrida, no se atribuye falsamente una ejecución a Compose.
No se usaron pve-dev, Raspberry, BrandMeister, RF ni credenciales.
