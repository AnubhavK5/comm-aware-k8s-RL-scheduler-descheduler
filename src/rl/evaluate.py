"""Comprehensive comparative evaluation script: benchmarks across dynamic workload drift."""

import logging
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
try:
    from stable_baselines3 import PPO
except ImportError:
    PPO = None

from src.rl.env.cluster_env import K8sClusterEnv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Evaluator")

class ModelCountingProxy:
    """Wraps an RL policy model and counts calls to predict()."""
    def __init__(self, model):
        self._model = model
        self.call_count = 0

    def predict(self, *args, **kwargs):
        self.call_count += 1
        if self._model is not None:
            return self._model.predict(*args, **kwargs)
        raise RuntimeError("Predict called on None model proxy")

    def __getattr__(self, name):
        return getattr(self._model, name)

def run_simulation_benchmark(episodes: int = 50, model_override: Optional[Any] = None) -> Dict[str, Dict[str, Any]]:
    """
    Evaluates 4 configurations in an analytical simulation environment:
    1. Default Kubernetes Scheduler (static placement, no descheduling)
    2. Load-Aware-style Descheduler (heuristic resource balance, unconstrained eviction strawman)
    3. KubeAI-style (oracle placement, simulator with static CPU drift)
    4. Proposed Greedy Heuristic (comm-aware scheduler + greedy exhaustive descheduler)
    """
    env = K8sClusterEnv(num_nodes=3, num_pods=12, max_steps=40)
    model_path = "src/rl/models/ppo_descheduler.zip"

    if model_override is not None:
        raw_model = model_override
    elif PPO is not None:
        try:
            raw_model = PPO.load(model_path, env=env)
            logger.info(f"Loaded trained PPO model from {model_path}")
        except Exception as e:
            logger.warning(f"Could not load PPO model ({e})")
            raw_model = None
    else:
        logger.warning("stable_baselines3 not installed; PPO model loading skipped.")
        raw_model = None

    proxy_model = ModelCountingProxy(raw_model)

    results = {
        "Default Scheduler": {"res_variance": [], "comm_latency": [], "combined_cost": [], "evictions": [], "uses_model": False, "calls_model_predict": False, "model_call_count": 0},
        "Load-Aware-style (Heuristic)": {"res_variance": [], "comm_latency": [], "combined_cost": [], "evictions": [], "uses_model": False, "calls_model_predict": False, "model_call_count": 0},
        "Static-Oracle (Placement-Only Heuristic)": {"res_variance": [], "comm_latency": [], "combined_cost": [], "evictions": [], "uses_model": False, "calls_model_predict": False, "model_call_count": 0},
        "Proposed Greedy Heuristic (Sched+Desched)": {"res_variance": [], "comm_latency": [], "combined_cost": [], "evictions": [], "uses_model": False, "calls_model_predict": False, "model_call_count": 0},
    }

    for ep in range(episodes):
        seed = 2000 + ep

        # --- 1. Default Scheduler (Static placement, no movement) ---
        obs, _ = env.reset(seed=seed)
        for _ in range(env.max_steps):
            obs, _, term, trunc, _ = env.step(0)
            if term or trunc:
                break
        res_var, comm_cost, comb = env._compute_cost(env.pod_nodes)
        results["Default Scheduler"]["res_variance"].append(res_var)
        results["Default Scheduler"]["comm_latency"].append(comm_cost)
        results["Default Scheduler"]["combined_cost"].append(comb)
        results["Default Scheduler"]["evictions"].append(0)

        # --- 2. Load-Aware Heuristic Descheduler (Evicts solely for node load balance, ignoring communication) ---
        obs, _ = env.reset(seed=seed)
        evictions = 0
        for _ in range(env.max_steps):
            node_cpu = np.zeros(env.num_nodes)
            for p in range(env.num_pods):
                node_cpu[env.pod_nodes[p]] += env.pod_cpu_req[p]
            max_node = np.argmax(node_cpu)
            candidates = [p for p in range(env.num_pods) if env.pod_nodes[p] == max_node]
            if candidates and np.var(node_cpu) > 0.08:
                action = candidates[0] + 1
                evictions += 1
            else:
                action = 0
            obs, _, term, trunc, _ = env.step(action)
            if term or trunc:
                break
        res_var, comm_cost, comb = env._compute_cost(env.pod_nodes)
        results["Load-Aware-style (Heuristic)"]["res_variance"].append(res_var)
        results["Load-Aware-style (Heuristic)"]["comm_latency"].append(comm_cost)
        results["Load-Aware-style (Heuristic)"]["combined_cost"].append(comb)
        results["Load-Aware-style (Heuristic)"]["evictions"].append(evictions)

        # --- 3. KubeAI-style (oracle placement, simulator with static CPU drift) ---
        obs, _ = env.reset(seed=seed)
        # Optimal communication-aware initial placement
        for p in range(env.num_pods):
            best_node = 0
            best_c = float("inf")
            for n in range(env.num_nodes):
                env.pod_nodes[p] = n
                _, _, c = env._compute_cost(env.pod_nodes)
                if c < best_c:
                    best_c = c
                    best_node = n
            env.pod_nodes[p] = best_node
        # Simulating drift during runtime (e.g. background traffic or pod load shifts)
        for step in range(env.max_steps):
            if step == 15:
                # Mid-run drift: pod demands change dynamically
                env.pod_cpu_req = np.roll(env.pod_cpu_req, 3)
            obs, _, term, trunc, _ = env.step(0)
            if term or trunc:
                break
        res_var, comm_cost, comb = env._compute_cost(env.pod_nodes)
        results["Static-Oracle (Placement-Only Heuristic)"]["res_variance"].append(res_var)
        results["Static-Oracle (Placement-Only Heuristic)"]["comm_latency"].append(comm_cost)
        results["Static-Oracle (Placement-Only Heuristic)"]["combined_cost"].append(comb)
        results["Static-Oracle (Placement-Only Heuristic)"]["evictions"].append(0)

        # --- 4. Proposed Greedy Heuristic (Comm-Aware Sched + Desched) ---
        obs, _ = env.reset(seed=seed)
        # 4a. Initial placement via Communication-Aware Extender
        for p in range(env.num_pods):
            best_node = 0
            best_c = float("inf")
            for n in range(env.num_nodes):
                env.pod_nodes[p] = n
                _, _, c = env._compute_cost(env.pod_nodes)
                if c < best_c:
                    best_c = c
                    best_node = n
            env.pod_nodes[p] = best_node

        evictions = 0
        for step in range(env.max_steps):
            if step == 15:
                # Same mid-run drift
                env.pod_cpu_req = np.roll(env.pod_cpu_req, 3)

            # Controller evaluates victim with greedy heuristic scoring (note: ppo_model is NOT queried)
            safe_action = 0
            best_improvement = 0.0
            _, _, current_cost = env._compute_cost(env.pod_nodes)

            for cand_p in range(env.num_pods):
                current_node = env.pod_nodes[cand_p]
                for target_node in range(env.num_nodes):
                    if target_node == current_node:
                        continue
                    sim_nodes = env.pod_nodes.copy()
                    sim_nodes[cand_p] = target_node
                    _, _, sim_c = env._compute_cost(sim_nodes)
                    gain = current_cost - sim_c
                    if gain > best_improvement and gain > env.eviction_cost + 0.1:
                        best_improvement = gain
                        safe_action = cand_p + 1

            if safe_action > 0 and evictions < 5:
                evictions += 1
                action = safe_action
            else:
                action = 0

            obs, _, term, trunc, _ = env.step(action)
            if term or trunc:
                break

        res_var, comm_cost, comb = env._compute_cost(env.pod_nodes)
        results["Proposed Greedy Heuristic (Sched+Desched)"]["res_variance"].append(res_var)
        results["Proposed Greedy Heuristic (Sched+Desched)"]["comm_latency"].append(comm_cost)
        results["Proposed Greedy Heuristic (Sched+Desched)"]["combined_cost"].append(comb)
        results["Proposed Greedy Heuristic (Sched+Desched)"]["evictions"].append(evictions)

    # Set calls_model_predict and model_call_count dynamically from the counting proxy
    for cfg_name, cfg_data in results.items():
        if cfg_data.get("uses_model", False):
            cfg_data["model_call_count"] = proxy_model.call_count
            cfg_data["calls_model_predict"] = proxy_model.call_count > 0
        else:
            cfg_data["model_call_count"] = 0
            cfg_data["calls_model_predict"] = False

    print("\n" + "="*88)
    print(f"{'Configuration':<45} | {'Resource Var':<12} | {'Comm Cost':<12} | {'Total Cost':<10} | {'Evictions':<9}")
    print("="*88)
    for name, m in results.items():
        mean_var = float(np.mean(m["res_variance"]))
        mean_lat = float(np.mean(m["comm_latency"]))
        mean_cost = float(np.mean(m["combined_cost"]))
        mean_ev = float(np.mean(m["evictions"]))
        print(f"{name:<45} | {mean_var:<12.4f} | {mean_lat:<12.2f} | {mean_cost:<10.4f} | {mean_ev:<9.1f}")
    print("="*88 + "\n")

    return results

if __name__ == "__main__":
    run_simulation_benchmark(episodes=40)
