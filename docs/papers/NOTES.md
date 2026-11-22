# Reference Papers Analysis and Notes

Project: Communication-aware pod scheduling and rescheduling for Kubernetes  
Owner: Anubhav Kumar (GE-230211124) | Supervisor: Prof. (Dr.) Durgaprasad Gangodkar  

This document records the exact experimental setups, methodologies, equations, and evaluation details verified from the source paper PDFs. Every statement is backed by an exact section or page citation (e.g., "p. 7", "pp. 11–13"). Unverified external assertions — including anything sourced from GitHub READMEs, blog posts, or web searches — are explicitly marked `[WEB, unverified]`.

---

## 1. Marchese & Tomarchio (2025)
**Title:** "Enhancing the Kubernetes Platform with a Load-Aware Orchestration Strategy"  
**Journal:** SN Computer Science (Springer), Vol. 6, Article 224, Feb. 2025  
**File:** `docs/papers/s42979-025-03712-z.pdf`

### What the paper actually did:
- **Core Architecture (pp. 6–7):**
  - **Monitoring Agent:** Written in Java (Quarkus Operator SDK), runs as a Deployment in the control plane. Triggered by `Cluster` and `AppGroup` Custom Resources.
  - **Prometheus Scrapes:** Scrapes node exporters and CAdvisor DaemonSets every 10 seconds.
  - **Crucial Clarification on Telemetry (pp. 7–8):** Prometheus measures **individual resource usage** of nodes and pods (CPU in millicores, Memory in MB, Network bandwidth in MB/s, Disk bandwidth in MB/s via Tables 1 & 2). It does **NOT** measure pairwise inter-pod request counts or communication matrices!
- **Scheduling Architecture (pp. 7–8):**
  - Implements a custom **Go scoring plugin** (`LoadAware`) built into the native **Kubernetes Scheduling Framework** (not an HTTP scheduler extender).
  - Evaluates candidate nodes using Equations (1)–(6):
    $$\text{score}(p, n_i) = \left(1 - \text{std}(cpu_{rn}, mem_{rn}, net_{rn}, disk_{rn})\right) \times 100$$
    where $cpu_{rn}, mem_{rn}, net_{rn}, disk_{rn}$ are the projected usage ratios for **CPU, memory, network bandwidth, and disk bandwidth** relative to node allocatable capacities.
- **Descheduling Architecture (pp. 8–9):**
  - Implemented as a custom evictor plugin in the Go-based Kubernetes descheduler framework, running as a CronJob.
  - **Safety Rule (p. 8):** Evicts at maximum 1 Pod per iteration, while ensuring that **at least one replica remains active** (`replicas >= 1` maintained) for each Deployment.
  - **Eviction Decision (p. 9, Eqs. 7–9):**
    $$dscore(p) = \max_{n_j \in cns}(score(p, n_j)) - score(p, n_i)$$
    Evicts the pod with $\max(dscore(p))$ provided $dscore(p) > 0$. Pods are **only** evicted when there is a strictly positive improvement.
- **Related Work (pp. 11–13):**
  - Survey of related schedulers; reference list on pp. 14–15.
- **Workload & Benchmark (pp. 9–10):**
  - Generates microservice topologies using **μBench** (Ref [13], Detti et al., IEEE TPDS 2023).
  - Uses the μBench **Loader function** to generate configurable CPU ($\pi$ decimals), memory, network bandwidth (bytes/req), and disk I/O.
- **Cluster & Load Testbed (p. 10):**
  - 1 master + 6 worker nodes on **RKE2** (Proxmox VMs, each 2 vCPU, 8GB RAM).
  - Load driven by **k6** sending HTTP requests to the API gateway.
  - 5 trials per experiment, 20 minutes per trial. Measures client-side **p95 response time** across concurrent virtual users.
- **Integration Note (p. 13):**
  - Marchese & Tomarchio explicitly acknowledge: "The proposed framework complements network-aware schedulers [26][27]; both can be integrated." (p. 13)
- **Limitation / Research Gap identified in our project:**
  - Marchese & Tomarchio's framework is **communication-blind**. It monitors network bandwidth consumption (MB/s), but has zero visibility into pairwise inter-service call graphs, request counts, or cross-node RTT dependencies.

---

## 2. KubeAI — Dhanyatha et al. (2026)
**Title:** "KubeAI-An AI-Powered Pod Placement Scheduler for Kubernetes"  
**Journal:** IEEE Access, Vol. 14, pp. 80268–80279, May 2026  
**File:** `docs/papers/KubeAI-An_AI-Powered_Pod_Placement_Scheduler_for_Kubernetes.pdf`

### What the paper actually did:
- **Core Architecture (pp. 80270–80273):**
  - Implements a Flask-based **Kubernetes Scheduler Extender** exposing endpoints (p. 80273):
    - `POST /schedule` — Handles scheduling requests from Kubernetes.
    - `GET /metrics` — Retrieves real-time cluster metrics.
    - `POST /update-policy` — Updates the PPO policy dynamically.
- **State Vector & Telemetry Formulation (p. 80271, Eq. 1):**
  - The 7-dimensional state vector $s$ evaluated by KubeAI is:
    $$s = [cpu\_eff, mem\_eff, node\_cpu, node\_mem, disk\_io, net\_lat, node\_temp]^T$$
  - **Crucial Clarification on State Features:** The 7-dimensional state vector contains **no pairwise communication features**. `cpu_eff` and `mem_eff` reflect pod resource allocation efficiency; `node_cpu`, `node_mem`, `disk_io` reflect the candidate node's operational state. `net_lat` is a **node-level latency metric** (the paper does not specify measurement method; "round-trip ping" is not stated in the PDF) `[p. 80271]`. `node_temp` is the node temperature sensor reading.
- **Reward Function (p. 80271, Eqs. 2–9):**
  - $R = 2 \cdot r_{cpu} + 2 \cdot r_{mem} + p_{overload} + p_{balance} + p_{disk} + p_{net} + p_{temp}$.
- **Evaluation & Metrics (pp. 80274–80275):**
  - Tested on a Kind cluster. Evaluated Pod Scheduling Latency (PSL), Resource Utilization Efficiency (RUE), and Failure Rate Reduction (FRR).
  - **Synthetic workload (p. 80274):** KubeAI generated 15,000 scheduling events using a custom event simulator — no named benchmark (not uBench, not k6). `[p. 80274]`
- **Limitation / Research Gap identified in our project:**
  - KubeAI is strictly an **initial placement scheduler**. It has no continuous descheduler to correct placement when workloads drift over time.

---

## 3. Detti, Funari, & Petrucci (2023) — μBench
**Title:** "μBench: An Open-Source Factory of Benchmark Microservice Applications"  
**Journal:** IEEE Transactions on Parallel and Distributed Systems (TPDS), Vol. 34, No. 3, March 2023  
**Citation:** Ref [10] in our synopsis / Ref [13] in Marchese & Tomarchio.

### Key Capabilities:
- Generates reproducible, synthetic, multi-tier microservice applications configured via JSON/YAML. `[WEB, unverified: μBench GitHub README]`
- Emits HTTP/gRPC traffic with configurable call chains, CPU calculations, memory usage, and payload sizes. `[WEB, unverified: μBench GitHub README]`
- Natively supports Prometheus metric scraping and Jaeger tracing `[WEB, unverified: μBench GitHub docs]`.

---

## 4. Rejiba & Chamanara (2023)
**Title:** "Custom Scheduling in Kubernetes: A Survey on Common Problems and Solution Approaches"  
**Journal:** ACM Computing Surveys, Vol. 55, No. 7, 2023  
**Citation:** Ref [1] in our synopsis.

### Key Survey Insights:
- Analyzes custom scheduler architectures: Custom Schedulers, Scheduler Extenders, and Scheduling Framework Plugins.
- Note on Scheduler Extenders: Extenders communicate with `kube-scheduler` via HTTP JSON webhooks, which introduces serialization and network latency overhead compared to in-tree Go plugins `[WEB, unverified: no PDF available; claim not verified from source text]`. *(Note: The previously stated "10–30ms" claim was an unverified web estimate and has been removed.)*

---

## 5. Must-Read References Before Making Novelty Claims

Before claiming novelty on communication-aware or network-aware Kubernetes scheduling/descheduling, the following papers from Marchese & Tomarchio (2025) Section "Related Work" (p. 15) must be read and analyzed:

1. **[19] NetMARKS (Wojciechowski et al., IEEE INFOCOM 2021):**
   - *Title:* "NetMARKS: Network Metrics-AwaRe Kubernetes Scheduler Powered by Service Mesh"
   - Uses dynamic network metrics collected with Istio Service Mesh for service function chaining placement.
2. **[24] Diktyo (Santos et al., IEEE TNSM 2023):**
   - *Title:* "Diktyo: Network-Aware Scheduling in Container-Based Clouds"
   - Proposes network-aware scheduling plugins for Kubernetes to determine low-latency deployment schemes.
3. **[26] Marchese & Tomarchio (IEEE CCGrid 2022):**
   - *Title:* "Network-Aware Container Placement in Cloud-Edge Kubernetes Clusters"
   - Reduces network distance between communicating microservices.
4. **[27] Marchese & Tomarchio (ICSOC 2022):**
   - *Title:* "Extending the Kubernetes Platform with Network-Aware Scheduling Capabilities"
   - Earlier network-aware scheduling framework from the authors.
