#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"
PID_FILE="${PROJECT_ROOT}/agent.pid"

if [ -f "${PID_FILE}" ]; then
    PID=$(cat "${PID_FILE}")
    echo "[STOP] Stopping agent (PID: ${PID})..."
    kill "${PID}" || true
    rm -f "${PID_FILE}"
    echo "[STOP] Agent stopped."
else
    echo "[STOP] No PID file found. Agent may not be running."
fi
