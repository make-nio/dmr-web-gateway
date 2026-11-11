#!/usr/bin/env bash
set -euo pipefail
repo=$(git rev-parse --show-toplevel)
out=${1:?supply a new output directory}
mkdir -p "$out"
out=$(realpath "$out")
mode=${2:-duplex}
case "$mode" in duplex|encode|decode) ;; *) exit 2 ;; esac
spike=sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab
node_image=sha256:363e1587494626837fa7f9a23bdb453d13b0ff3c67c705c2805cfc69c2d2fad7
flags=(--pull never --network none --read-only --cap-drop ALL --security-opt no-new-privileges --user 1000:1000 --cpus 1 --memory 512m --memory-swap 512m)
for provider in opendmr blip25; do
  test ! -e "$out/$provider.json"
  idfile=$(mktemp)
  rm "$idfile"
  set +e
  docker run --rm "${flags[@]}" --entrypoint cat "$node_image" /usr/local/bin/node |
    docker run -i --cidfile "$idfile" "${flags[@]}" --tmpfs /tmp:exec,rw,size=240m \
      -v "$repo:/repo:ro" -v "$out:/results" "$spike" sh -ec '
        cat >/tmp/node; chmod 700 /tmp/node
        cd /repo
        python3 experiments/vocoder/d4/prepare.py
        /tmp/node node_modules/typescript/bin/tsc -p experiments/vocoder/d4 --outDir /tmp/js
        cp package.json /tmp/js/package.json
        exec /tmp/node experiments/vocoder/d5/stress.mjs "$1" "$2"
      ' sh "$provider" "$mode"
  rc=$?
  set -e
  id=$(cat "$idfile")
  docker inspect --format '{{json .State}}' "$id" > "$out/$provider-container.json"
  oom=$(docker inspect --format '{{.State.OOMKilled}}' "$id")
  docker rm "$id" >/dev/null
  rm "$idfile"
  if [[ $rc != 0 && $oom != true ]]; then exit "$rc"; fi
done
