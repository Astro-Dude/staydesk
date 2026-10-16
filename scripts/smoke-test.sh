#!/usr/bin/env bash
# Hit the app through the Ingress and check the key endpoints.
# Usage: ./scripts/smoke-test.sh [base-url]     (default http://staydesk.localhost)
set -euo pipefail
BASE="${1:-http://staydesk.localhost}"
fail=0

check() {
  local path=$1 expect=$2 code
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$BASE$path")
  if [[ "$code" == "$expect" ]]; then
    printf 'PASS %s %s\n' "$code" "$path"
  else
    printf 'FAIL %s %s (expected %s)\n' "$code" "$path" "$expect"; fail=1
  fi
}

check /                     200   # React UI via frontend Service
check /api/meta             200   # FastAPI via backend Service
check /api/rooms            200
check /api/reservations     200
check /api/dashboard/stats  200
check /api/rooms/999999     404
check /docs                 200   # Swagger UI
check /openapi.json         200
exit $fail
