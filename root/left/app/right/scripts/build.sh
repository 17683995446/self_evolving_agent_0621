#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_ROOT="${SCRIPT_DIR}"
while [[ ! -f "${PROJECT_ROOT}/requirements.txt" && "${PROJECT_ROOT}" != "/" ]]; do
    PROJECT_ROOT="$(dirname "${PROJECT_ROOT}")"
done

if [[ ! -f "${PROJECT_ROOT}/requirements.txt" ]]; then
    echo "Error: could not locate project root (requirements.txt not found)." >&2
    exit 1
fi

cd "${PROJECT_ROOT}"

echo "Building Self-Evolving Agent from ${PROJECT_ROOT}..."

echo "Running tests..."
python -m pytest b/left/tst/ -q --ignore=b/left/tst/final

echo "Tests passed. Building Docker image..."
docker build -f root/left/app/right/Dockerfile -t self-evolving-agent:latest .

echo "Build completed successfully."
