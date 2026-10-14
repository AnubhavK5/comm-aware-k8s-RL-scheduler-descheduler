#!/usr/bin/env bash
set -e

echo "=== Communication-Aware RL Scheduler & Descheduler Demo ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

if [ ! -d ".venv" ]; then
    echo "Virtualenv not found. Please set up .venv first."
    exit 1
fi

source .venv/bin/activate
export PYTHONPATH=.

echo "[1/4] Running Unit Tests..."
pytest tests/

echo "[2/4] Verifying Trained PPO Model..."
if [ ! -f "src/rl/models/ppo_descheduler.zip" ]; then
    echo "Training PPO model..."
    python3 src/rl/train.py
else
    echo "Found trained model at src/rl/models/ppo_descheduler.zip"
fi

echo "[3/4] Running Comparative Benchmark across 4 Configurations..."
python3 src/rl/evaluate.py

echo "[4/4] Verifying Live Kubernetes Cluster Status..."
kubectl get nodes -o wide || echo "No live cluster reachable."
kubectl get pods -n benchmark -o wide || echo "No benchmark pods found."

echo "=== Demo Run Complete ==="
