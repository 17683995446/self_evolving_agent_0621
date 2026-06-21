#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"

echo "[START] Starting Self-Evolving Agent..."
cd "${PROJECT_ROOT}"

export PYTHONPATH="${PROJECT_ROOT}"

nohup python -m a.left.src.main > agent.log 2>&1 &
echo $! > agent.pid

echo "[START] Agent started with PID $(cat agent.pid)"
