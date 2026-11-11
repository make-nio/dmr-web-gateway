#!/usr/bin/env bash
set -eu -o pipefail
repo=$(git rev-parse --show-toplevel)
spike=sha256:30e7ca9f6a5703eb472244d80106f37d5bfd1f5d7413068065faf89224a7edab
node_image=sha256:363e1587494626837fa7f9a23bdb453d13b0ff3c67c705c2805cfc69c2d2fad7
flags=(--rm --pull never --network none --read-only --cap-drop ALL --security-opt no-new-privileges --user 1000:1000 --cpus 1 --memory 512m)
docker run "${flags[@]}" --entrypoint cat "$node_image" /usr/local/bin/node |
  docker run -i "${flags[@]}" --tmpfs /tmp:exec,rw,size=240m -v "$repo:/repo:ro" "$spike" sh -ec '
    cat >/tmp/node
    chmod 700 /tmp/node
    cd /repo
    export D4_NATIVE=1
    python3 experiments/vocoder/d4/prepare.py
    /tmp/node --version
    /tmp/node node_modules/typescript/bin/tsc --version
    /tmp/node node_modules/typescript/bin/tsc -p experiments/vocoder/d4 --outDir /tmp/js
    cp package.json /tmp/js/package.json
    /tmp/node --test /tmp/js/sessions.test.js
    /tmp/node /tmp/js/timing.js
    head -c 320 /tmp/d4.s16le >/tmp/one.pcm
    for p in simulated opendmr blip25; do
      VOCODER_PROVIDER=$p /tmp/node /tmp/js/bench.js /tmp/one.pcm >/tmp/one.frame
      test "$(wc -c </tmp/one.frame)" -eq 9
      echo "bench CLI $p: 9 bytes"
    done
  '
