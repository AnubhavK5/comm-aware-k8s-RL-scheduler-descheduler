"""Control experiments on the project's own simulator (no PPO involved).

Q1: Do the README gains come from handling drift, or from simply running more
    optimisation steps on the same objective that is also used for scoring?
Q2: What happens if the *communication graph* drifts (the paper's actual claim)?
"""
import numpy as np
from src.rl.env.cluster_env import K8sClusterEnv

N_EP = 200


def greedy_initial_placement(env):
    """Exact replica of evaluate.py: one sequential pass, other pods at random positions."""
    for p in range(env.num_pods):
        best_node, best_c = 0, float("inf")
        for n in range(env.num_nodes):
            env.pod_nodes[p] = n
            _, _, c = env._compute_cost(env.pod_nodes)
            if c < best_c:
                best_c, best_node = c, n
        env.pod_nodes[p] = best_node


def greedy_descheduler_step(env, max_moves_left):
    """Exact replica of the 'Proposed' decision rule in evaluate.py."""
    best_improvement, action = 0.0, 0
    _, _, cur = env._compute_cost(env.pod_nodes)
    for p in range(env.num_pods):
        for t in range(env.num_nodes):
            if t == env.pod_nodes[p]:
                continue
            sim = env.pod_nodes.copy()
            sim[p] = t
            _, _, c = env._compute_cost(sim)
            gain = cur - c
            if gain > best_improvement and gain > env.eviction_cost + 0.1:
                best_improvement, action = gain, p + 1
    return action if (action > 0 and max_moves_left > 0) else 0


def run(mode, drift_cpu=True, drift_comm=False, seeds=range(N_EP)):
    env = K8sClusterEnv(num_nodes=3, num_pods=12, max_steps=40)
    costs, evs = [], []
    for s in seeds:
        env.reset(seed=2000 + s)
        greedy_initial_placement(env)
        if mode == "extra_sweep":          # KubeAI placement + one more sweep, NO descheduler
            greedy_initial_placement(env)
        ev = 0
        for step in range(env.max_steps):
            if step == 15:
                if drift_cpu:
                    env.pod_cpu_req = np.roll(env.pod_cpu_req, 3)
                if drift_comm:             # traffic pattern actually changes
                    rng = np.random.default_rng(10_000 + s)
                    m = np.zeros_like(env.comm_matrix)
                    for i in range(env.num_pods):
                        for j in range(i + 1, env.num_pods):
                            if rng.random() < 0.35:
                                m[i, j] = m[j, i] = rng.uniform(20, 100)
                    env.comm_matrix = m
            a = 0
            if mode == "proposed":
                a = greedy_descheduler_step(env, 5 - ev)
                ev += int(a > 0)
            env.step(a)
        costs.append(env._compute_cost(env.pod_nodes)[2])
        evs.append(ev)
    return float(np.mean(costs)), float(np.std(costs) / np.sqrt(len(costs))), float(np.mean(evs))


def row(label, r):
    print(f"  {label:<46} cost={r[0]:7.3f} (+/-{r[1]:.2f})  evictions={r[2]:.1f}")


print("=== Q1. Same simulator, same drift as README (CPU demands shift at step 15) ===")
row("KubeAI placement only",                        run("kubeai"))
row("KubeAI placement + ONE EXTRA placement sweep", run("extra_sweep"))
row("Proposed (greedy descheduler, <=5 moves)",     run("proposed"))

print("\n=== Q1b. NO drift at all (nothing for a descheduler to 'adapt' to) ===")
row("KubeAI placement only",                        run("kubeai", drift_cpu=False))
row("KubeAI placement + ONE EXTRA placement sweep", run("extra_sweep", drift_cpu=False))
row("Proposed (greedy descheduler, <=5 moves)",     run("proposed", drift_cpu=False))

print("\n=== Q2. Communication graph ALSO drifts at step 15 (the paper's real claim) ===")
row("KubeAI placement only",                        run("kubeai", drift_comm=True))
row("Proposed (greedy descheduler, <=5 moves)",     run("proposed", drift_comm=True))
