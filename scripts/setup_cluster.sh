#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Starting Kind Cluster Setup for RL Scheduler & Descheduler"
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

# 1. Verify Docker connectivity
if ! docker info >/dev/null 2>&1; then
    echo "[!] Docker daemon cannot be accessed without sudo or is not running."
    echo "    Fix permission by running:"
    echo "      sudo usermod -aG docker \$USER && newgrp docker"
    exit 1
fi

echo "[1/4] Docker is running and accessible."

# 2. Check if cluster already exists
if kind get clusters 2>/dev/null | grep -q "^rl-scheduler$"; then
    echo "[2/4] Kind cluster 'rl-scheduler' already exists."
else
    echo "[2/4] Creating 3-worker Kind cluster 'rl-scheduler'..."
    kind create cluster --name rl-scheduler --config manifests/kind/kind-config.yaml
fi

# 3. Wait for all nodes to be Ready
echo "[3/4] Waiting for all nodes to report Ready status..."
kubectl wait --for=condition=Ready nodes --all --timeout=120s
kubectl get nodes -o wide

# 4. Deploy benchmark microservices
echo "[4/4] Deploying benchmark microservices..."
kubectl apply -f manifests/benchmark/microservice_app.yaml

echo "Waiting for benchmark pods to become ready..."
kubectl wait --namespace benchmark --for=condition=Ready pods --all --timeout=180s || true

echo ""
echo "=========================================================="
echo " Cluster setup completed successfully!"
echo "=========================================================="
kubectl get pods,svc -n benchmark -o wide
