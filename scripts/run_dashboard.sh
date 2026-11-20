#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

if [ ! -d ".venv" ]; then
    echo "Virtualenv not found. Please set up .venv first."
    exit 1
fi

source .venv/bin/activate
export PYTHONPATH=.
PORT="${1:-5000}"

echo "=============================================================="
echo " Starting K8s RL Scheduler & Descheduler Visual Dashboard"
echo " Open in your browser: http://localhost:${PORT}"
echo "=============================================================="

python3 src/dashboard/app.py
