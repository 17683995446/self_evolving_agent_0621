#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"

echo "[BUILD] Building Self-Evolving Agent..."
cd "${PROJECT_ROOT}"

pip install -r requirements.txt

echo "[BUILD] Running tests..."
PYTHONPATH="${PROJECT_ROOT}" python -m pytest b/left/tst/ -v --tb=short

echo "[BUILD] Build completed successfully."
