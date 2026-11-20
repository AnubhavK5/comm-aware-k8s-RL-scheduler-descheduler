# Claims Ledger

Project: Communication-aware pod scheduling and rescheduling for Kubernetes  
Owner: Anubhav Kumar (GE-230211124) | Supervisor: Prof. (Dr.) Durgaprasad Gangodkar  

This document tracks every claim made in the README, synopsis, and paper. No claim may be cited in documentation, presentations, or papers unless verified with saved evidence under `results/` or `docs/evidence/`.

---

## 1. Claims Ledger

| Claim | Status Today | Allowed Wording | Evidence Needed | Required Gate / Milestone |
| :--- | :--- | :--- | :--- | :--- |
| **Comm-aware descheduling cuts latency** | Not supported | "In a simulator with modeled latency, a greedy heuristic rule lowers modeled cost" | Live p95 response time in Scenario S2 | Gate G4 |
| **PPO-based descheduler outperforms baselines** | Not supported | "An RL attempt was made; results in Section X (or simulator prototype evaluated)" | Live S2 comparison against greedy with same information | Gate G5b |
| **Outperforms KubeAI / Load-Aware** | Not supported | "Outperforms KubeAI-style / Load-Aware-style baselines in simulated cost" (once C1/C2 exist) | Multi-trial live experiments in Phase 4 | Phase 4 (G4) |
| **Uses OpenTelemetry** | Not implemented | None yet (planned for Phase 2) | Non-empty live telemetry graph fed from OTel traces | Gate G2 |
| **Uses disk I/O and node temperature** | Not implemented | None (unmeasurable in Kind without host sensors; remove from claims) | None (feature deleted from state vector) | Task T2.3 |
| **Safety guards (replicas >= 2, cooldown, namespace)** | Code exists | "Implemented in controller; tested in unit test suite" | Live eviction log demonstrating safety enforcement | Phase 3 (T3.3) |
| **Extender integrated with kube-scheduler** | Endpoints exist | "Extender service implemented; kube-scheduler wiring unverified" | Kube-scheduler control-plane log showing HTTP call to extender | Phase 3 (T3.1) |

---

## 2. Forbidden Claims (Until Backed by Gate-Passed Evidence)

1. **"PPO reduces latency by 40.5%"** — FORBIDDEN. (The benchmark used a hardcoded greedy search, not the PPO model, and evaluated on an analytical formula, not measured milliseconds).
2. **"64.5% reduction in node resource variance"** — FORBIDDEN. (Derived from the same greedy simulation loop).
3. **"92.5% fewer evictions than Load-Aware"** — FORBIDDEN. (Compared against an unconstrained strawman baseline that evicted on almost every cycle without a gain check).
4. **"Validated on a real Kubernetes cluster"** — FORBIDDEN. (Only plumbing and deployment manifests were checked; no benchmark has run live on Kind with measured traffic).
5. **"Communication latency measured in milliseconds"** — FORBIDDEN. (Current numbers are unitless analytical sums: $0.2 \times \text{calls}$ and $5.0 \times \text{calls}$).
