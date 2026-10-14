"""Service-level communication graph and affinity tracker."""

import time
import logging
from typing import Dict, Tuple, Set, Optional, Any
import numpy as np

logger = logging.getLogger(__name__)

class CommunicationGraph:
    """Tracks inter-pod communication frequency, payload bytes, and network latency."""

    def __init__(self, intra_node_latency_ms: float = 0.2, inter_node_latency_ms: float = 5.0):
        self.intra_node_latency_ms = intra_node_latency_ms
        self.inter_node_latency_ms = inter_node_latency_ms
        # Edge storage: (src_pod, dst_pod) -> {"calls": int, "bytes": float, "last_updated": float}
        self.edges: Dict[Tuple[str, str], Dict[str, Any]] = {}
        # Node-to-node simulated/measured RTT latency matrix: (node_A, node_B) -> ms
        self.node_latency_matrix: Dict[Tuple[str, str], float] = {}

    def set_node_latency(self, node_a: str, node_b: str, latency_ms: float):
        """Set measured round-trip time between two nodes."""
        self.node_latency_matrix[(node_a, node_b)] = latency_ms
        self.node_latency_matrix[(node_b, node_a)] = latency_ms

    def get_node_latency(self, node_a: str, node_b: str) -> float:
        """Get latency between two nodes in milliseconds."""
        if not node_a or not node_b:
            return self.inter_node_latency_ms
        if node_a == node_b:
            return self.intra_node_latency_ms
        return self.node_latency_matrix.get((node_a, node_b), self.inter_node_latency_ms)

    def record_communication(self, src_pod: str, dst_pod: str, bytes_transferred: float = 1024.0, count: int = 1):
        """Record an observed communication exchange between two pods."""
        if src_pod == dst_pod:
            return
        key = (src_pod, dst_pod)
        now = time.time()
        if key not in self.edges:
            self.edges[key] = {"calls": 0, "bytes": 0.0, "last_updated": now}
        self.edges[key]["calls"] += count
        self.edges[key]["bytes"] += bytes_transferred
        self.edges[key]["last_updated"] = now

    def decay_old_metrics(self, max_age_seconds: float = 300.0, decay_factor: float = 0.8):
        """Exponential decay for call counts to prioritize recent telemetry."""
        now = time.time()
        stale_keys = []
        for key, data in self.edges.items():
            if now - data["last_updated"] > max_age_seconds:
                stale_keys.append(key)
            else:
                data["calls"] = int(data["calls"] * decay_factor)
                data["bytes"] = data["bytes"] * decay_factor
        for key in stale_keys:
            del self.edges[key]

    def get_pod_communication_partners(self, pod_name: str) -> Dict[str, Dict[str, Any]]:
        """Return all pods communicating with pod_name."""
        partners = {}
        for (src, dst), stats in self.edges.items():
            if src == pod_name:
                partners[dst] = stats
            elif dst == pod_name:
                partners[src] = stats
        return partners

    def calculate_communication_affinity(self, target_pod: str, candidate_node: str, pod_locations: Dict[str, str]) -> float:
        """Calculate communication affinity score for placing target_pod on candidate_node."""
        affinity = 0.0
        for (src, dst), stats in self.edges.items():
            other_pod = None
            if src == target_pod:
                other_pod = dst
            elif dst == target_pod:
                other_pod = src

            if other_pod and other_pod in pod_locations:
                other_node = pod_locations[other_pod]
                latency = self.get_node_latency(candidate_node, other_node)
                # Higher frequency and lower latency yields higher affinity score
                traffic_weight = np.log1p(stats["calls"]) + (stats["bytes"] / 1024.0)
                affinity += traffic_weight / max(0.1, latency)
        return float(affinity)

    def calculate_total_communication_cost(self, pod_locations: Dict[str, str]) -> float:
        """Compute aggregate cluster communication latency weighted by traffic volume."""
        total_cost = 0.0
        for (src, dst), stats in self.edges.items():
            if src in pod_locations and dst in pod_locations:
                node_src = pod_locations[src]
                node_dst = pod_locations[dst]
                latency = self.get_node_latency(node_src, node_dst)
                total_cost += stats["calls"] * latency
        return total_cost
