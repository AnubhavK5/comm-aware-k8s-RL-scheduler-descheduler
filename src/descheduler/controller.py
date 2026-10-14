"""Communication-Aware Descheduler Controller."""

import time
import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from src.common.k8s_client import K8sClient
from src.telemetry.aggregator import TelemetryAggregator, ClusterSnapshot
from src.descheduler.safety import SafetyChecker
from src.common.config import (
    DESCHEDULER_INTERVAL_SECONDS,
    RESOURCE_WEIGHT,
    COMMUNICATION_WEIGHT,
    EVICTION_COST,
    CHURN_PENALTY,
    MAX_EVICTIONS_PER_CYCLE
)

logger = logging.getLogger("RLDescheduler")

class DeschedulerController:
    """Monitors running pods and reschedules pods to minimize communication distance and node imbalance."""

    def __init__(
        self,
        k8s_client: K8sClient,
        aggregator: TelemetryAggregator,
        rl_policy=None,
        interval_seconds: int = DESCHEDULER_INTERVAL_SECONDS
    ):
        self.k8s_client = k8s_client
        self.aggregator = aggregator
        self.rl_policy = rl_policy
        self.interval_seconds = interval_seconds
        self.safety_checker = SafetyChecker(k8s_client)
        self.eviction_counter = 0

    def compute_cluster_objective(self, snapshot: ClusterSnapshot, pod_locations: Dict[str, str]) -> Tuple[float, float, float]:
        """
        Computes (RUE_variance, Comm_Cost, Combined_Cost).
        Lower combined cost is better.
        """
        # 1. Resource utilization variance across worker nodes
        cpu_utils = []
        for n in snapshot.nodes:
            if not n.get("is_control_plane", False):
                util = snapshot.get_node_utilization(n["name"])
                cpu_utils.append(util["cpu_util"])

        resource_variance = float(np.var(cpu_utils)) if cpu_utils else 0.0

        # 2. Total inter-pod communication latency cost
        comm_cost = snapshot.comm_graph.calculate_total_communication_cost(pod_locations)

        combined = (RESOURCE_WEIGHT * resource_variance * 100.0) + (COMMUNICATION_WEIGHT * comm_cost)
        return resource_variance, comm_cost, combined

    def evaluate_eviction_candidates(self, snapshot: ClusterSnapshot) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        Evaluates safe candidate pods and identifies the pod whose relocation yields the highest net reward.
        Returns (victim_pod, expected_reward) or None.
        """
        safe_candidates = self.safety_checker.get_safe_eviction_candidates(snapshot.pods)
        if not safe_candidates:
            logger.info("No eligible pods pass safety checks for descheduling this cycle.")
            return None

        current_locations = dict(snapshot.pod_locations)
        _, current_comm, current_combined = self.compute_cluster_objective(snapshot, current_locations)

        worker_node_names = snapshot.node_names
        best_candidate = None
        best_reward = 0.0

        for pod in safe_candidates:
            p_name = pod["name"]
            current_node = pod.get("node_name")

            # Simulate best destination node for this pod
            best_simulated_combined = current_combined

            for target_node in worker_node_names:
                if target_node == current_node:
                    continue

                # Simulate new location
                sim_locations = dict(current_locations)
                sim_locations[p_name] = target_node
                _, _, sim_combined = self.compute_cluster_objective(snapshot, sim_locations)

                if sim_combined < best_simulated_combined:
                    best_simulated_combined = sim_combined

            # Reward = cost reduction - eviction overhead penalty
            cost_reduction = current_combined - best_simulated_combined
            net_reward = cost_reduction - EVICTION_COST

            if net_reward > best_reward:
                best_reward = net_reward
                best_candidate = pod

        if best_candidate and best_reward > 0.05:
            return best_candidate, best_reward

        return None

    def run_cycle(self) -> bool:
        """Executes a single descheduling evaluation cycle."""
        logger.info("--- Starting Descheduler Evaluation Cycle ---")
        snapshot = self.aggregator.get_cluster_snapshot(force_refresh=True)

        eviction_decision = self.evaluate_eviction_candidates(snapshot)
        if not eviction_decision:
            logger.info("Decision: No-Op (cluster placement is optimal or no candidates yield net gain).")
            return False

        victim, reward = eviction_decision
        p_name = victim["name"]
        p_ns = victim["namespace"]
        logger.info(f"Decision: Evicting pod {p_ns}/{p_name} on node {victim.get('node_name')} (Expected Net Gain: {reward:.4f})")

        success = self.k8s_client.evict_pod(pod_name=p_name, namespace=p_ns)
        if success:
            self.safety_checker.mark_evicted(victim)
            self.eviction_counter += 1
            return True
        return False

    def start_loop(self, max_cycles: Optional[int] = None):
        """Runs the descheduling daemon periodically."""
        logger.info(f"Starting Descheduler loop with {self.interval_seconds}s interval.")
        cycles = 0
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"Error in descheduler cycle: {e}", exc_info=True)

            cycles += 1
            if max_cycles and cycles >= max_cycles:
                logger.info(f"Completed {max_cycles} descheduling cycles.")
                break

            time.sleep(self.interval_seconds)

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    k8s = K8sClient()
    agg = TelemetryAggregator(k8s)
    controller = DeschedulerController(k8s_client=k8s, aggregator=agg)
    controller.start_loop()

if __name__ == "__main__":
    main()
