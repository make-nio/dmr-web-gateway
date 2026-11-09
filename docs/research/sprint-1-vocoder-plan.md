# Sprint 1 — investigación inicial y plan experimental

Actualización: la ejecución posterior del baseline de Fase B y sus resultados
se encuentran en [sprint-1-vocoder-results.md](sprint-1-vocoder-results.md).
Las declaraciones de estado de este plan describen la entrega inicial de Fase A.

Fecha: 2026-11-09. Base: dbed6177dff0bb647b1b399b3e1ba550637f7b68.
Estado: inspección de fuentes; NO se ejecutaron compilaciones, mediciones,
escuchas ni pruebas de interoperabilidad en esta fase. Este documento presenta
el plan antes de desarrollar el banco. Ningún resultado de rendimiento se supone.

## Revisiones inspeccionadas

| Candidato | Commit | Fecha del commit |
| --- | --- | --- |
| MW0MWZ/OpenDMR | d28164b39ba4d91ad5948ff22707937f8944f70f | 2025-12-31 |
| OpenBLIP25/blip25-vocoder | d1762813b7142c021f4105c832bf7f060d1249fa | 2026-08-11 |
| nakhonthai/vocoder_plugin | 390dc6a8770bbafa57d92ebb8f932e8fccce2a1f | 2021-11-16 |

Las fechas son señales de mantenimiento, no pruebas de madurez. Se descargaron
fuentes en el espacio de trabajo; no se incorporaron terceros ni binarios al repo.

## Comparación técnica por inspección

| Aspecto | OpenDMR | BLIP25 | vocoder_plugin |
| --- | --- | --- | --- |
| Encode real en código | MBEEncoder, análisis IMBE/OP25 y parámetros DMR | Motor Rust de análisis/encode, API Vocoder | imbe_encode y cuantización AMBE en encode_2450 |
| Decode real en código | mbelib-neo, mbe_processAmbe2450Data | Motor Rust de síntesis/decode | mbelib, decode_2450 y variante con protección |
| Entrada PCM | API 160 muestras int16/8 kHz | API 160 muestras, adaptación por verificar | API int16, estado en objeto C++ |
| Formato | API 9 bytes, 72 bits en orden canónico A/B/C; NO asumir burst DMR listo | HalfRate; encode_frame usa interleave P25; foreign_protocol muestra code_vectors para DMR | Separar 2450 crudo de 2450x1150, revisar orden de bits |
| Integración futura | ABI C y CLI; proceso persistente o addon N-API | Rust; proceso persistente, N-API o WASM sujeto a prueba | Clase virtual C++/dlopen; wrapper estable necesario |
| Build | Make, gcc/g++, libm; decoder/encoder vendorizados | Rust >=1.85, Cargo.lock; sin deps runtime por defecto, serde opcional | Make, gcc/g++, imbe_vocoder externo no fijado |
| Madurez observable | API compacta; no suite de conformidad independiente identificada | Tests de streaming, garbage, regresión y ejemplos; separar pruebas omitidas | Código antiguo, interfaz de plugin, sin prueba pública independiente identificada |

OpenDMR opendmr.cpp implementa extracción Golay/descrambling y síntesis. Su
contador errs se alimenta del procesamiento de parámetros después del FEC:
no debe interpretarse sin prueba como un contador completo de errores del canal.
Se comprobará con flips de bits conocidos. También se revisarán estado global,
RNG y aislamiento de canales antes de prometer concurrencia.

OpenDMR y el plugin comparten linaje OP25/mbelib: acuerdo entre ambos no equivale
a una referencia independiente. BLIP25 expone rutas P25 y un núcleo compartido;
no se conectará encode_frame directamente al empaquetado DMR.

## Procedencia y revisión legal preliminar

- OpenDMR presenta LICENSE GPL-2.0, pero encoder/mbeenc.cpp declara GPL-3.0-or-later;
  decoder/mbelib.c declara GPL-2.0-or-later y procedencia mbelib-neo. PFFFT/FFTPACK
  llevan avisos propios. No basta clasificar el conjunto como GPL-2.0 a partir
  de la etiqueta GitHub. Inventariar todos los archivos y opciones "or later",
  conservar avisos y determinar licencia compatible del conjunto antes de distribuir.
- BLIP25 declara MIT, pero ATTRIBUTION.md describe ingeniería inversa de un
  binario de referencia y recuperación de constantes. PATENT_NOTICE.md advierte
  sobre uso, compilación y distribución. MIT no concede derechos sobre patentes
  de terceros ni resuelve procedencia de datos. Revisar también por qué Cargo.toml
  no incluye los documentos de procedencia/patentes en su lista de empaquetado.
- El plugin contiene avisos ISC en fuentes, pero depende de imbe_vocoder externo;
  sin revisión exacta de esa dependencia no se afirma que el binario sea permisivo.
  No descargar los plugins precompilados enlazados por HTTP en el README.
- BLIP25 señala US8359197 como relevante. Google Patents muestra estado activo y
  fecha prevista 2028-05-20, pero advierte que su estado no es conclusión legal.
  No se certificó vigencia, alcance de reivindicaciones ni equivalentes por país.
  La residencia del usuario no determina todas las jurisdicciones de uso/distribución.
  Consultar registros oficiales y asesoramiento especializado antes de liberar
  ejecutables o habilitar un servicio. Una prueba offline no crea por sí sola una
  exención de patentes. No se da autorización legal de uso comercial ni redistribución.

## Selección propuesta

1. OpenDMR como primer candidato: ABI C simple, rutas encode/decode visibles y
   dependencias incluidas; prioridad a detectar errores de formato y calidad.
2. BLIP25 como segundo candidato técnico: implementación distinta para contraste,
   APIs de información/FEC disponibles. Procedencia y patentes siguen como riesgos
   independientes de cualquier éxito técnico.

Plugin como reserva: comparte linaje con OpenDMR, requiere resolver dependencia
externa y aporta menos independencia al contraste. No seleccionar aún proveedor
de producción ni incorporar ninguno al gateway.

## Plan experimental reproducible (fase B, pendiente)

1. Fijar commits de candidatos/dependencias, hashes de corpus, imagen de build y
   compiladores. Compilar desde fuentes en Docker Linux x86-64 local. Separar
   descarga/build del runtime sin red, no root y read-only; nunca usar pve-dev.
2. Crear banco separado bajo experiments/vocoder. Adaptadores de proceso persistente,
   sin cargar terceros en Node/Homebrew. Mantener estado por sesión/dirección,
   serializar llamadas por instancia y probar independencia de dos instancias.
3. Corpus: silencio, impulso, tonos, ruido con semilla, amplitudes pequeñas y cerca
   de clipping, más voz real con permiso/documentación de origen. Versionar hashes,
   no capturas de terceros con redistribución dudosa. PCM mono 8 kHz, s16le, 160
   muestras/20 ms. No limitar pruebas a tonos ni a una sola trama.
4. Validar encode y decode por separado; roundtrip; secuencias, reset, fronteras,
   frames truncados, padding, estados de pérdida y flips de bits/FEC. Fallos y
   casos omitidos deben diferenciarse. Ejecutar sanitizers cuando el build lo permita.
5. Formato explícito: parámetros de voz 49 bits frente a FEC 72 bits y a burst DMR.
   Definir orden de bits con fixtures antes de normalizar adaptadores. Vectores
   independientes con procedencia/autorización se buscan primero. Los fixtures
   públicos de BLIP25 son generados por él mismo; sus engine_golden/dvsi_gold
   externos no están incluidos. No contabilizar tests omitidos como conformidad.
   Cruces A-encode/B-decode y viceversa son evidencia adicional, no certificación.
6. Medir por llamada encode/decode p50/p95/p99/máximo con reloj monotónico tras
   calentamiento; throughput sin pacing por separado; tiempo CPU, RSS y cgroups,
   incluyendo y excluyendo IPC. Registrar CPU host, cuotas, compilador y flags.
   Criterio experimental de tiempo real: p99 por dirección <20 ms en un canal,
   más margen medido para encode+decode/IPC; no prometer capacidad antes de medir.
7. Soak de >=600 s de reloj por candidato, 50 frames/s, >=30000 frames continuos
   por dirección, sin recrear el proceso por frame. Registrar errores, deadlines,
   máximos muestreados y tendencia de memoria; no confundir procesamiento acelerado
   de 10 minutos de audio con 10 minutos reales de estabilidad.
8. Producir WAV original/roundtrip/cross-decode, medir RMS, DC, clipping, energía
   de silencio y discontinuidades; alinear demora antes de comparar señales.
   SNR no prueba inteligibilidad. Escucha A/B humana con frases y reporte explícito;
   si no hay escucha, marcar calidad audible pendiente. Sin inventar MOS.
9. Publicar comandos, logs, versiones, métricas crudas y límites. Resultado separado
   para build, funcionalidad, estabilidad, calidad, conformidad y redistribución.
   Abrir Draft del spike; no fusionar ni integrar transporte en esta fase.

## Contrato conceptual VocoderProvider

Contrato propuesto, no implementación ni dependencia del gateway:

```ts
interface VocoderProvider {
  readonly id: string;
  readonly frameFormat: 'ambe2450-info-msb49';
  encode(pcm160: Int16Array): Promise<Uint8Array>;
  decode(frame7: Uint8Array): Promise<Int16Array>;
  reset(): Promise<void>;
  close(): Promise<void>;
}
```

Una sesión con estados encode/decode independientes; llamadas seriales y cola
acotada, errores tipados para entrada/timeout/backend. 49 bits en 7 bytes MSB-first
con los 7 bits finales de padding en cero. El orden exacto de los 49 parámetros
queda sujeto a fixture de referencia antes de congelar el contrato. PCM en IPC
s16le, 160 muestras; FEC/interleave/burst fuera del provider, sin confundir tasas
2450/3600. Un backend de 9 bytes requiere adaptación verificada, no truncamiento.

## Fuentes

- [OpenDMR código](https://github.com/MW0MWZ/OpenDMR/tree/d28164b39ba4d91ad5948ff22707937f8944f70f): opendmr.cpp/.h, Makefile, LICENSE y encabezados decoder/encoder.
- [BLIP25 código](https://github.com/OpenBLIP25/blip25-vocoder/tree/d1762813b7142c021f4105c832bf7f060d1249fa): Cargo.toml, ATTRIBUTION.md, PATENT_NOTICE.md, examples/foreign_protocol.rs, tests/golden_corpus.rs.
- [Plugin código](https://github.com/nakhonthai/vocoder_plugin/tree/390dc6a8770bbafa57d92ebb8f932e8fccce2a1f): Makefile, vocoder_plugin.cpp/.h y avisos de mbelib.
- [Registro agregado US8359197B2](https://patents.google.com/patent/US8359197B2/en): advertencia de estado no concluyente y enlaces a registros oficiales.

Esta revisión no es asesoramiento jurídico ni auditoría exhaustiva de cada dependencia.
