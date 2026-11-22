# Architecture and Research Decisions Log

Project: Communication-aware pod scheduling and rescheduling for Kubernetes  
Owner: Anubhav Kumar (GE-230211124) | Supervisor: Prof. (Dr.) Durgaprasad Gangodkar  

This log records major design choices, alternatives considered, justifications, and items requiring explicit verification.

---

## 1. Items to Verify in Phase 1 (T1.2) & Phase 3 (T3.1)

### DEC-001: Kernel `netem` support in Kind node container (T1.2)
- **Context:** Inter-node latency emulation on a single machine requires `tc qdisc add dev eth0 root netem delay ...` inside Kind worker containers.
- **Risk:** Kind node base images (`kindest/node`) might lack the `tc` binary, or the host kernel might lack the `sch_netem` module.
- **Action for T1.2:** Verify with `docker exec <worker> tc -V` and check `lsmod | grep sch_netem`. If missing, modprobe `sch_netem` on the Linux host.

### DEC-002: μBench Telemetry & Overhead Verification (T1.3 / T2.1)
- **Context:** μBench is chosen as the primary microservice benchmark (matching Marchese & Tomarchio 2025).
- **Risk:** μBench may not output native OpenTelemetry traces out of the box, requiring either sidecars, eBPF, or Prometheus metrics scraping.
- **Action for T2.1:** Review μBench capabilities and present telemetry options with computational and operational costs for owner approval.

### DEC-003: Control-Plane Reachability of Scheduler Extender in Kind (T3.1)
- **Context:** In `manifests/scheduler/scheduler-policy.yaml`, the extender URL was set to `http://172.17.0.1:8888`.
- **Risk:** The Docker network bridge on Linux is often `172.18.0.1` (or dynamic), leading to silent connection timeouts.
- **Action for T3.1:** Determine correct control-plane reachability:
  - *Option A:* Run Extender as a Pod with `hostNetwork: true` on the control-plane node.
  - *Option B:* Access through the dynamic Kind bridge gateway IP.
  - *Decision:* To be calibrated and verified in T3.1.

### DEC-004: Simulator vs Live Cost Calibration (Gate G5a)
- **Context:** The RL environment uses an analytical cost model.
- **Risk:** If modeled cost does not correlate with empirical $p95$ latency measured under load, RL policies trained in simulation will optimize a surrogate metric disconnected from reality.
- **Action for Phase 5:** Do not train or claim RL results until Gate G5a validates correlation between the model and real measured p95.

### DEC-005: kube-scheduler DNS Resolution in Kind (T3.1)
- **Context:** The `kube-scheduler` control plane pod runs with `hostNetwork: true`.
- **Constraint:** It cannot resolve in-cluster CoreDNS names (e.g., `*.svc.cluster.local`) without special configuration.
- **Action for T3.1:** Use a direct IP / ClusterIP or bind the extender to `hostNetwork` on the control-plane node.

### DEC-006: Extender Bootstrapping & Scheduling Deadlock Prevention (T3.1)
- **Context:** If `kube-scheduler` starts before the extender is healthy, it could block scheduling of all pods (including the extender itself if run in-cluster).
- **Constraint:** Extender policy must specify `ignorable: true` during bootstrapping so core cluster services schedule cleanly.

---

## 2. Owner Decisions

### DEC-007: Workload for T1.3 — μBench (Owner Decision, 2026-11-22)
- **Decision:** Use **μBench** (Detti et al., IEEE TPDS 2023) as the microservice workload for T1.3 and all subsequent live experiments.
- **Rationale:** Matches the benchmark used by Marchese & Tomarchio 2025 (the primary paper this project extends), enabling a reproducible comparison. μBench generates configurable CPU, memory, network bandwidth, and disk I/O load via a JSON/YAML topology.
- **Status:** Owner confirmed. T1.3 not yet started (pending T1.2 completion and rtt.csv review).

---

## 3. Host-Safety Rule (NEW — 2026-11-22)

### RULE-001: No sudo or kernel/network changes without explicit owner approval
- **Rule:** Never run `sudo`, `modprobe`, `tc`, or any other command that modifies host kernel state or network configuration without first:
  1. Showing the **exact command(s)** to the owner in a Status Report.
  2. Receiving explicit written approval.
- **Cleanup requirement:** Every host-level change must have a corresponding cleanup script (e.g., `scripts/netem_clear.sh`) that fully reverts the change, and an entry in this file describing what was changed and what the cleanup does.
- **Cleanup script:** `scripts/netem_clear.sh` (reverting netem qdisc on Kind worker containers — to be populated in T1.2 after approval).

