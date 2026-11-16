#!/usr/bin/env bash
# Tests .gitleaks.toml. Requires gitleaks on PATH. Tested with gitleaks 8.16.0.
# Run from anywhere:  bash scripts/test-gitleaks-config.sh
#
# At run time it creates, in a temporary directory, 3 FAKE secrets that must be detected, 3 more
# that try to hide behind an exclusion (must also be detected) and 2 harmless lines that must NOT be
# detected, and checks all of them. The fake values are generated
# randomly here and never written inside the repository, so they do not trigger scanners on it.
set -u
TESTED_VERSION="8.16.0"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$RAIZ/.gitleaks.toml"

command -v gitleaks >/dev/null || { echo "gitleaks not found on PATH" >&2; exit 2; }
version="$(gitleaks version 2>/dev/null | head -1)"
# Some builds print no number ("version is set by build process"); then the version cannot be checked.
case "$version" in
  "$TESTED_VERSION"|"v$TESTED_VERSION") ;;
  [0-9]*|v[0-9]*) echo "WARNING: tested with gitleaks $TESTED_VERSION, found $version. Review the result and update TESTED_VERSION here and in .gitleaks.toml." >&2 ;;
  *) echo "WARNING: this gitleaks build does not report its version ('$version'); the config was tested with $TESTED_VERSION." >&2 ;;
esac

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
alnum() { LC_ALL=C tr -dc "$1" </dev/urandom | head -c "$2"; }
# Password-like value with #, $ and ! inside. The default gitleaks rules do not flag such values in a
# NAME=value line, so the cases using it exercise the env-secret-assignment rule itself.
pw() { printf '%s#%s$%s!%s' "$(alnum 'A-Za-z0-9' 4)" "$(alnum 'A-Za-z0-9' 4)" "$(alnum 'A-Za-z0-9' 4)" "$(alnum 'A-Za-z0-9' 4)"; }

# 3 fakes with real-looking shapes
printf 'aws_access_key_id = AKIA%s\n' "$(alnum 'A-Z2-7' 16)" > "$tmp/cloud.cfg"      # cloud access key
printf 'GITHUB_TOKEN_VALUE=ghp_%s\n' "$(alnum 'A-Za-z0-9' 36)" > "$tmp/token.txt"    # GitHub-style token
printf 'DB_USER=app\nDB_PASSWORD=%s\n' "$(pw)" > "$tmp/.env"        # .env password

# 2 negatives that must stay silent (the whole point of the exclusions)
printf 'DMR_HOTSPOT_PASSWORD_FILE=/run/secrets/dmr_password\n' > "$tmp/neg-file.env"
printf 'services:\n  gateway:\n    secrets: [dmr_password]\n' > "$tmp/neg-compose.yaml"

# 3 more that must be detected: each tries to hide a real value behind an exclusion
printf 'secrets: %s\n' "$(pw)" > "$tmp/pos-secrets-value.yaml"                      # `secrets:` with a value
printf 'DB_PASSWORD=%s # e.g.: example\n' "$(pw)" > "$tmp/pos-comment-example.env"   # trailing placeholder word
printf 'API_TOKEN=%s # see DB_PASSWORD_FILE=/run/secrets/x\n' "$(pw)" > "$tmp/pos-comment-file.env"  # trailing _FILE text

report="$tmp/report.json"
gitleaks detect --source "$tmp" --no-git --no-banner --redact -c "$CONFIG" \
  --report-format json --report-path "$report" >/dev/null 2>&1
rc=$?
[ -s "$report" ] || { echo "FAIL: no report (gitleaks exit $rc)" >&2; exit 1; }

# file names flagged, one per line
flagged="$(grep -o '"File": *"[^"]*"' "$report" | sed 's/.*\/\([^/"]*\)"$/\1/' | sort -u)"
fail=0
for f in cloud.cfg token.txt .env pos-secrets-value.yaml pos-comment-example.env pos-comment-file.env; do
  echo "$flagged" | grep -qx -- "$f" && echo "ok   detected: $f" || { echo "FAIL not detected: $f"; fail=1; }
done
for f in neg-file.env neg-compose.yaml; do
  echo "$flagged" | grep -qx -- "$f" && { echo "FAIL false positive: $f"; fail=1; } || echo "ok   silent:   $f"
done
[ $fail -eq 0 ] && echo "PASS (gitleaks $version)" || echo "FAILED (gitleaks $version)"
exit $fail
