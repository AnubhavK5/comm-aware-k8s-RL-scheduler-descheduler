# Phase 0 System & Environment Precheck (T0.6)

Recorded At: 2026-11-20T16:08:00+05:30  
Host Environment: Linux (Arch / CachyOS)  
Kernel: `7.2.9-2-cachyos #1 SMP PREEMPT_DYNAMIC` x86_64  

---

## 1. Physical Hardware and Container Platform

| Resource | Specification / Measured Value |
| :--- | :--- |
| **OS** | Linux 7.2.9-2-cachyos x86_64 |
| **CPU Model** | AMD Ryzen 7 8845HS w/ Radeon 780M Graphics |
| **CPU Cores** | 16 logical cores (8 cores / 16 threads) |
| **Total Memory (RAM)** | 27 GiB (Available: 16 GiB, Used: 11 GiB) |
| **Swap Space** | 27 GiB |
| **Docker Engine** | Docker version 29.9.3, build 5457199aa5 |
| **Kind Version** | kind v0.33.0 go1.27.0 |
| **Kind Docker Subnet** | IPv4: `172.18.0.0/16` (Gateway: `172.18.0.1`), IPv6: `fc00:f853:ccd:e793::/64` |

---

## 2. Kernel & Traffic Control Verification (T1.2 Readiness)

1. **`tc` utility inside Kind worker container:**
   ```bash
   $ docker exec rl-scheduler-worker tc -V
   tc utility, iproute2-6.15.0, libbpf 1.5.0
   ```
   **Result:** `tc` is pre-installed in `kindest/node:v1.37.0`.

2. **Kernel `sch_netem` module availability:**
   - Inspection:
     ```bash
     $ modinfo sch_netem
     filename: /lib/modules/7.2.9-2-cachyos/kernel/net/sched/sch_netem.ko.zst
     description: Network characteristics emulator qdisc
     ```
   - Current state: Module exists in kernel storage (`/lib/modules/...`) but is not currently loaded in memory (`lsmod | grep netem` returned empty).
   - **Requirement for T1.2:** Run `sudo modprobe sch_netem` on the Linux host before applying `tc qdisc add dev eth0 root netem` inside Kind worker containers.

---

## 3. μBench Telemetry & Metrics Review

- **Official Repository:** `mSvcBench/muBench` (Detti, Funari, Petrucci, IEEE TPDS 2023).
- **Workload Model:** Uses configurable "Loader functions" simulating configurable CPU computation ($\pi$ calculation), memory allocations, disk I/O operations, and network payload bytes forwarded over HTTP/gRPC.
- **Built-in Telemetry Support:**
  - **Prometheus:** Natively integrated into the μBench reference stack. Microservices expose Prometheus endpoints or are scraped via Prometheus/Grafana/CAdvisor.
  - **Jaeger / Istio:** μBench documentation provides reference configurations for Jaeger tracing and Istio service mesh.
  - **OpenTelemetry:** Native OpenTelemetry auto-instrumentation is not bundled by default inside the bare μBench python containers, but can be added via the OpenTelemetry Python automatic instrumentation agent (`opentelemetry-instrument`) or an OpenTelemetry Collector scraping Prometheus metrics.

---

## 4. Telemetry Options with Relative Costs [FOR OWNER DECISION IN T2.1]

To construct the live inter-workload communication graph ($C_{w1 \to w2}$) without making assumptions, here are the viable options:

| Option | Architecture | Operational & Resource Cost | Alignment with Synopsis |
| :--- | :--- | :--- | :--- |
| **Option A: OpenTelemetry Auto-Instrumentation Agent + OTel Collector** | Attach OpenTelemetry agent to Python/HTTP microservices; sends OTLP spans to in-cluster OTel Collector. Aggregator queries collector for edge weights. | **Medium-High:** Adds ~30–50MB RAM per pod, requires configuring OTel SDK environment variables in Deployment manifests. | **Exact match:** Matches the exact wording and reference in your synopsis. |
| **Option B: Prometheus Server + App Request Metrics (as in Marchese & Tomarchio)** | Microservices expose standard HTTP request metrics (`http_requests_total{source=..., destination=...}`). In-cluster Prometheus scrapes every 5–10s. Aggregator queries Prometheus HTTP API. | **Low-Medium:** Very lightweight (~15MB RAM per pod), rock-solid stability, proven in Marchese 2025. | **Close match:** Requires clarifying in synopsis that Prometheus was used for metric aggregation. |
| **Option C: Lightweight Envoy / Service Mesh Sidecar** | Deploy Envoy sidecar alongside each pod to transparently record peer-to-peer traffic matrices without changing app code. | **High:** Consumes ~100MB RAM per pod (200MB per service across 2 replicas); adds significant memory pressure on a local laptop. | **Overkill:** High resource overhead on a local 3-node Kind cluster. |
| **Option D: eBPF-based Traffic Snooping (e.g., Pixie or custom eBPF)** | Host/node-level eBPF probes inspect TCP socket connections between container IPs. | **High Engineering Complexity:** Requires elevated container privileges (`CAP_SYS_ADMIN`), kernel header mounting inside Kind. | **Too brittle:** High failure risk in simulated Kind environments. |

---

## 5. Verification Status Summary

- [x] Host OS, CPU, RAM, and Docker versions recorded.
- [x] Docker Kind subnet confirmed: `172.18.0.0/16` (Gateway `172.18.0.1`).
- [x] `tc` confirmed present inside Kind worker container (`iproute2-6.15.0`).
- [x] `sch_netem` kernel module confirmed present on host (needs `modprobe` before T1.2).
- [x] μBench telemetry capabilities analyzed.
- [x] Telemetry options formulated with trade-offs for owner decision.
