# D2b · Cuatro tramas archivadas y errores simples

Se reutilizaron los dos ejecutables del banco D2a. La compilación offline verifica
que los hashes de fuentes y binarios coinciden con su manifiesto. Se leyó el
archivo de C5 fijado por SHA-256 y se seleccionaron las filas de índice 0–3.
`adaptedInput49` es la entrada de información; `adapted72`, el control de la
trama local protegida, sin intercalar. El manifiesto incluye el hash individual
de los nueve bytes locales de cada fila.

Primero se contrastan las cuatro codificaciones y las recuperaciones limpias.
Para cada inversión se parte del slot archivado intercalado, se invierte
únicamente el índice de canal indicado y se desintercala esa misma entrada
para OpenDMR. Los índices empiezan en cero, MSB primero. Para una posición
local k de C (47…71), el bit de información esperado es k−23 (24…48).
Los decodificadores se ejecutan por separado. Se comprueban los datos de
ambos, el padding Go y el estado de dmrgo. El desempaquetador OpenDMR expone
los bits recuperados; la comprobación de corrección usa esos bits. Una fila
fallida se guarda íntegra en el manifiesto y detiene la secuencia.

Desde la raíz del repositorio en WSL2, usando los activos ya preparados para D2a:

```sh
v="$PWD/experiments/vocoder"
assets="$(dirname "$PWD")"
mkdir -p "$v/results/d2b"
docker run --rm --pull never --network none --read-only --user 1000:1000 \
  --cap-drop ALL --security-opt no-new-privileges --cpus 2 --memory 1536m \
  --tmpfs /tmp:rw,exec,size=900m -v "$assets/go1.27.4.linux-amd64.tar.gz:/go.tgz:ro" \
  -v "$assets/dmrgo-reference:/dmrgo:ro" -v "$v/c5:/c5:ro" -v "$v/d2a:/d2a:ro" \
  -v "$v/d2b:/d2b:ro" -v "$v/evidence/c5:/ref5:ro" -v "$v/evidence/d2a:/ref2a:ro" \
  -v "$v/results/d2b:/results" \
  sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab \
  python3 -B /d2b/run.py
```

La corrida publicada escribió en `evidence/d2b`. Cada fila de `cases.jsonl`
identifica la trama, posición de canal, posición local, región, entrada de
reproducción, salida esperada y observada de ambos motores, estado Go y
primera comprobación fallida si la hubiera. En controles limpios la posición
es null. Secuencia: cuatro controles, luego índices 0–71 para cada trama.
Comandos individuales equivalentes dentro del contenedor:

```sh
/tmp/native "$info49_bin" "$nativeInput72_hex"
/tmp/ref "$info49_padded_hex" "$inputSlot_hex"
```

El primer argumento nativo es la cadena binaria de 49 caracteres de la fila.
El primer argumento Go empaqueta la misma cadena con siete ceros finales.
