# D2a · Vector literal de silencio

Única entrada de información: `F801A99F8CE080`, con siete ceros de
relleno. Entrada de canal para el sentido inverso: `B9E881526173002A6B`.
El ejecutable C++ invoca directamente `emit` de C5, que C7 reutiliza
para proteger la información ya ordenada. Para recepción llama a
`decode_ambe_frame` sobre los bytes externos desintercalados. El ejecutable
Go llama a las dos funciones públicas de dmrgo con los literales independientes.
El verificador compara los bits MSB primero, comprueba la permutación y
su inversa contra las tablas publicadas y guarda los índices de diferencias.
La salida de 49 bits de OpenDMR se representa en hex añadiendo siete ceros
solo para su presentación. El padding emitido por Go se comprueba directamente.

Desde la raíz del checkout en WSL, disponer localmente de la imagen de C5,
del checkout limpio de dmrgo y del archivo oficial de Go. Ajustar las rutas
de los dos mounts si los archivos están en otro directorio. dmrgo queda
fijado en `f78e033e90559995213498973fe9d75e9bd45b93`; el archivo
`go1.27.4.linux-amd64.tar.gz` se verificó contra el SHA-256 del catálogo
oficial antes del ensayo y se verifica también dentro del contenedor.
[Archivo Go](https://dl.google.com/go/go1.27.4.linux-amd64.tar.gz) ·
[Metadatos de distribución](https://go.dev/dl/?mode=json&include=all).

```sh
v="$PWD/experiments/vocoder"
assets="$(dirname "$PWD")"
mkdir -p "$v/results/d2a"
docker run --rm --pull never --network none --read-only --user 1000:1000 \
  --cap-drop ALL --security-opt no-new-privileges --cpus 2 --memory 1536m \
  --tmpfs /tmp:rw,exec,size=900m \
  -v "$assets/go1.27.4.linux-amd64.tar.gz:/go.tgz:ro" \
  -v "$assets/dmrgo-reference:/dmrgo:ro" -v "$v/c5:/c5:ro" \
  -v "$v/d2a:/d2a:ro" -v "$v/results/d2a:/results" \
  sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab \
  python3 /d2a/run.py
```

La ejecución publicada usó `evidence/d2a` como directorio de salida. El
manifiesto registra comandos de compilación, revisiones, toolchains,
hashes de fuentes y ejecutables, resultados y posiciones. La compilación
Go usa la copia local del módulo con GOPROXY=off y GOTOOLCHAIN=local.
