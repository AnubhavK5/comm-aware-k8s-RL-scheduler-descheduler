# Current Project Hand-off State

Updated At: 2026-11-20T16:08:20+05:30  
Phase: Phase 0 Completed  
Owner: Anubhav Kumar (GE-230211124)  

- **What is Done:**
  - T0.1: Git tag `v0-sim-prototype` created and verified.
  - T0.2: `CLAIMS.md` and `docs/DECISIONS.md` created with verified vs unverified claims and architectural verification items.
  - T0.3: Relabeled `README.md`, `src/dashboard/app.py`, `src/dashboard/templates/index.html`, and `src/rl/evaluate.py`. Mislabeled "PPO" names changed to "greedy heuristic", "Comm Latency (ms)" marked as "Weighted Comm Cost (model units)".
  - T0.4: `tests/test_eval_integrity.py` created. Verified it FAILED on unmodified code (AssertionError for missing model.predict), and PASSED (3/3) after relabeling evaluate.py.
  - T0.5: `docs/papers/NOTES.md` written analyzing Marchese & Tomarchio 2025 and KubeAI 2026 equations, setups, μBench loader structure, and k6 evaluation.
  - T0.6: Precheck completed and saved to `docs/evidence/precheck.md` (RAM, CPU, Kind subnet `172.18.0.0/16`, `tc` present in Kind worker, `sch_netem` module verified, telemetry trade-offs tabulated).
- **What is Broken / Unverified:**
  - PPO model still learns no-op (to be redesigned in Phase 5).
  - Cluster extender wiring into kube-scheduler unverified (to be wired in Phase 3).
  - Workload pods in `microservice_app.yaml` are idle (to be replaced with μBench in Phase 1).
- **What is Next:**
  - Awaiting owner review before starting Phase 1 (Task T1.1).
