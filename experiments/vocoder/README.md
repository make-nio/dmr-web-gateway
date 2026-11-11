# Banco experimental AMBE+2, sin integración con gateway

Linux x86-64 sobre Docker local. Solo fuentes fijadas; no descarga de firmware,
hardware DVSI, RF, master real ni cambios a Homebrew. Build usa Internet para
fuentes/dependencias/corpus; la ejecución tiene network_mode none.

## Reproducir

Desde esta carpeta, con Docker Compose en Linux/WSL2 y directorio results
escribible por UID 1000:

```sh
mkdir -p results
docker compose -p dmr-vocoder-spike build
docker compose -p dmr-vocoder-spike run --rm bench python3 test_workers.py
docker compose -p dmr-vocoder-spike run --rm bench python3 bench.py --soak 0
docker compose -p dmr-vocoder-spike run --rm bench python3 bench.py --soak 600
```

Cada corrida sobrescribe results.json y las muestras de esa carpeta; preservar
resultados previos antes de repetir. No ejecutar dos bancos sobre results a la vez.
Compose limita a 2 CPU/1 GiB, user 1000, rootfs read-only, sin capacidades ni
privilegios nuevos. El único bind escribible es results. No usar el stack SRE.
La imagen contiene terceros compilados para investigación local; no publicarla
como producto. Su éxito técnico no concede derechos de redistribución.

## Qué mide y qué NO afirma

- Dos workers persistentes: OpenDMR C++ y BLIP25 Rust. Una sesión/dirección por
  objeto, candidatos separados por proceso; no se promete seguridad multihilo.
- PCM mono 8 kHz, 160 muestras int16 little-endian por frame. Canal experimental
  de 9 bytes en orden canónico de code vectors 24/23/11/14, MSB-first, no burst DMR.
  BLIP25 usa encode_info/decode_info + FEC, NO el interleave P25 de encode_frame.
- No se exporta ni congela un contrato de 49 bits. Falta un vector independiente
  con derechos claros para probar orden de parámetros e interoperabilidad DMR.
- IPC por stdin/stdout, líneas hex E/D/R. Entrada de tamaño incorrecto rechazada;
  deadline de respuesta 5 s. Es un protocolo de laboratorio, no API de producción.
- codec = tiempo medido dentro del worker alrededor de conversión PCM, códec y
  FEC/packing. No es tiempo puro del algoritmo sin wrapper; diferencias de
  adaptación entre C++/Rust deben considerarse al comparar.
- IPC = tiempo desde envío de la petición hasta recibir respuesta, incluyendo
  hex, pipes y planificación. No incluye una cola de aplicación de producción.
- scheduledRoundtrip incluye espera/atraso desde el tick previsto, encode,
  decode e IPC; queueDelay registra esa espera. El orden de candidatos alterna
  por frame. Se mide el camino real del banco, no latencia Node/N-API inexistente.
- Throughput sin pacing: 1000 roundtrips tras 100 de calentamiento; máximo
  observado repitiendo una sola trama de voz, no capacidad garantizada ni número
  de usuarios. El soak sí recorre silencio, tono, ruido y voz completos en ciclo.
- Soak: ambos candidatos coejecutan durante >=600 s reales, 50 frames/s cada uno,
  >=30000 encode y decode cada uno. No se omiten frames atrasados: se cuenta
  deadlineMisses (>20 ms desde tick), percentiles y máximo. Los resultados no
  corresponden a dos pruebas con host exclusivo; se documenta la coejecución.
- CPU/RSS por worker desde /proc cada 5 s. CPU% respecto de un núcleo; RSS no
  incluye harness Python/imagen/caché. No confundir con consumo total del sistema.
  samples.jsonl permite examinar crecimiento; no garantiza ausencia de fugas.

## Corpus y calidad

Voz: **Open Speech Repository**, Harvard sentences, archivo
OSR_us_000_0010_8k.wav; primeros 20 s para este banco.
Origen: https://www.voiptroubleshooter.com/open_speech/american.html
Permiso publicado: uso/copia/modificación para pruebas VoIP e investigación con
atribución. SHA256 del WAV completo:
`a4bf9becd046d7aedb6d05b6e12347a6294a44f74d263089c636fb0a2b1e6561`.
Se agregan 1 s de silencio, 1 s de tono 440 Hz y 1 s de ruido con semilla fija.
No hay grabaciones privadas ni datos de estaciones reales.

El banco produce original y cuatro WAV de speech (dos roundtrips y dos cruces).
RMS/DC/clipping/ceros son diagnósticos, NO inteligibilidad, MOS ni calidad audible
aprobada. Escuchar A/B humano y anotar palabras/frases y artefactos antes de elegir
proveedor de producción. No aplicar umbral universal a ruido de confort.
Pruebas de flips/random solo verifican no-crash y longitud de salida; no certifican
corrección FEC. Un cross-decode que devuelve PCM tampoco certifica DMR.

## Dependencias y procedencia

Dockerfile fija índice rust:1.85-bookworm, commits upstream y hash de corpus.
Cargo.lock fija el grafo Rust sin dependencias runtime adicionales en esta ruta.
Paquetes apt proceden de Bookworm, sin snapshot temporal: repetir puede cambiar
paquetes del entorno. Registrar imagen y versiones con cada resultado.
No se vendorizan fuentes ni binarios upstream en el PR. Licencias/patentes se
evalúan por separado en el informe: no inferir permiso de despliegue del build.

Referencias de procedencia: docs/research/sprint-1-vocoder-plan.md (en la raíz
del repo), más CREDITS/avisos por archivo de OpenDMR y ATTRIBUTION.md y
PATENT_NOTICE.md de BLIP25 en los commits fijados. Los goldens independientes de
BLIP25 no se distribuyen y su test puede reportar PASS tras imprimir SKIP.
