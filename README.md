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

## 📊 Comparative Benchmark Results (Simulation Only — Modeled Latency, PPO Not Used)

> [!WARNING]
> **Status:** The results below represent an offline **simulation prototype** evaluating an exhaustive **greedy heuristic** search against simplified baseline rules. Inter-service latency is computed via an analytical model ($0.2\,\text{ms}$ intra-node vs $5.0\,\text{ms}$ cross-node lookup), not measured network packets. The trained PPO model is **not** used to produce these numbers (see `CLAIMS.md`). Live cluster validation under real network emulation is in progress.

Evaluated across dynamic microservice workload shifts in the simulator over identical random seeds:

| Configuration | Resource Variance | Weighted Comm Cost (model units) | Total Cost | Eviction Churn | Notes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Default Scheduler (Simulated)** | 0.8765 | 4639.35 | 27.5791 | 0.0 | Static placement, no rescheduling |
| **Load-Aware-style Descheduler (Simulated Heuristic)** | 0.3769 | 4479.45 | 24.2815 | 32.2 | Unchecked eviction rule (strawman baseline) |
| **KubeAI-style (Oracle Placement, Simulator)** | 0.5380 | 3026.17 | 17.8211 | 0.0 | Perfect-information initial placement, static drift |
| **Proposed Greedy Heuristic (Comm-Aware Sched + Desched)** | **0.3111** | **2757.60** | **15.3435** | **2.4** | Greedy exhaustive search on cost objective |

- In the analytical simulator, communication-aware greedy relocation reduces modeled communication cost compared to static placement.
- These results reflect simulated surrogate objectives; see `CLAIMS.md` for verified vs unverified claims.

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
│   ├── run_dashboard.sh                 # Launch web visual interface
│   └── run_demo.sh                      # One-click verification & demo script
└── docs/
    ├── SCHEDULER.md                     # Arc42 & C4 architecture: Scheduler Extender
    ├── DESCHEDULER.md                   # Arc42 & C4 architecture: PPO Descheduler
    └── synopsis_ANUBHAV_references_fixed.pdf
```

---

## 🚀 Quickstart & How to Run

You can run this project in **two ways**:
1. **Simulation / Benchmark Mode (No Kubernetes cluster needed)**: Trains the RL agent, evaluates the algorithms against baseline schedulers, and runs the interactive visual dashboard.
2. **Live Kubernetes Cluster Mode (Kind cluster)**: Deploys the microservice application into a real multi-node Kind cluster and runs the live Scheduler Extender and continuous RL Descheduler daemon.

---

### What do the scripts do?

| Script | Purpose | What it executes |
| :--- | :--- | :--- |
| **`scripts/run_demo.sh`** | **Automated end-to-end verification** | Runs test suite (`pytest`), ensures/trains the PPO RL model (`train.py`), executes comparative benchmarks (`evaluate.py`), and checks if a live cluster is reachable. *Note: It does not start persistent background servers (extender/dashboard).* |
| **`scripts/run_dashboard.sh`** | **Visual Web Dashboard** | Starts the interactive web UI (`http://localhost:5000`) to visualize cluster nodes, traffic heatmaps, 7D state vector metrics, and step-by-step PPO descheduling actions. |
| **`scripts/setup_cluster.sh`** | **Local Cluster Provisioning** | Creates a 3-worker local `kind` cluster named `rl-scheduler` and deploys the benchmark microservices. |

---

### Step 1: Environment Setup

Ensure you have Python 3.11+ installed. Set up the virtual environment and install dependencies:

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### Mode A: One-Click Quick Verification & Benchmark (Recommended First Step)

To run the unit tests, verify or train the PPO model, and run the comparative benchmark across all 4 configurations in one command:

```bash
./scripts/run_demo.sh
```

> **Is `run_demo.sh` doing all the work?**  
> `run_demo.sh` runs the tests, RL training (if model is missing), and benchmark evaluation automatically. It gives you the full comparative metrics in the terminal. However, it terminates once complete. To launch the interactive dashboard or run against a real cluster, follow Mode B or Mode C below.

---

### Mode B: Launch the Interactive Visual Dashboard

To explore pod placements, inspect the 7D state vector, and step through PPO decisions visually in your web browser:

```bash
./scripts/run_dashboard.sh
```
Then open **http://localhost:5000** in your browser.

*(Alternatively: `source .venv/bin/activate && PYTHONPATH=. python3 src/dashboard/app.py`)*

---

### Mode C: Run with a Live Kubernetes Cluster (Kind)

To run the custom scheduler extender and continuous descheduler against a real multi-node cluster:

1. **Create the Kind cluster and deploy benchmark pods:**
   ```bash
   ./scripts/setup_cluster.sh
   ```
   *(Or manually: `kind create cluster --name rl-scheduler --config manifests/kind/kind-config.yaml` followed by `kubectl apply -f manifests/benchmark/microservice_app.yaml`)*

2. **Start the Scheduler Extender (HTTP Service on port 8888):**
   In terminal 1:
   ```bash
   source .venv/bin/activate
   export PYTHONPATH=.
   python3 src/scheduler/extender_server.py
   ```

3. **Start the Continuous RL Descheduler Controller:**
   In terminal 2:
   ```bash
   source .venv/bin/activate
   export PYTHONPATH=.
   python3 src/descheduler/controller.py
   ```

4. **Monitor cluster activity:**
   ```bash
   kubectl get pods -n benchmark -o wide --watch
   ```

---

## 📚 References

1. Z. Rejiba and J. Chamanara, *"Custom Scheduling in Kubernetes: A Survey on Common Problems and Solution Approaches,"* ACM Computing Surveys, vol. 55, no. 7, 2023.
2. H. Dhanyatha et al., *"KubeAI: An AI-Powered Pod Placement Scheduler for Kubernetes,"* IEEE Access, vol. 14, 2026.
3. A. Marchese and O. Tomarchio, *"Enhancing the Kubernetes Platform with a Load-Aware Orchestration Strategy,"* SN Computer Science, vol. 6, 2025.
4. J. Schulman et al., *"Proximal Policy Optimization Algorithms,"* arXiv:1707.06347, 2017.
