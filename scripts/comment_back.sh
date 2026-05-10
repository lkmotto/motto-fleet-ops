#!/usr/bin/env bash
# Comment on the originating issue with the result.
set -uo pipefail

if [ -z "${ISSUE_REPO:-}" ] || [ -z "${ISSUE_NUMBER:-}" ]; then
  echo "no issue context — skipping comment"
  exit 0
fi

granted_list=$(echo "$GRANTED" | tr ' ' '\n' | sed 's/^/- /' | sed '/^- $/d')
missing_list=$(echo "$MISSING" | tr ' ' '\n' | sed 's/^/- /' | sed '/^- $/d')

body=$(cat <<EOF
## Provisioned

**Target:** \`$TARGET_REPO\`

**Granted as repo secrets:**
${granted_list:-(none)}

**Missing from Doppler motto-core/prd:**
${missing_list:-(none)}

You can re-run your workflow now. Audit log: [provision-log.jsonl](https://github.com/lkmotto/motto-fleet-provisioner/blob/main/audit/provision-log.jsonl)
EOF
)

gh issue comment "$ISSUE_NUMBER" --repo "$ISSUE_REPO" --body "$body" || echo "comment failed (non-fatal)"
