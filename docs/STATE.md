# Current Project Hand-off State

Updated At: 2026-11-21T17:48:00+05:30  
Phase: Phase 0 Rigorous Clean-up Completed (T0.1 – T0.11)  
Owner: Anubhav Kumar (GE-230211124)  

- **What is Done:**
  - T0.1: Git tag `v0-sim-prototype` created and verified.
  - T0.2: `CLAIMS.md` and `docs/DECISIONS.md` created with verified vs unverified claims and architectural verification items (DEC-001 to DEC-006).
  - T0.3: Relabeled `README.md`, `src/dashboard/app.py`, `src/dashboard/templates/index.html`, and `src/rl/evaluate.py`.
  - T0.4 & T0.7: Real evaluation guards implemented in `tests/test_eval_integrity.py`:
    - `ModelCountingProxy` automatically counts calls to `predict()`.
    - Any configuration labeled with RL/learned/policy/AI requires `uses_model=True` and counter >= 1.
    - Sentinel failing model verified to allow all non-model heuristic configs to run.
    - Defect D5 (7D vs 42D state mismatch) tracked as an `@pytest.mark.xfail` test.
    - Demonstrated mutation failures verified and logged.
  - T0.8: Added `Any` to `src/rl/evaluate.py` typing imports. Verified Python 3.11 AST parsing and `ModelCountingProxy` logic under Python 3.11 container.
  - T0.9: Corrected `docs/papers/NOTES.md` and `docs/evidence/precheck.md`:
    - Marchese & Tomarchio uses Go scoring plugin (p. 7) in Scheduling Framework, not extender.
    - Eqs. 1–6 balance CPU, memory, network bandwidth, and disk bandwidth (pp. 7–8).
    - Descheduler enforces `replicas >= 1` maintained (p. 8).
    - Prometheus measures individual resource metrics, not pairwise call counts.
    - KubeAI endpoints are `POST /schedule`, `GET /metrics`, `POST /update-policy` (p. 80273).
    - KubeAI 7D state vector has no pairwise communication features (p. 80271).
    - Removed unverified Rejiba "10-30ms" claim.
    - Added Marchese references [19], [24], [26], [27] to must-read list before novelty claims.
  - T0.10: Relabeled README overview and `docs/SCHEDULER.md` to remove premature PPO descheduler assertions and document the unverified RL scoring path.
  - T0.11: Updated `CLAIMS.md` status for safety guards to "Implemented, untested".
- **What is Broken / Unverified:**
  - Full pip install of stable-baselines3 on Python 3.11 inside container timed out over network (host runs Python 3.14).
  - PPO model learns no-op (to be redesigned in Phase 5).
  - Live extender wiring into kube-scheduler unverified (to be wired in Phase 3).
  - Live eviction safety guards untested under active cluster workload (Phase 3).
- **What is Next:**
  - Awaiting owner review of Phase 0 closeout before starting Phase 1 (T1.1).
