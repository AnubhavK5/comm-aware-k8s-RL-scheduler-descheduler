# Communication-Aware Adaptive Pod Scheduling and Rescheduling for Kubernetes Using Reinforcement Learning

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Kubernetes v1.37+](https://img.shields.io/badge/kubernetes-v1.37+-326ce5.svg)](https://kubernetes.io/)
[![RL Engine](https://img.shields.io/badge/RL-Stable--Baselines3%20%7C%20PPO-green.svg)](https://stable-baselines3.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📌 Overview

This project implements the architecture proposed in the research synopsis:
**"Communication-Aware Adaptive Pod Scheduling and Rescheduling for Kubernetes Using Reinforcement Learning"**  
*Project Team ID: MP2026CSE197 | Department of Computer Science & Engineering, Graphic Era Deemed to be University*

### The Identified Research Gap
1. **Default Kubernetes Scheduler**: Uses static developer-declared resource requests and schedules a pod only **once**. It does not re-evaluate placement as workloads evolve, nor does it account for inter-service network traffic.
2. **KubeAI (Dhanyatha et al., 2026)**: Employs Proximal Policy Optimization (PPO) for **initial** pod placement with communication awareness, but cannot reschedule pods once placed.
3. **Load-Aware Descheduler (Marchese & Tomarchio, 2025)**: Periodically reschedules running pods based on real-time node telemetry, but uses a **fixed non-adaptive formula** with zero visibility into inter-pod network communications.
4. **Our Solution**: Unifies both paradigms into an end-to-end framework:
   - A **Scheduler Extender** (`src/scheduler/`) for communication-aware initial placement.
   - A **Continuous RL Descheduler** (`src/descheduler/`) driven by PPO to continuously evict and relocate pods that drift into high-latency cross-node configurations, while preserving replica availability.

---

## 🏗️ Architecture

```
                                    +------------------------------------------+
                                    |        Kubernetes Control Plane          |
                                    |                                          |
                                    |   +-----------------+                    |
                                    |   |  kube-scheduler |                    |
                                    |   +--------+--------+                    |
                                    |            | (HTTP /prioritize)          |
                                    +------------|-----------------------------+
                                                 v
+-------------------------------+   +------------+------------+   +-------------------------------+
|  Telemetry Aggregator         |   | Scheduler Extender      |   | PPO RL Descheduler            |
|  - Metrics Server (CPU/Mem)   +-->+ - Flask HTTP Service    |   | - Periodic evaluation loop    |
|  - Node resource utilization  |   | - 7D State Scorer       |   | - Safety & replica guards     |
|  - Inter-pod Comm Graph       |   | - Action-Value Ranking  |   | - Eviction subresource API    |
+---------------+---------------+   +-------------------------+   +---------------+---------------+
                |                                                                 |
                +-----------------------------------------------------------------+
                                                 |
                                                 v
                               +-----------------+-----------------+
                               |  Kind Kubernetes Worker Nodes     |
                               |  - node 1: frontend, orders       |
                               |  - node 2: cart, catalog          |
                               |  - node 3: payment (co-located)   |
                               +-----------------------------------+
```

---

## 📊 Comparative Benchmark Results

Evaluated across dynamic microservice workload shifts over identical random seeds:

| Configuration | Resource Variance | Comm Latency (ms) | Total Cost | Eviction Churn |
| :--- | :---: | :---: | :---: | :---: |
| **Default Scheduler** | 0.8765 | 4639.35 | 27.5791 | 0.0 |
| **Load-Aware Descheduler (Heuristic)** [5] | 0.3769 | 4479.45 | 24.2815 | 32.2 (flapping) |
| **KubeAI (RL Placement Only)** [2] | 0.5380 | 3026.17 | 17.8211 | 0.0 (drifted) |
| **Proposed (Comm-Aware Sched + Desched)** | **0.3111** | **2757.60** | **15.3435** | **2.4 (stable)** |

- **40.5% lower inter-service communication latency** than default scheduler.
- **64.5% reduction in node resource variance** across worker nodes.
- **92.5% fewer evictions** than heuristic descheduling, eliminating eviction flapping.

---

## 📁 Repository Structure

```
.
├── manifests/
│   └── benchmark/
│       └── microservice_app.yaml        # Multi-tier benchmark deployment
├── src/
│   ├── common/
│   │   ├── config.py                    # Cluster constants & hyperparameters
│   │   └── k8s_client.py                # Kubernetes API client & eviction helpers
│   ├── telemetry/
│   │   ├── aggregator.py                # 7D state builder & metrics merger
│   │   └── comm_graph.py                # Inter-pod communication affinity tracker
│   ├── scheduler/
│   │   ├── extender_server.py           # HTTP Scheduler Extender (/filter, /prioritize)
│   │   └── scorer.py                    # State vector node scorer
│   ├── descheduler/
│   │   ├── controller.py                # Continuous descheduling loop
│   │   └── safety.py                    # Pod disruption & replica guards
│   └── rl/
│       ├── env/
│       │   └── cluster_env.py           # Gymnasium Kubernetes environment
│       ├── train.py                     # PPO training pipeline
│       └── evaluate.py                  # Comparative benchmark script
├── tests/
│   └── test_scheduler_descheduler.py    # Pytest unit & integration test suite
├── scripts/
│   └── run_demo.sh                      # One-click verification & demo script
└── docs/
    └── synopsis_ANUBHAV_references_fixed.pdf
```

---

## 🚀 Quickstart

### 1. Prerequisites
- Linux with Python 3.11+ (Python 3.14 supported)
- Docker & Kind (`kind`)
- `kubectl`

### 2. Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # or torch, stable-baselines3, gymnasium, kubernetes, flask
```

### 3. Run Unit Tests
```bash
source .venv/bin/activate
PYTHONPATH=. pytest tests/
```

### 4. Train the PPO Descheduler
```bash
source .venv/bin/activate
PYTHONPATH=. python3 src/rl/train.py
```

### 5. Run the Comparative Benchmark
```bash
source .venv/bin/activate
PYTHONPATH=. python3 src/rl/evaluate.py
```

### 6. Run Against Live Kubernetes Cluster
```bash
# Deploy benchmark microservices
kubectl apply -f manifests/benchmark/microservice_app.yaml

# Start Scheduler Extender
PYTHONPATH=. python3 src/scheduler/extender_server.py &

# Run Descheduler Controller
PYTHONPATH=. python3 src/descheduler/controller.py
```

---

## 📚 References

1. Z. Rejiba and J. Chamanara, *"Custom Scheduling in Kubernetes: A Survey on Common Problems and Solution Approaches,"* ACM Computing Surveys, vol. 55, no. 7, 2023.
2. H. Dhanyatha et al., *"KubeAI: An AI-Powered Pod Placement Scheduler for Kubernetes,"* IEEE Access, vol. 14, 2026.
3. A. Marchese and O. Tomarchio, *"Enhancing the Kubernetes Platform with a Load-Aware Orchestration Strategy,"* SN Computer Science, vol. 6, 2025.
4. J. Schulman et al., *"Proximal Policy Optimization Algorithms,"* arXiv:1707.06347, 2017.
