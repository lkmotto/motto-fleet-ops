#!/usr/bin/env bash
# Read each requested secret from Doppler motto-core/prd and set it on the target repo.
# Required env: DOPPLER_TOKEN, GH_TOKEN, TARGET_REPO, SECRET_NAMES (space-separated)
set -uo pipefail

granted=()
missing=()

# Pull the entire prd config once (single Doppler call).
doppler_json=$(doppler secrets download --project motto-core --config prd --no-file --format json --token "$DOPPLER_TOKEN" 2>/dev/null) || {
  echo "::error::doppler download failed"
  echo "granted=" >> "$GITHUB_OUTPUT"
  echo "missing=$SECRET_NAMES" >> "$GITHUB_OUTPUT"
  exit 1
}

for name in $SECRET_NAMES; do
  # Doppler JSON shape: {"KEY":{"computed":"value","note":"..."}, ...}
  value=$(printf '%s' "$doppler_json" | python3 -c "
import json, sys
d = json.load(sys.stdin)
v = d.get('$name')
if v is None:
    sys.exit(2)
print(v.get('computed', '') if isinstance(v, dict) else v)
" 2>/dev/null)
  rc=$?
  if [ $rc -ne 0 ] || [ -z "$value" ]; then
    echo "::warning::$name not found in motto-core/prd"
    missing+=("$name")
    continue
  fi
  printf '%s' "$value" | gh secret set "$name" --repo "$TARGET_REPO" --body - 2>&1 | tail -3
  if [ ${PIPESTATUS[1]} -eq 0 ]; then
    granted+=("$name")
  else
    echo "::error::failed to set $name on $TARGET_REPO"
    missing+=("$name")
  fi
done

echo "granted=${granted[*]}" >> "$GITHUB_OUTPUT"
echo "missing=${missing[*]}" >> "$GITHUB_OUTPUT"

if [ ${#granted[@]} -eq 0 ]; then
  exit 1
fi
