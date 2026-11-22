# Current Project Hand-off State

Updated At: 2026-11-22T18:12:00+05:30
Phase: Phase 0 Completed (T0.1 – T0.12); T1.1 and T1.2 in progress
Owner: Anubhav Kumar (GE-230211124)

**Python version status:** `3.14 full` (host, all tests pass); `3.11 partial` (SB3 install timed out in container; AST/proxy logic verified, RL training not tested).

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
  - T0.12a: Switched to one `ModelCountingProxy` PER CONFIG (no shared counter). Mutation test (`tests/test_mutation_proxy.py`) demonstrates that two configs with `uses_model=True` where only one calls `predict()` correctly FAILS the guard.
  - T0.12b: D5 xfail test rewritten to build a 7-dim vector locally (no cluster). Fails with `AssertionError: 7 != 42`, not a kubeconfig error. Guard 3 renamed to "Observation shape check" (passive env consistency check, not a model-call guard). Label regex updated to use `\b` word boundaries.
  - T0.12c: `docs/papers/NOTES.md` updated: removed Rejiba `[p. 15]` cite (tagged `[WEB, unverified]`); removed "round-trip ping" for `net_lat`; Related Work pp. 11–13, refs pp. 14–15 added; Marchese p. 13 integration note added; KubeAI p. 80274 synthetic workload note added; uBench lines tagged; header reworded.
  - T0.12d: `docs/DESCHEDULER.md` title and intro updated to "Continuous Descheduler (greedy heuristic; PPO Phase 5 stretch)". README lines 107, 126, 161 updated to remove premature PPO claims.
  - T0.12e: Python version status updated to "3.14 full, 3.11 partial".
  - T0.12f: Status split into "not run" vs "derived from docs, not observed" (see NOT VERIFIED section below).
- **NOT VERIFIED — not run (not executed on this machine during Phase 0):**
  - Live eviction safety guards (replica check, cooldown, namespace filter) on a real cluster workload.
  - kube-scheduler extender HTTP call to our extender endpoint.
  - Live PPO model training convergence (SB3 install timed out on 3.11; not attempted on 3.14).
  - netem RTT calibration and rtt.csv validation (T1.2, pending approval).
- **NOT VERIFIED — derived from docs, not observed:**
  - uBench OpenTelemetry support (tagged `[WEB, unverified]` in precheck.md).
  - Rejiba serialization overhead for extender (tagged `[WEB, unverified: no PDF]` in NOTES.md).
  - Kind node image `tc` availability was read from precheck.md (observed in a previous session, not re-confirmed this session).
- **What is Broken / Unverified:**
  - Full pip install of stable-baselines3 on Python 3.11 inside container timed out over network (host runs Python 3.14).
  - PPO model learns no-op (to be redesigned in Phase 5).
  - Live extender wiring into kube-scheduler unverified (to be wired in Phase 3).
  - Live eviction safety guards untested under active cluster workload (Phase 3).
- **What is Next:**
  - T1.1: Create Kind cluster (1 control-plane + 3 workers, pinned image).
  - T1.2: Apply netem on workers only (pending `modprobe` command approval from owner).
  - T1.3: Workload selection = **uBench** (owner decision logged in `docs/DECISIONS.md` DEC-007).
