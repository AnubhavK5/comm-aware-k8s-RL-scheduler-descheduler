# Reference Papers Analysis and Notes

Project: Communication-aware pod scheduling and rescheduling for Kubernetes  
Owner: Anubhav Kumar (GE-230211124) | Supervisor: Prof. (Dr.) Durgaprasad Gangodkar  

This document records the exact experimental setups, methodologies, equations, and evaluation details from the core reference papers.

---

## 1. Marchese & Tomarchio (2025)
**Title:** "Enhancing the Kubernetes Platform with a Load-Aware Orchestration Strategy"  
**Journal:** SN Computer Science (Springer), Vol. 6, Article 224, Feb. 2025  
**File:** `docs/papers/s42979-025-03712-z.pdf`

### What the paper actually did:
- **Core Architecture:** Combines a custom monitoring agent (scraping Prometheus/CAdvisor/node_exporter every 10s), a Kubernetes Scheduler Extender, and a custom Descheduler.
- **Descheduling Algorithm:** Evaluates running pods periodically. Computes node scores $S(n)$ using Equations 7–9 based strictly on real-time CPU and Memory utilization.
- **Safety Guards:**
  - Enforces minimum 2 replicas per deployment so availability is preserved during eviction.
  - Pods are evicted one at a time and only when the relocation yields a strictly positive score improvement.
- **Workload & Benchmark:**
  - Generates microservice topologies using **μBench** (Reference [13] in their paper: Detti et al., IEEE TPDS 2023).
  - Uses the μBench **Loader function** to generate configurable CPU (decimals of $\pi$), memory, disk, and network payloads across $N_l$ layered microservices (Section "Performance Evaluation", pp. 9–10).
- **Cluster Environment:**
  - 1 master + 6 worker nodes on **RKE2 (Rancher Kubernetes Engine 2)** running on Proxmox VMs (each 2 vCPU, 8GB RAM).
- **Load Generation & Metrics:**
  - Real load driven by **k6** sending HTTP requests to the API gateway.
  - 5 trials per experiment, 20 minutes per trial, measuring empirical **client-side 95th-percentile (p95) response time** across concurrent virtual users (VUs).
  - Reported 13% to 53% reduction in p95 response time compared to the default Kubernetes scheduler.
- **Limitation / Research Gap identified in our project:**
  - Marchese & Tomarchio's descheduler is **completely communication-blind**. It only balances CPU and memory, ignoring inter-service network traffic and cross-node network latency bottlenecks.

---

## 2. KubeAI — Dhanyatha et al. (2026)
**Title:** "KubeAI-An AI-Powered Pod Placement Scheduler for Kubernetes"  
**Journal:** IEEE Access, Vol. 14, pp. 80268–80279, May 2026  
**File:** `docs/papers/KubeAI-An_AI-Powered_Pod_Placement_Scheduler_for_Kubernetes.pdf`

### What the paper actually did:
- **Core Architecture:** A Flask-based Kubernetes Scheduler Extender implementing `/filter` and `/prioritize` driven by a PPO reinforcement learning model for **initial** pod placement.
- **State Vector & Telemetry:**
  - Evaluates candidate nodes using a 7-dimensional state vector:
    $$s = [cpu\_eff, mem\_eff, node\_cpu, node\_mem, disk\_io, net\_lat, node\_temp]$$
  - Gathers infrastructure metrics via Kubernetes Metrics Server and inter-pod call frequencies via **OpenTelemetry**.
- **Model Training:**
  - PPO agent trained for 15,000 steps using Stable-Baselines3 in an offline simulation environment.
- **Evaluation & Metrics:**
  - Tested on a Kind (Kubernetes-in-Docker) cluster.
  - Primary metrics: Pod Scheduling Latency (PSL - Equation 12), Resource Utilization Efficiency (RUE - Equation 13), and Failure Rate Reduction (FRR - Equation 14).
  - Evaluated on synthetic scheduled events; did **not** use k6 or μBench.
- **Limitation / Research Gap identified in our project:**
  - KubeAI schedules pods **only once at creation time**. It has no descheduling capability; when inter-service traffic drifts or nodes experience variance after initial placement, KubeAI cannot relocate running pods.

---

## 3. Detti, Funari, & Petrucci (2023) — μBench
**Title:** "μBench: An Open-Source Factory of Benchmark Microservice Applications"  
**Journal:** IEEE Transactions on Parallel and Distributed Systems (TPDS), Vol. 34, No. 3, March 2023  
**Citation:** Reference [10] in our synopsis / Reference [13] in Marchese & Tomarchio.

### Key Capabilities:
- Generates reproducible, synthetic, multi-tier microservice applications configured via JSON/YAML files.
- Provides standard container images with configurable workload primitives (CPU calculation, memory buffer allocations, inter-service HTTP forwarding chains, network payload sizing).
- Emits application-level execution traces and integrates cleanly with external HTTP load drivers (k6 / Locust).

---

## 4. Rejiba & Chamanara (2023)
**Title:** "Custom Scheduling in Kubernetes: A Survey on Common Problems and Solution Approaches"  
**Journal:** ACM Computing Surveys, Vol. 55, No. 7, 2023  
**Citation:** Reference [1] in our synopsis.

### Key Survey Insights:
- Analyzes custom scheduler architectures: Custom Scheduler, Scheduler Extender, and Scheduling Framework Plugins.
- Identifies that Scheduler Extenders (HTTP webhooks for `/filter` and `/prioritize`) provide the cleanest out-of-tree deployment without recompiling `kube-scheduler` binaries, but incur network serialization overhead (~10–30ms per scheduling event).
