"""Node scoring engine for Scheduler Extender."""

import logging
from typing import Dict, List, Any, Optional
import numpy as np

from src.telemetry.aggregator import ClusterSnapshot
from src.common.config import RESOURCE_WEIGHT, COMMUNICATION_WEIGHT

logger = logging.getLogger(__name__)

class NodeScorer:
    """Computes placement priority scores combining resource balance and communication affinity."""

    def __init__(self, resource_weight: float = RESOURCE_WEIGHT, comm_weight: float = COMMUNICATION_WEIGHT):
        self.resource_weight = resource_weight
        self.comm_weight = comm_weight
        self.rl_policy = None  # Loaded PPO policy model if present

    def set_rl_policy(self, policy):
        """Set a trained RL policy for scoring."""
        self.rl_policy = policy

    def score_candidate_nodes(self, pod_name: str, candidate_nodes: List[str], snapshot: ClusterSnapshot) -> List[Dict[str, Any]]:
        """
        Calculates priority scores for candidate nodes.
        Returns a list of dicts: [{"Host": node_name, "Score": int(0..100)}]
        """
        scores = []
        raw_scores = {}

        for node_name in candidate_nodes:
            state_vec = snapshot.compute_state_vector(pod_name=pod_name, candidate_node=node_name)

            if self.rl_policy is not None:
                # Use RL policy action-value / Q-value prediction
                try:
                    action, _ = self.rl_policy.predict(state_vec, deterministic=True)
                    score_val = float(action)
                except Exception as e:
                    logger.warning(f"RL policy prediction failed, fallback to heuristic: {e}")
                    score_val = self._compute_heuristic_score(state_vec, pod_name, node_name, snapshot)
            else:
                score_val = self._compute_heuristic_score(state_vec, pod_name, node_name, snapshot)

            raw_scores[node_name] = score_val

        # Normalize raw scores to integer range [0, 100] as expected by kube-scheduler
        min_s = min(raw_scores.values()) if raw_scores else 0.0
        max_s = max(raw_scores.values()) if raw_scores else 1.0
        s_range = max(1e-5, max_s - min_s)

        for node_name in candidate_nodes:
            normalized = int(((raw_scores[node_name] - min_s) / s_range) * 100.0)
            scores.append({
                "Host": node_name,
                "Score": max(0, min(100, normalized))
            })

        logger.info(f"Scored {len(candidate_nodes)} nodes for pod {pod_name}: {scores}")
        return scores

    def _compute_heuristic_score(self, state_vec: np.ndarray, pod_name: str, node_name: str, snapshot: ClusterSnapshot) -> float:
        """
        Heuristic formula combining resource efficiency and communication affinity (KubeAI Eq. 4.1):
        s = [cpu_eff, mem_eff, node_cpu, node_mem, disk_io, net_lat, node_temp]
        """
        cpu_eff = state_vec[0]
        mem_eff = state_vec[1]
        net_lat = state_vec[5]

        # Resource efficiency term
        resource_score = (cpu_eff + mem_eff) / 2.0

        # Communication affinity term (lower net_lat means higher affinity)
        comm_score = 1.0 - net_lat

        combined = (self.resource_weight * resource_score) + (self.comm_weight * comm_score)
        return float(combined)
