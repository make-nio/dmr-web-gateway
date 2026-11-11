# D3b · Cruce experimental de voz entre BLIP25 y OpenDMR

**Criterio técnico cumplido en RX y TX. Escucha pendiente en ambos sentidos.**
Se usó un solo pasaje de 20 s (Open Speech Repository, OSR 0010, desde el
inicio). El PCM original mono s16le a 8 kHz tiene 160000 muestras y SHA-256
`677d09d1c91e7cae74c0a5dc3e5e3bcd3ded3634ed471bcbca6dd65ea82e2279`.
OpenDMR d28164b39ba4d91ad5948ff22707937f8944f70f y BLIP25
d1762813b7142c021f4105c832bf7f060d1249fa. Resultados específicos
de esas revisiones, esta interfaz de voz y este pasaje.

| Sentido | Productor y consumidor | Tramas / muestras | Errores de ejecución / FEC BLIP25 | RMS / pico absoluto | Muestras en extremos int16 |
|---|---|---|---|---|---|
| RX | BLIP25 encode → OpenDMR decode con conversión C6 ×1 | 1000 / 160000 | 0 / 0 | 1686,08 / 10630 | 0 |
| TX | OpenDMR encode corregido C5 → BLIP25 decode | 1000 / 160000 | 0 / 0 | 3023,37 / 26060 | 0 |

En RX ninguna muestra flotante excedió el umbral de conversión de C6.
En TX se observó la salida int16 del worker. El recorte interno del motor
BLIP25 queda sin medir. El RMS del estímulo fue 1570,76 y el pico 10751.
Ambos WAV tienen 20 s, 8000 Hz y un canal. Un proceso nuevo por operación
stateful mantuvo su estado durante todo el pasaje. En TX la secuencia
archivada procede de un único encoder continuo de C5.

**Interfaz verificada antes de sintetizar.** BLIP25 en HalfRate3600x2450
analiza 160 muestras por trama y genera cuatro palabras de información
de 12,12,11,14 bits. El worker usa encode_code_vectors/decode_code_vectors
y empaqueta sus palabras de 24,23,11,14 bits MSB primero (9 octetos).
En OpenDMR corregido la capa local es A24|B23|C25 con B alineado y
enmascarado; los últimos 25 bits corresponden a esas dos palabras crudas.
RX entra directamente a decode_ambe_frame y al sintetizador original,
que interpreta los índices de C2; C6 toma las muestras antes de la
conversión final. TX reutiliza las tramas con correspondencia de parámetros
y B corregido de C5 (adapted72). La frontera de intercambio es de 72 bits
locales. El intercalado DMR de D2 y el de P25 quedan fuera de esta interfaz.

Los dos verificadores independientes desempaquetaron todas las tramas en
ambos sentidos, compararon los 49 bits y comprobaron reencodificación limpia
byte a byte. En TX los 49 bits coincidieron además con adaptedInput49 de C5.
El verificador Rust enlazó la rlib ya compilada de BLIP25. La traza C++ usó
decode_ambe_frame original y el empaquetado corregido de C5. El hash de la
secuencia TX coincidió con el de entrada de C6. Se comprobaron longitudes
y respuestas de worker; se verificó salida exitosa de los procesos.

**Artefactos para coordinación.** [RX.wav](../../experiments/vocoder/evidence/d3b/RX.wav)
· [TX.wav](../../experiments/vocoder/evidence/d3b/TX.wav) ·
[Manifiesto de hashes y métricas](../../experiments/vocoder/evidence/d3b/manifest.json)
· [Trazas por trama y paquetes individuales](../../experiments/vocoder/evidence/d3b).
Entregar un ZIP distinto a cada oyente. Cada ZIP contiene únicamente dos
pistas neutras y la hoja de instrucciones. La clave de diez palabras se
fijó antes de la corrida y su hash se registró en el manifiesto.
[Protocolo y clave exclusivos de coordinación](../../experiments/vocoder/d3b/coordinator.md).

| Resultado auditivo | Oyente 1 | Oyente 2 | Dictamen |
|---|---|---|---|
| RX | pendiente | pendiente | pendiente |
| TX | pendiente | pendiente | pendiente |

Cada sentido requiere ≥9/10 de **cada** oyente. La repetición del pasaje
puede facilitar el reconocimiento de la segunda pista. Se contrabalanceó
el orden y se pide cerrar la primera transcripción antes de escuchar la
segunda. El cruce aporta evidencia entre estos motores; la evaluación frente
al fabricante continúa pendiente.

## Reproducción

Desde la raíz del checkout en WSL2 con la imagen precargada:

```sh
v="$PWD/experiments/vocoder"
mkdir -p "$v/results/d3b"
docker run --rm --pull never --network none --read-only --user 1000:1000 \
  --cap-drop ALL --security-opt no-new-privileges --cpus 1 --memory 512m \
  --tmpfs /tmp:rw,exec,size=64m -v "$v:/bank:ro" -v "$v/results/d3b:/results" \
  sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab \
  python3 -B /bank/d3b/experiment.py
```

La corrida publicada escribió en evidence/d3b. El manifiesto conserva las
órdenes de compilación y los hashes de componentes, PCM, secuencias, trazas
y WAV. La etiqueta de escucha queda pendiente hasta recibir las cuatro
transcripciones.
