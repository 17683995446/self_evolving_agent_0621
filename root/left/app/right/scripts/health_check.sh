#!/bin/bash
set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"

echo "Health check against ${BASE_URL}"
echo

for endpoint in /health /metrics /state; do
    url="${BASE_URL}${endpoint}"
    echo "=== ${endpoint} ==="
    if response="$(curl -fsS "${url}" 2>&1)"; then
        echo "${response}"
    else
        echo "ERROR: ${response}"
    fi
    echo
done
