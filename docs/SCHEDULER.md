# Arc42 Architecture & Implementation: Communication-Aware Scheduler Extender

This document provides a comprehensive architecture and implementation specification for the **Communication-Aware Scheduler Extender** (`src/scheduler/`), structured according to the **Arc42 architectural template** and visualised using the **C4 model** (Context, Containers, Components) via Mermaid diagrams.

---

## 1. Introduction and Goals

### 1.1 Purpose
The default Kubernetes scheduler (`kube-scheduler`) evaluates resource requests statically at pod creation time without considering inter-service communication patterns or dynamic network latencies. The Scheduler Extender augments `kube-scheduler` by intercepting initial pod scheduling decisions, computing a 7-dimensional infrastructure and network affinity state vector, and ranking candidate nodes to minimize inter-node communication bottlenecks.

### 1.2 Quality Goals
1. **Low Scheduling Latency**: Complete node filtering and scoring within < 50ms per pod evaluation.
2. **Communication Affinity Optimization**: Colocate frequently communicating pods on the same worker node or within the same low-latency zone.
3. **Cluster Resource Balance**: Prevent hotspots by balancing CPU and Memory utilization alongside communication affinity.
4. **Resilience & Fallback**: Degrade gracefully to native kube-scheduler scoring heuristics if the telemetry pipeline or RL policy is unavailable.

---

## 2. Architecture Constraints

- **Kubernetes Extender Protocol**: Must strictly conform to the native Kubernetes Scheduler Extender JSON HTTP payload contract (`ExtenderArgs`, `ExtenderFilterResult`, `HostPriorityList`).
- **Stateless Scoring**: Extender endpoints must remain idempotent and stateless, relying on cached telemetry snapshots from the Aggregator.
- **Python / Flask Runtime**: Implemented in Python 3.11+ using lightweight Flask web server, integrated with NumPy and PyTorch/Stable-Baselines3.

---

## 3. System Scope & Context (C4 Level 1)

The Scheduler Extender operates as an external webhook service invoked directly by the Kubernetes Control Plane during the scheduling pipeline.

```mermaid
flowchart TD
    User["DevOps / Cluster Operator"] -->|"kubectl apply -f manifest"| APIServer["Kubernetes API Server"]
    APIServer -->|"Unscheduled Pod"| KubeScheduler["kube-scheduler (Control Plane)"]
    
    subgraph "Custom Scheduling Framework"
        KubeScheduler -->|"POST /filter & /prioritize"| Extender["Scheduler Extender Service (Port 8888)"]
        Extender -->|"HostPriorityList (Scores 0-100)"| KubeScheduler
        Telemetry["Telemetry Pipeline (Metrics Server / eBPF / CommGraph)"] -->|"7D State Telemetry"| Extender
    end

    KubeScheduler -->|"Bind Pod to Node"| WorkerNodes["Worker Nodes (Node 1, 2, 3)"]
```

---

## 4. Solution Strategy

1. **Extender Integration**: Expose two REST endpoints (`/filter` and `/prioritize`) compatible with `KubeSchedulerConfiguration`.
2. **7D State Feature Extraction**: For each candidate node, construct a feature vector:
   $$s = [cpu\_eff, mem\_eff, node\_cpu, node\_mem, disk\_io, net\_lat, node\_temp]$$
3. **Composite Scoring**: Combine normalized resource balance scores and communication affinity scores into an integer score in the range `[0, 100]`.
4. **Deterministic Heuristic Scoring (RL Path Unverified)**: Uses a deterministic weighted heuristic scoring function. Note: As documented in `CLAIMS.md` and Rule 4.10, the RL policy scoring path (`predict()`) is currently unverified due to Defect D5 (feeding a 7D vector into a 42D model) and must NOT silently fall back to heuristic while claiming RL inference.

---

## 5. Building Block View

### 5.1 Container Diagram (C4 Level 2)

```mermaid
flowchart LR
    subgraph "Control Plane Node"
        KS["kube-scheduler"]
        APIS["kube-apiserver"]
    end

    subgraph "Scheduler Extender Container (src/scheduler)"
        API["Flask HTTP Server (extender_server.py)"]
        Scorer["NodeScorer Engine (scorer.py)"]
        Agg["TelemetryAggregator (src/telemetry)"]
        Graph["CommunicationGraph (src/telemetry)"]
    end

    subgraph "Cluster Telemetry Sources"
        Prom["Prometheus / Metrics Server"]
    end

    KS -->|"HTTP POST /prioritize"| API
    API --> Scorer
    Scorer --> Agg
    Agg --> Graph
    Agg -->|"Metrics query"| Prom
    Agg -->|"Node & Pod query"| APIS
    API -->|"JSON HostPriorityList"| KS
```

### 5.2 Component Diagram (C4 Level 3: `src/scheduler/`)

```mermaid
classDiagram
    class FlaskExtenderApp {
        +filter_nodes() ExtenderFilterResult
        +prioritize_nodes() HostPriorityList
        +health_check() Dict
    }

    class NodeScorer {
        -float resource_weight
        -float comm_weight
        -Policy rl_policy
        +set_rl_policy(policy)
        +score_candidate_nodes(pod_name, candidate_nodes, snapshot) List~Dict~
        -_compute_heuristic_score(state_vec, pod_name, node_name, snapshot) float
    }

    class ClusterSnapshot {
        +List nodes
        +List pods
        +Dict node_metrics
        +CommunicationGraph comm_graph
        +compute_state_vector(pod_name, candidate_node) ndarray
        +get_node_utilization(node_name) Dict
    }

    class CommunicationGraph {
        +record_communication(src, dst, count, bytes)
        +calculate_communication_affinity(target_pod, candidate_node, pod_locations) float
        +get_node_latency(node_a, node_b) float
    }

    FlaskExtenderApp --> NodeScorer : delegates scoring
    NodeScorer --> ClusterSnapshot : fetches 7D state vector
    ClusterSnapshot --> CommunicationGraph : computes network affinity
```

---

## 6. Runtime View (Sequence Diagram)

The following sequence illustrates the complete life cycle of an unscheduled pod being prioritized by the Scheduler Extender:

```mermaid
sequenceDiagram
    autonumber
    actor User as Client
    participant KubeAPI as kube-apiserver
    participant KS as kube-scheduler
    participant Extender as extender_server.py
    participant Scorer as scorer.py
    participant Aggregator as TelemetryAggregator

    User->>KubeAPI: Submit pod manifest
    KubeAPI->>KS: Notify unscheduled pod
    KS->>KS: Run native filtering plugins
    KS->>Extender: POST /prioritize (Pod spec, Candidate Nodes)
    Extender->>Aggregator: get_cluster_snapshot()
    Aggregator-->>Extender: ClusterSnapshot (Nodes, Pods, CommGraph)
    Extender->>Scorer: score_candidate_nodes(pod, candidate_nodes, snapshot)
    loop For each candidate node
        Scorer->>Aggregator: compute_state_vector(pod, candidate_node)
        Aggregator-->>Scorer: 7D state vector [cpu_eff, mem_eff, ..., net_lat]
        Scorer->>Scorer: Compute composite score (Resource + Network Affinity)
    end
    Scorer->>Scorer: Normalize scores to [0, 100]
    Scorer-->>Extender: HostPriorityList [{Host: node1, Score: 95}, ...]
    Extender-->>KS: HTTP 200 HostPriorityList JSON
    KS->>KS: Combine with internal priority scores
    KS->>KubeAPI: Bind pod to highest scoring node
```

---

## 7. Deployment View

In a multi-node Kubernetes cluster (e.g. Kind or production bare-metal):

```mermaid
flowchart TD
    subgraph "Control Plane Node (kind-control-plane)"
        KubeSched["kube-scheduler"]
        KubeConfig["KubeSchedulerConfiguration (/etc/kubernetes/scheduler-config.yaml)"]
        ExtenderProc["Scheduler Extender Daemon (Port 8888)"]
        KubeSched -.->|"Reads config"| KubeConfig
        KubeSched -->|"localhost:8888"| ExtenderProc
    end

    subgraph "Worker Node 1"
        P1["Frontend Pod"]
        P2["Orders Pod"]
    end

    subgraph "Worker Node 2"
        P3["Cart Service Pod"]
        P4["Catalog Service Pod"]
    end

    subgraph "Worker Node 3"
        P5["Payment Service Pod"]
    end

    ExtenderProc -.->|"Monitors traffic & latency"| P1
    ExtenderProc -.->|"Monitors traffic & latency"| P3
    ExtenderProc -.->|"Monitors traffic & latency"| P5
```

---

## 8. Cross-Cutting Concepts

### 8.1 7-Dimensional State Vector
For any given pod $p$ and candidate node $n$, the state vector is structured as:
1. $cpu\_eff \in [0, 1]$: Predicted CPU headroom efficiency post-placement.
2. $mem\_eff \in [0, 1]$: Predicted memory headroom efficiency post-placement.
3. $node\_cpu \in [0, 1]$: Current node CPU saturation.
4. $node\_mem \in [0, 1]$: Current node memory saturation.
5. $disk\_io \in [0, 1]$: Disk I/O load factor.
6. $net\_lat \in [0, 1]$: Weighted network latency to communicating peer pods.
7. $node\_temp \in [0, 1]$: Node thermal throttling / hardware health coefficient.

### 8.2 Heuristic Scoring Formula
$$\text{ResourceScore} = \frac{cpu\_eff + mem\_eff}{2}$$
$$\text{CommScore} = 1.0 - net\_lat$$
$$\text{CompositeScore} = w_{res} \cdot \text{ResourceScore} + w_{comm} \cdot \text{CommScore}$$
Normalized into integer range $[0, 100]$:
$$\text{Score}(n) = \text{round}\left(\frac{\text{CompositeScore}(n) - \min(S)}{\max(S) - \min(S) + \epsilon} \times 100\right)$$

---

## 9. Architecture Decisions (ADR)

- **ADR-01: Extender Pattern vs. Out-of-Tree Scheduler Binary**: Selected the Kubernetes Scheduler Extender webhook pattern over recompiling `kube-scheduler` in Golang. This allows running advanced Python RL engines (PyTorch, SB3) natively without Go-to-Python C-bindings or gRPC serialization overhead.
- **ADR-02: Strict Normalization Range**: Normalized final node scores to `[0, 100]` matching Kubernetes default weight scales, ensuring smooth composition with native scheduler priority plugins.
- **ADR-03: Two-Phase Degradation**: If the trained PPO policy model cannot be loaded, scoring seamlessly degrades to the closed-form deterministic heuristic without returning 500 errors to `kube-scheduler`.
