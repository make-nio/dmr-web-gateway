#!/usr/bin/env bash
# Banco D5: estrés multicanal con pacing de 20 ms. Mismo entorno aislado que d4/validate.sh
# (sin red, raíz de solo lectura, usuario 1000, CPU y memoria acotadas).
#
#   bash experiments/vocoder/d5-independiente/run.sh <directorio-de-resultados> [escalones] [segundos]
#
# Variables: PROVIDERS="opendmr blip25"  MODES="rx tx duplex"  CPUS=1  MEMORY=512m  REPEAT_STEP="10:2"
# El directorio de resultados se crea (modo 777 para el usuario 1000 del contenedor) y recibe un JSON por medición.
set -eu -o pipefail
out=${1:?directorio de resultados}
steps=${2:-"1 2 5 10 15 20 25"}
seconds=${3:-20}
providers=${PROVIDERS:-"opendmr blip25"}
modes=${MODES:-"rx tx duplex"}
cpus=${CPUS:-1}
memory=${MEMORY:-512m}
limits=${LIMITS:-'{}'}
repeat_step=${REPEAT_STEP:-}           # p. ej. "10:2" = repetir 2 veces más el escalón de 10 canales
repo=$(git rev-parse --show-toplevel)
spike=sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab
node_image=sha256:363e1587494626837fa7f9a23bdb453d13b0ff3c67c705c2805cfc69c2d2fad7
mkdir -p "$out"; chmod 777 "$out"
flags=(--rm --pull never --network none --read-only --cap-drop ALL --security-opt no-new-privileges --user 1000:1000 --cpus "$cpus" --memory "$memory")
docker run "${flags[@]}" --entrypoint cat "$node_image" /usr/local/bin/node |
  docker run -i "${flags[@]}" --tmpfs /tmp:exec,rw,size=240m -v "$repo:/repo:ro" -v "$out:/out" \
    -e STEPS="$steps" -e SECONDS_PER_STEP="$seconds" -e PROVIDERS="$providers" -e MODES="$modes" -e REPEAT_STEP="$repeat_step" \
    -e LIMITS="${LIMITS:-{\}}" "$spike" sh -ec '
    cat >/tmp/node
    chmod 700 /tmp/node
    cd /repo
    export D4_NATIVE=1
    python3 experiments/vocoder/d4/prepare.py
    /tmp/node --version
    /tmp/node node_modules/typescript/bin/tsc -p experiments/vocoder/d5-independiente --outDir /tmp/js
    cp package.json /tmp/js/package.json
    /tmp/node --test /tmp/js/d5-independiente/d5.test.js
    echo "cgroup v2: $(test -r /sys/fs/cgroup/cpu.stat && echo si || echo no)"
    run() {  # proveedor modo canales sufijo
      f=/out/$1-$2-$3ch$4.json
      /tmp/node /tmp/js/d5-independiente/bench.js --provider "$1" --mode "$2" --channels "$3" --seconds "$SECONDS_PER_STEP" --limits "$LIMITS" --out "$f" || echo "  (rc=$?: $f)"
      echo "listo $f"
    }
    for p in $PROVIDERS; do for m in $MODES; do for n in $STEPS; do
      run "$p" "$m" "$n" ""
      if [ -n "$REPEAT_STEP" ] && [ "${REPEAT_STEP%%:*}" = "$n" ]; then
        for r in $(seq 1 "${REPEAT_STEP##*:}"); do run "$p" "$m" "$n" "-rep$r"; done
      fi
    done; done; done
  '
