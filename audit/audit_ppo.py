import numpy as np, collections
from src.rl.env.cluster_env import K8sClusterEnv
from np_policy import NPPolicy

pol = NPPolicy("src/rl/models/ppo_descheduler.zip")
N = 300


def make_env():
    # exactly the settings used in src/rl/train.py
    return K8sClusterEnv(num_nodes=3, num_pods=12, max_steps=40,
                         resource_weight=0.5, comm_weight=0.5, eviction_cost=0.3)


def greedy_action(env):
    """Evict the single pod whose best relocation gives the biggest cost drop (if > eviction cost)."""
    _, _, cur = env._compute_cost(env.pod_nodes)
    best, act = 0.0, 0
    for p in range(env.num_pods):
        for t in range(env.num_nodes):
            if t == env.pod_nodes[p]:
                continue
            s = env.pod_nodes.copy(); s[p] = t
            g = cur - env._compute_cost(s)[2]
            if g > best and g > env.eviction_cost:
                best, act = g, p + 1
    return act


def rollout(policy_name, seed, comm_drift=False):
    env = make_env()
    obs, _ = env.reset(seed=seed)
    rng = np.random.default_rng(seed + 777)
    total_r, ev, acts = 0.0, 0, []
    for step in range(env.max_steps):
        if comm_drift and step == 15:
            m = np.zeros_like(env.comm_matrix)
            for i in range(env.num_pods):
                for j in range(i + 1, env.num_pods):
                    if rng.random() < 0.35:
                        m[i, j] = m[j, i] = rng.uniform(20, 100)
            env.comm_matrix = m
        if policy_name == "noop":
            a = 0
        elif policy_name == "random":
            a = int(rng.integers(0, env.num_pods + 1))
        elif policy_name == "ppo":            # deterministic (argmax) - what predict(deterministic=True) does
            a, _ = pol.act(obs)
        elif policy_name == "ppo_sampled":    # sampled from the softmax - what PPO does during training
            _, lg = pol.act(obs); p = np.exp(lg - lg.max()); p /= p.sum()
            a = int(rng.choice(len(p), p=p))
        elif policy_name == "greedy":
            a = greedy_action(env)
        obs, r, term, trunc, info = env.step(a)
        total_r += r; ev += int(info["evicted"]); acts.append(a)
    return total_r, env._compute_cost(env.pod_nodes)[2], ev, acts


def summarize(name, comm_drift=False):
    R, C, E, A = [], [], [], []
    for s in range(N):
        r, c, e, a = rollout(name, 50_000 + s, comm_drift)
        R.append(r); C.append(c); E.append(e); A += a
    return np.array(R), np.array(C), np.array(E), A


print(f"{'policy':<8} {'episode reward':>18} {'final cost':>14} {'evictions/ep':>13}")
res = {}
for name in ["noop", "random", "ppo", "ppo_sampled", "greedy"]:
    R, C, E, A = summarize(name)
    res[name] = (R, C, E, A)
    print(f"{name:<8} {R.mean():>10.2f} (+/-{R.std()/np.sqrt(N):.2f}) {C.mean():>8.2f} (+/-{C.std()/np.sqrt(N):.2f}) {E.mean():>8.1f}")

# paired comparison on identical seeds
for a, b in [("ppo", "noop"), ("ppo", "random"), ("greedy", "ppo"), ("random", "greedy")]:
    d = res[b][1] - res[a][1]      # positive => first policy has LOWER final cost
    print(f"paired final-cost gain  {a:>6} vs {b:<6}: {d.mean():+.3f}  (95% CI +/- {1.96*d.std()/np.sqrt(N):.3f})")

cnt = collections.Counter(res["ppo"][3])
print("\nPPO action histogram over all steps (0 = no-op, k = evict pod k-1):")
tot = sum(cnt.values())
for k in sorted(cnt):
    print(f"  action {k:>2}: {cnt[k]/tot*100:5.1f}%")
