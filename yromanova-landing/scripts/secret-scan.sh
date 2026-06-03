#!/usr/bin/env bash
# Security gate (PRD §7): GetCourse secrets / server-only proxy must NOT be in
# the client bundle. Run after `next build`. Exit 1 on any leak.
set -euo pipefail

DIR="${1:-.next/static}"

if [ ! -d "$DIR" ]; then
  echo "[secret-scan] FAIL: '$DIR' not found — run 'npm run build' first." >&2
  exit 1
fi

# Patterns that must never appear in client-shipped JS:
#  - the GetCourse import-API endpoint (proves submitLead leaked client-side)
#  - server-only secret env var names
#  - the secret value being inlined as action=add&key=
PATTERNS=(
  'getcourse\.ru/pl/api'
  'GC_API_KEY'
  'GC_ACCOUNT'
  'action=add&key='
)

leaked=0
for pat in "${PATTERNS[@]}"; do
  if grep -rIlE "$pat" "$DIR" 2>/dev/null; then
    echo "[secret-scan] LEAK: pattern '$pat' found in client bundle ^" >&2
    leaked=1
  fi
done

if [ "$leaked" -ne 0 ]; then
  echo "[secret-scan] FAIL — GetCourse secrets/proxy leaked to client. Block release." >&2
  exit 1
fi

echo "[secret-scan] PASS — no GetCourse secrets in $DIR"
