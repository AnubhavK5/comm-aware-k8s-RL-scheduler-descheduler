# AGENT PLAN AND RULES

Project: Communication-aware pod scheduling and rescheduling for Kubernetes
Owner: Anubhav Kumar (GE-230211124) | Supervisor: Prof. (Dr.) Durgaprasad Gangodkar

> **Read this whole file at the start of every session.** Say which phase and task
> you are working on. If anything here conflicts with a request, stop and ask the owner.
> The owner must be able to explain every design choice in a viva. You are the typist
> and checker, not the decision-maker, for anything marked [OWNER DECIDES].

---

## 0. Session protocol (saves tokens and prevents drift)

1. Read this file and `docs/STATE.md` (the hand-off note). Do **not** re-read the whole repo.
2. Work on **one task** from Section 5. Small commit, tests run, evidence saved.
3. End the session by (a) updating `docs/STATE.md` (what is done, what is broken,
   what is next, 10 lines max) and (b) printing the **Status Report** (Section 9).
4. Anything you did not run yourself must be written as `NOT VERIFIED`.

---

## 1. Where the project actually stands (from an audit that ran the code)

**Real today:** Kubernetes client calls, Eviction API code, safety guards, Flask extender
endpoints (`/filter`, `/prioritize`), Kind manifests, plumbing unit tests.

**Simulated or modeled today:** every latency number (constants 0.2 ms same-node, 5.0 ms
cross-node), the whole README benchmark table, and all baselines (Python stand-ins inside
the same simulator).

**Verified defects (details in Section 7):**

- The README benchmark never uses the trained PPO model. The "Proposed" row is a greedy
  exhaustive search using the same cost function that scores it. The README table
  reproduces exactly with the model unable to load.
- The trained PPO learned almost nothing: argmax picks no-op 99.6% of the time (final
  cost equals do-nothing); sampled, it behaves like a random policy (about 30 evictions
  per 40 steps).
- The RL observation (42-dim) contains no communication data, yet half the reward depends
  on it. The agent cannot be communication-aware by construction. The environment's
  `step()` also picks the best destination node itself (an oracle).
- The benchmark is circular (metric = reward = oracle objective). The drift tested is CPU
  only; the communication graph never changes, so the core thesis is untested.
- Live path: nothing ever feeds the communication graph; the descheduler process builds its
  own empty graph; the objective ignores hypothetical moves; `disk_io` and `node_temp` are
  constants; the extender is never wired into kube-scheduler by the setup scripts; the
  workload pods are idle `python -m http.server`; no live run has ever been recorded.

**Claims allowed today:** "A simulator-based prototype of a communication-aware greedy
descheduler with safety guards."
**Claims NOT allowed today:** "PPO reduces latency by 40.5%", "validated on a real
cluster", "outperforms KubeAI / Load-Aware", "uses OpenTelemetry", "uses disk I/O and
node temperature".

---

## 2. Goal and contribution [OWNER DECIDES, mentor to confirm]

**Working contribution:** a communication-aware descheduler that relocates running
workloads when inter-service traffic patterns drift, evaluated on a latency-emulated Kind
cluster with a real microservice benchmark and real load.

- **Core (guaranteed paper):** the heuristic descheduler + communication-aware extender,
  measured live. Name it honestly ("greedy", "heuristic").
- **Stretch:** RL policy, reported **only** if it passes Gate G5. A negative or tie result
  is acceptable and gets reported as such.
- The word "RL" appears in a result label only if the trained model produced that result.

---

## 3. DO

1. **Evidence over narration.** Any sentence of the form "X works / X does Y" needs the
   command you ran and its output saved under `results/` or `docs/evidence/`. Otherwise
   write `NOT VERIFIED`.
2. **Describe what the code does, not what it is meant to do.** Before summarizing any
   component, grep its call sites. Mention anything stubbed, constant, unused, unwired, or
   falling back silently.
3. **Label every number** as `simulated`, `emulated` (tc netem), or `measured`.
4. **Information parity:** before any comparison, write down what information each method
   gets. All methods get the same information unless the difference is the thing being tested.
5. **Faithful baselines:** implement each baseline from the paper's equations (PDFs in
   `docs/papers/`). If not exact, call it "X-style" and say how it differs.
6. **Use upstream tools as-is** (uBench, k6, Prometheus, OpenTelemetry). Read their official
   docs first. Do not reimplement them.
7. **Read the papers, don't recall them.** Cite only what the PDFs in `docs/papers/` say,
   with page numbers in `docs/papers/NOTES.md`.
8. **Regression test per bug.** Every defect fixed gets a test that fails before the fix.
9. **Record decisions** in `docs/DECISIONS.md`: decision, alternatives, why. The owner
   reads and approves them.
10. **Reproducibility:** pin versions, record seeds, save raw outputs, one command per
    experiment, plots generated by script from raw CSVs.
11. **Safety:** descheduler defaults to `--dry-run`; evictions only in namespace
    `benchmark`; never touch `kube-system`.
12. **Report failure plainly.** Bad or negative results are fine. Hiding them is not.

## 4. DON'T

1. Don't present simulated results as real, or greedy results as "PPO/RL".
2. Don't evaluate with the same function you optimize. Real measurements (client-side
   p95/p99, throughput, errors) are the primary metrics; model-based cost is only a
   diagnostic.
3. Don't put oracle or perfect-information shortcuts inside the learning environment or a
   baseline unless every method gets them.
4. Don't hardcode telemetry constants in anything reported as measured. Delete features you
   cannot measure (e.g. `node_temp`) from claims, code, and the paper.
5. Don't weaken baselines (e.g. "evict every step, no gain check"). A strawman invalidates
   the paper.
6. Don't tune anything after looking at evaluation results without logging it. Training
   seeds and evaluation seeds are separate and fixed in advance.
7. Don't report a headline percentage from fewer than 5 trials, or without a confidence
   interval.
8. Don't edit README or paper claims that are not in `CLAIMS.md` with evidence.
9. Don't call something "real" because code exists. Say "implemented, unverified" until
   it ran in the cluster with saved logs.
10. Don't add silent fallbacks (e.g. scorer falling back to the heuristic when the model
    fails). Log loudly and record `rl_path_active=true/false` in every result file.
11. Don't delete, overwrite, or hand-edit raw results.
12. Don't refactor or add features outside the current task (no new dashboards, no extras).
13. Don't invent citations, numbers, or library APIs. If unsure, say so and check docs.
14. Don't write "everything is working." Report a pass / fail / not-run table instead.

## 4b. Stop and ask the owner before you...

- change the reward, observation space, action space, or any evaluation metric;
- change a baseline definition or add/remove a baseline;
- change a claim in README, synopsis, or paper text;
- install a heavy dependency (CUDA/torch builds fill the disk), or change cluster size;
- see a result that is much better or much worse than expected (investigate first,
  explain, then ask);
- find that a gate (Section 5) fails.

---

## 5. Plan (weeks are relative; compress or stretch to the real deadline)

### Phase 0 - Freeze and clean the claims (week 1)

| Task | Done when |
|---|---|
| T0.1 `git tag v0-sim-prototype` | tag exists |
| T0.2 Create `CLAIMS.md` from Section 8 | file exists, owner has read it |
| T0.3 Relabel: README table marked "simulation only, modeled latency, PPO not used"; rename "Comm Latency (ms)" to "weighted comm cost (model units)"; dashboard "PPO step" renamed to "greedy step" | grep shows no mislabeled "PPO" |
| T0.4 Add `tests/test_eval_integrity.py`: any config labeled RL must call `model.predict` at least once; assert obs shape equals the model's observation space; fail on silent fallback | test fails on the current code, passes after fix |
| T0.5 Put the 4 PDFs in `docs/papers/`; write `NOTES.md` (what each paper actually did, with page refs) | file exists |

### Phase 1 - Real testbed (weeks 1-4)

| Task | Done when |
|---|---|
| T1.1 Kind: 1 control-plane + 3 workers, pinned node image; document machine RAM/CPU needed | `kubectl get nodes`, `kubectl top nodes` output saved |
| T1.2 Latency emulation with `tc netem` on **workers only**; preferably delay only inter-worker traffic (tc prio + filter on worker IPs) so API server, extender and load-generator paths are untouched. Netem acts on egress at each node, so RTT is roughly the sum of both directions: calibrate, don't assume. Check `tc` exists in the node image | `results/env_validation/rtt.csv`: same-node RTT under 1 ms; cross-node within 20% of target; control-plane path unaffected |
| T1.3 Real workload: **uBench** as primary (same tool as Marchese and Tomarchio, so results are comparable; topology is controllable). 2 replicas per service (the safety guard needs 2). Topology config committed with fixed seeds. Optional later: Online Boutique as a generalization check. [OWNER DECIDES] | all pods Ready; one request through the gateway returns 200 and traverses the expected chain |
| T1.4 k6 load script (VUs, ramp, duration as parameters) writing CSV | one run gives p50/p95/p99, RPS, error rate |
| **Gate G1: placement matters.** Pin communicating services together (best) vs spread apart (worst), 5 trials each | p95 differs clearly (report % and CI). If not: raise delay / call depth / payload, lower per-service CPU time. If still no effect, **stop and tell the owner**: there is no headroom in this setup |
| T1.5 Baseline: default scheduler only, 5 trials x 10-20 min, VU sweep | raw CSVs in `results/baseline_default/` + `scripts/make_plots.py` regenerates the plots |

### Phase 2 - Real telemetry (weeks 3-6)

| Task | Done when |
|---|---|
| T2.1 Choose the telemetry source and record it in `DECISIONS.md` (OpenTelemetry collector with auto-instrumentation, app metrics + Prometheus, service mesh, or eBPF). Need per (source workload -> destination workload) request rate, latency if available. Check the benchmark's own docs for built-in support. The synopsis promises OpenTelemetry, so prefer it unless the cost is prohibitive [OWNER DECIDES] | decision logged |
| T2.2 Aggregator: windowed + EMA; key by **Deployment/workload name**, not pod name (pods churn on eviction); one shared store used by both the extender and the descheduler (no second, empty graph) | `GET /graph` is non-empty within 60 s of load starting |
| **Gate G2: telemetry is correct.** Compare measured edge weights with the true call rates in the uBench config | rank/Pearson correlation reported; project threshold: 0.8 or higher, otherwise fix before moving on |
| T2.3 Network latency input: use measured RTT probes, or the netem value validated in T1.2 and say "configured and validated". Remove `disk_io` and `node_temp` from state and docs unless really measured (Kind has no real temperature) | no constants remain in the state vector; synopsis wording updated |

### Phase 3 - Make the live system do what the docs say (weeks 4-8)

| Task | Done when |
|---|---|
| T3.1 Wire the extender into kube-scheduler (kubeadm config patch / extra mount). Prefer running the extender as an in-cluster Deployment; if it stays a host process, document the gateway IP and verify reachability from the control-plane container | scheduler logs and extender logs both show `/filter` and `/prioritize` calls; a test pod lands where the scores say; logs saved |
| T3.2 One shared module `src/common/placement_objective.py` used by **both** the extender scoring and the descheduler: (a) comm cost = live graph x validated inter-node latency, (b) resource balance computed **under the hypothetical move** (shift the pod's measured usage between nodes) | unit tests: hot->cold move lowers the resource term; co-locating a chatty pair lowers the comm term |
| T3.3 Descheduler heuristic core: gain above calibrated eviction cost, hysteresis/cooldown, at most 1 eviction per cycle, replicas >= 2 ready, namespace `benchmark` only, dry-run default. Log each decision with objective before/after and, later, the **actual landing node** | decision log CSV with a placement-agreement-rate column |
| T3.4 Calibrate eviction cost: evict each service once under load, record errors, latency spike, time-to-ready | `eviction_cost` set from data, not guessed |
| **Gate G3: end-to-end smoke test.** Deliberately spread a chatty pair; run the descheduler | converges to co-located within a few cycles without thrashing; p95 better than the same run with the descheduler off |

### Phase 4 - Live experiments (weeks 8-12)

Write `docs/eval_plan.md` (hypotheses, configs, scenarios, metrics, statistics) **before**
running anything.

| Config | What it is |
|---|---|
| C0 | Default scheduler |
| C1 | Load-Aware-style descheduler (resource-only, Marchese and Tomarchio Eq. 7-9) + default scheduler |
| C2 | KubeAI-style placement (resource + communication at placement, no descheduler). Say "style": their trained model is not public |
| C3 | Ours: comm-aware extender + comm-aware descheduler |
| C4 | Ablation: ours without the communication term |
| C5 | Ablation: ours with the descheduler off |

| Scenario | Purpose |
|---|---|
| S1 steady traffic, static topology | sanity, no harm done |
| **S2 traffic drift mid-run** (change which services are hot at a fixed time) | **the key test of the thesis** |
| S3 node pressure (stress pod on one node) | resource-aware behavior |
| S4 several apps colocated (as Paper 2, scenario 2) | optional |

Rules: >= 5 trials, 10-20 min each, same arrival pattern and seeds across configs,
**randomized run order**, cluster reset between runs. Primary metrics: client p95/p99,
throughput, error rate. Mechanism metrics: cross-node call fraction, evictions,
availability dip per eviction. Overhead: agent CPU/RAM, decision time. Statistics: mean +/-
95% CI, paired differences, Welch t-test or Mann-Whitney, effect sizes.

**Gate G4:** C3 beats C0, C1, C2 in S2 with a paired-difference CI that excludes zero. If
not: debug and **ask the owner**; do not tune on the evaluation seeds.
Optional: if cloud credits appear (about 60% chance), repeat S2 on a larger multi-VM cluster
as an external-validity check.

### Phase 5 - RL stretch (weeks 10-15; only after G3, ideally after G4)

Environment spec (changes need owner approval):

1. **Observation includes communication:** per-workload cross-node comm share and the
   workload-by-node traffic matrix, plus placement, node utilization, pod usage.
   Act on **workloads** (Deployments), not pod names.
2. **No oracle in `step()`.** Action = (workload, destination) or (workload, "let scheduler
   decide"). The environment applies the scheduler's real rule, not an exhaustive search.
3. **Randomized drift in training:** several drift types, graph densities, node counts.
   The communication graph must change during episodes.
4. **Reward** = change in the cost model - lambda x disruption cost (lambda from T3.4
   measurements). Mask ineligible actions (replicas < 2, cooldown).
5. **Baselines in the same env:** no-op, random, greedy-with-threshold (same information),
   greedy-without-communication.
6. **Protocol:** >= 5 training seeds, separate fixed evaluation seeds, fixed hyperparameter
   budget, log reward / entropy / explained variance, evaluate **both** deterministic and
   sampled policies.
   Warning signs seen before: entropy barely moves, explained variance near 0, argmax
   collapsing to one action. Treat those as "the observation or reward is wrong," not as
   "train longer".
7. **One observation builder** shared by the env and the live controller; a test asserts
   they are identical.
8. **Calibrate the simulator from real data** (Phase 1/4): Gate G5a: report the correlation
   between modeled cost and measured p95 across placements. If the model does not track
   reality, the simulator results are not evidence.

**Gate G5b:** RL vs greedy-with-same-information on the live S2. Outcomes: win, tie with
fewer evictions, or lose. All are reportable. If it does not pass, RL goes in the paper as
an honest negative result or future work.

### Phase 6 - Paper (weeks 14-18)

- Outline: Intro, Related Work, Design, Implementation, Evaluation, Threats to validity
  (emulated latency, single host, Kind, small scale), Limitations, Conclusion.
- Related work: KubeAI (placement only; its communication terms are not in its RL
  state/reward), Load-Aware (fixed formula, no communication), KubeSPT (migration
  mechanism, not policy), DRS. The owner does a real literature search (Google Scholar,
  IEEE Xplore, arXiv) before any novelty claim; word it "to our knowledge".
- Reproducibility package: tag, configs, seeds, raw CSVs, one command per experiment.
- Update synopsis and README so every claim matches `CLAIMS.md`. Ask the mentor about venue.

### Timeline

| Weeks | Phase |
|---|---|
| 1 | P0 freeze + clean claims |
| 1-4 | P1 real testbed (G1) |
| 3-6 | P2 telemetry (G2) |
| 4-8 | P3 live system (G3) |
| 8-12 | P4 experiments (G4) |
| 10-15 | P5 RL stretch (G5a/b) |
| 14-18 | P6 paper |

---

## 6. Facts the agent previously got wrong (do not repeat)

- KubeAI's paper evaluated on Kind with 15,000 **generated** scheduling events and
  OpenTelemetry for traces. It does **not** mention k6 or a named benchmark. k6 + uBench
  on a 6-worker RKE2 cluster is **Marchese and Tomarchio's** setup (Paper 2).
- Claims about DRS using DeathStarBench / TrainTicket are **not verifiable** from the
  provided PDFs. Check the DRS paper before citing.
- "Extender integration: real" and "dashboard runs your trained PPO" were wrong
  (see Section 1 / Section 7).
- "Descheduler monitors communication graphs" is false in live mode until Phase 2 is done.

---

## 7. Known-defect backlog (from the audit)

| # | File | Defect | Phase |
|---|---|---|---|
| D1 | `src/rl/evaluate.py` | `ppo_model` loaded, never used; "Proposed" = greedy search on the scoring function; "KubeAI" baseline = perfect-information single-pass placement; "Load-Aware" evicts every step with no gain check and gets a comm-aware destination from `env.step` | P0, P4 |
| D2 | `src/rl/env/cluster_env.py` | obs has no comm data; `step()` oracle destination; static comm graph; reward = evaluation metric | P5 |
| D3 | `src/rl/models/ppo_descheduler.zip` | collapses to no-op under argmax; about random when sampled; critic explained variance about 0 | P5 |
| D4 | `src/descheduler/controller.py` | `rl_policy=None` and never read; creates its own empty `CommunicationGraph`; resource term ignores hypothetical moves | P2, P3 |
| D5 | `src/scheduler/scorer.py` | RL path feeds a 7-dim vector to a 42-dim model; action index treated as a score | P5 |
| D6 | `src/telemetry/aggregator.py` | `disk_io`, `node_temp` constants; nothing feeds the comm graph | P2 |
| D7 | `src/telemetry/comm_graph.py` | latency constants 0.2 / 5.0, never measured | P1, P2 |
| D8 | `scripts/setup_cluster.sh`, `manifests/kind/kind-config.yaml` | extender never wired into kube-scheduler | P3 |
| D9 | `manifests/benchmark/microservice_app.yaml` | idle `python -m http.server`, no inter-service traffic | P1 |
| D10 | `src/dashboard/app.py` | "PPO step" is a greedy search | P0 |
| D11 | docs / README | "ms" label on a unitless cost; unverified percentages | P0 |

---

## 8. Claims ledger (`CLAIMS.md` starts from this)

| Claim | Status today | Allowed wording | Evidence needed |
|---|---|---|---|
| Comm-aware descheduling cuts latency | not supported | "In a simulator with modeled latency, a greedy rule lowers modeled cost" | live p95 in S2 (G4) |
| PPO-based descheduler | not supported | "An RL attempt was made; results in Section X" | G5b |
| Outperforms KubeAI / Load-Aware | not supported | "Outperforms KubeAI-style / Load-Aware-style baselines" (once C1/C2 exist) | Phase 4 |
| Uses OpenTelemetry | not implemented | none yet | G2 |
| Uses disk I/O and node temperature | not implemented | none | remove from claims |
| Safety guards (replicas >= 2, cooldown, namespace) | code exists | "implemented" | live log |
| Extender integrated with kube-scheduler | endpoints exist | "implemented, wiring unverified" | T3.1 logs |

---

## 9. Status report (print at the end of every task)

```
TASK:            <id and name>
FILES CHANGED:   <list>
COMMANDS RUN:    <exact commands>
EVIDENCE:        <paths to saved outputs>
TESTS:           <pass / fail / not run>
NOT VERIFIED:    <everything you did not run>
DECISIONS NEEDED FROM OWNER: <list or "none">
GATE STATUS:     G1 / G2 / G3 / G4 / G5: <pass / fail / not reached>
```

---

## 10. Kickoff prompt (paste this to start)

```
Read AGENT_PLAN_AND_RULES.md fully. Do not write code yet.
Reply with: (1) the 10 rules you consider most important and why,
(2) the exact files you would touch for Phase 0, in order,
(3) anything in the plan that looks wrong, risky, or unclear.
Then wait for my approval before starting T0.1.
```
