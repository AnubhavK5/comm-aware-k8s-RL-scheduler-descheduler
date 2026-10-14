"""Gymnasium Environment for Kubernetes Communication-Aware Descheduling."""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

class K8sClusterEnv(gym.Env):
    """
    Simulated Gymnasium environment for training PPO descheduling policy.
    Simulates a multi-node Kubernetes cluster with interdependent microservices.
    """
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        num_nodes: int = 3,
        num_pods: int = 12,
        node_cpu_capacity: float = 4.0,
        node_mem_capacity: float = 8.0,
        inter_node_latency_ms: float = 5.0,
        intra_node_latency_ms: float = 0.2,
        eviction_cost: float = 0.15,
        resource_weight: float = 0.5,
        comm_weight: float = 0.5,
        max_steps: int = 30
    ):
        super().__init__()
        self.num_nodes = num_nodes
        self.num_pods = num_pods
        self.node_cpu_capacity = node_cpu_capacity
        self.node_mem_capacity = node_mem_capacity
        self.inter_node_latency_ms = inter_node_latency_ms
        self.intra_node_latency_ms = intra_node_latency_ms
        self.eviction_cost = eviction_cost
        self.resource_weight = resource_weight
        self.comm_weight = comm_weight
        self.max_steps = max_steps
        self.current_step = 0

        # Action: 0 = No-Op, 1..num_pods = Evict pod (i - 1)
        self.action_space = spaces.Discrete(self.num_pods + 1)

        # Observation dimension:
        # [num_nodes * 2 (cpu_util, mem_util), num_pods (normalized node_idx), num_pods * 2 (cpu, mem req)]
        obs_dim = (self.num_nodes * 2) + self.num_pods + (self.num_pods * 2)
        self.observation_space = spaces.Box(
            low=0.0,
            high=5.0,
            shape=(obs_dim,),
            dtype=np.float32
        )

        self.pod_nodes = np.zeros(self.num_pods, dtype=np.int32)
        self.pod_cpu_req = np.zeros(self.num_pods, dtype=np.float32)
        self.pod_mem_req = np.zeros(self.num_pods, dtype=np.float32)
        self.comm_matrix = np.zeros((self.num_pods, self.num_pods), dtype=np.float32)
        self.last_evicted_step = np.full(self.num_pods, -100, dtype=np.int32)

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        self.current_step = 0

        # Generate realistic pod demands
        self.pod_cpu_req = self.np_random.uniform(0.2, 0.8, size=self.num_pods).astype(np.float32)
        self.pod_mem_req = self.np_random.uniform(0.5, 1.5, size=self.num_pods).astype(np.float32)

        # Generate communication graph
        self.comm_matrix = np.zeros((self.num_pods, self.num_pods), dtype=np.float32)
        for i in range(self.num_pods):
            for j in range(i + 1, self.num_pods):
                if self.np_random.random() < 0.35:
                    calls = self.np_random.uniform(20.0, 100.0)
                    self.comm_matrix[i, j] = calls
                    self.comm_matrix[j, i] = calls

        # Initially assign pods arbitrarily or clustered on node 0 (simulating imbalance & distance)
        self.pod_nodes = self.np_random.integers(0, self.num_nodes, size=self.num_pods, dtype=np.int32)
        self.last_evicted_step = np.full(self.num_pods, -100, dtype=np.int32)

        return self._get_obs(), {}

    def _get_obs(self) -> np.ndarray:
        node_cpu = np.zeros(self.num_nodes, dtype=np.float32)
        node_mem = np.zeros(self.num_nodes, dtype=np.float32)
        for p in range(self.num_pods):
            node_idx = self.pod_nodes[p]
            node_cpu[node_idx] += self.pod_cpu_req[p]
            node_mem[node_idx] += self.pod_mem_req[p]

        node_cpu_util = np.clip(node_cpu / self.node_cpu_capacity, 0.0, 2.0)
        node_mem_util = np.clip(node_mem / self.node_mem_capacity, 0.0, 2.0)
        norm_pod_nodes = self.pod_nodes.astype(np.float32) / max(1, self.num_nodes - 1)

        obs = np.concatenate([
            node_cpu_util,
            node_mem_util,
            norm_pod_nodes,
            self.pod_cpu_req,
            self.pod_mem_req
        ])
        return obs.astype(np.float32)

    def _compute_cost(self, pod_placements: np.ndarray) -> Tuple[float, float, float]:
        node_cpu = np.zeros(self.num_nodes, dtype=np.float32)
        for p in range(self.num_pods):
            node_cpu[pod_placements[p]] += self.pod_cpu_req[p]
        res_variance = float(np.var(node_cpu))

        comm_cost = 0.0
        for i in range(self.num_pods):
            for j in range(i + 1, self.num_pods):
                if self.comm_matrix[i, j] > 0:
                    lat = self.intra_node_latency_ms if pod_placements[i] == pod_placements[j] else self.inter_node_latency_ms
                    comm_cost += self.comm_matrix[i, j] * lat

        combined = (self.resource_weight * res_variance * 10.0) + (self.comm_weight * (comm_cost / 100.0))
        return res_variance, comm_cost, combined

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, dict]:
        self.current_step += 1
        _, _, cost_before = self._compute_cost(self.pod_nodes)

        evicted = False
        action_penalty = 0.0

        if action > 0:
            pod_idx = action - 1
            evicted = True
            current_node = self.pod_nodes[pod_idx]

            # Churn penalty for quick repeated evictions of same pod
            churn_steps = self.current_step - self.last_evicted_step[pod_idx]
            churn_penalty = 0.5 if churn_steps < 3 else 0.0

            # Communication-aware relocation: test all target nodes and place on lowest cost node
            best_target_node = current_node
            best_cost = cost_before

            for target_node in range(self.num_nodes):
                if target_node == current_node:
                    continue
                test_placements = self.pod_nodes.copy()
                test_placements[pod_idx] = target_node
                _, _, test_cost = self._compute_cost(test_placements)
                if test_cost < best_cost:
                    best_cost = test_cost
                    best_target_node = target_node

            self.pod_nodes[pod_idx] = best_target_node
            self.last_evicted_step[pod_idx] = self.current_step
            action_penalty = self.eviction_cost + churn_penalty

        _, _, cost_after = self._compute_cost(self.pod_nodes)

        # Immediate improvement reward + ongoing state quality reward
        improvement = (cost_before - cost_after)
        step_reward = improvement - action_penalty - (cost_after / 50.0)

        terminated = self.current_step >= self.max_steps
        truncated = False
        info = {"evicted": evicted, "action": action, "cost": cost_after}

        return self._get_obs(), float(step_reward), terminated, truncated, info
