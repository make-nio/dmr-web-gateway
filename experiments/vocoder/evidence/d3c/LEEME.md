# D3c · Escucha exploratoria en español rioplatense

Los dos WAV son adaptaciones de la lectura de **Gabriel Quagliano** (23 de octubre de 2011) de la primera parte de *Rosario (Argentina)*, texto de los colaboradores de Wikipedia en español. [Grabación y créditos](https://commons.wikimedia.org/wiki/File:Es-Rosario_(Argentina)_Parte_1-article.ogg) · [Artículo y atribución a sus autores](https://es.wikipedia.org/wiki/Rosario_(Argentina)). La grabación y estas dos adaptaciones se distribuyen bajo [Creative Commons Atribución-CompartirIgual 3.0 Unported](https://creativecommons.org/licenses/by-sa/3.0/).

Cambios: fragmento [00:15, 00:35), conversión a PCM mono s16le a 8 kHz y paso por dos pares encoder/decoder. Ambos WAV conservan su nivel de salida. El manifiesto identifica las rutas y los hashes. La escucha exploratoria del usuario queda pendiente; D3b mantiene sus resultados y su evaluación formal inglesa pendiente.

## Reproducción

Verificar el OGG original por su SHA-1 publicado en Commons `56448464985566dcf898fb16422d802d19a2b371` y el SHA-256 del manifiesto. Desde la raíz del checkout en WSL2, con FFmpeg 6.1.1-3ubuntu5 y la imagen local del banco:

```sh
ffmpeg -nostdin -v error -y -i ../rosario-d3c.ogg -ss 15 -t 20 -map_metadata -1 -ac 1 -ar 8000 -c:a pcm_s16le ../rosario-d3c-input.wav
v="$PWD/experiments/vocoder"
mkdir -p "$v/results/d3c"
docker run --rm --pull never --network none --read-only --user 1000:1000 \
  --cap-drop ALL --security-opt no-new-privileges --cpus 1 --memory 512m \
  --tmpfs /tmp:rw,exec,size=64m -v "$v:/bank:ro" \
  -v "$(realpath ../rosario-d3c-input.wav):/input.wav:ro" -v "$v/results/d3c:/results" \
  sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab \
  python3 -B /bank/d3c/run_cross.py
```

En la corrida publicada se escribió en evidence/d3c. Las trazas RX/TX registran las comparaciones de formato por trama. Cada ruta completó 1000 tramas y generó 160000 muestras.
