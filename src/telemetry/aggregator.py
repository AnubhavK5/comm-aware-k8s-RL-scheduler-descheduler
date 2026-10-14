"""Telemetry Aggregator: merges infrastructure and service-level metrics."""

import logging
import time
from typing import Dict, List, Any, Optional
import numpy as np

from src.common.k8s_client import K8sClient
from src.telemetry.comm_graph import CommunicationGraph
from src.common.config import NODE_FEATURE_DIM

logger = logging.getLogger(__name__)

class ClusterSnapshot:
    """Represents the global cluster state at a given evaluation timestamp."""
    def __init__(
        self,
        nodes: List[Dict[str, Any]],
        pods: List[Dict[str, Any]],
        node_metrics: Dict[str, Dict[str, float]],
        pod_metrics: Dict[str, Dict[str, float]],
        comm_graph: CommunicationGraph,
        timestamp: float
    ):
        self.nodes = nodes
        self.pods = pods
        self.node_metrics = node_metrics
        self.pod_metrics = pod_metrics
        self.comm_graph = comm_graph
        self.timestamp = timestamp

        # Precompute mappings
        self.node_names = [n["name"] for n in self.nodes if not n.get("is_control_plane", False)]
        self.node_index = {name: i for i, name in enumerate(self.node_names)}
        self.pod_locations = {p["name"]: p["node_name"] for p in self.pods if p.get("node_name")}

    def get_node_utilization(self, node_name: str) -> Dict[str, float]:
        """Returns normalized CPU and memory utilization (0.0 - 1.0)."""
        metrics = self.node_metrics.get(node_name, {})
        node_spec = next((n for n in self.nodes if n["name"] == node_name), None)

        if not node_spec:
            return {"cpu_util": 0.0, "mem_util": 0.0}

        alloc_cpu = node_spec.get("cpu_allocatable_cores", 1.0)
        alloc_mem = node_spec.get("mem_allocatable_bytes", 1.0)

        used_cpu = metrics.get("cpu_usage_cores", 0.0)
        used_mem = metrics.get("mem_usage_bytes", 0.0)

        cpu_util = min(1.0, used_cpu / max(alloc_cpu, 0.001))
        mem_util = min(1.0, used_mem / max(alloc_mem, 1024))
        return {"cpu_util": cpu_util, "mem_util": mem_util}

    def compute_state_vector(self, pod_name: str, candidate_node: str, req_cpu: float = 0.1, req_mem_bytes: float = 128 * 1024 * 1024) -> np.ndarray:
        """
        Constructs the 7D state vector from Synopsis Eq. 4.1:
        s = [cpu_eff, mem_eff, node_cpu, node_mem, disk_io, net_lat, node_temp]
        """
        node_spec = next((n for n in self.nodes if n["name"] == candidate_node), None)
        alloc_cpu = node_spec.get("cpu_allocatable_cores", 1.0) if node_spec else 1.0
        alloc_mem = node_spec.get("mem_allocatable_bytes", 1024**3) if node_spec else 1024**3

        node_util = self.get_node_utilization(candidate_node)
        node_cpu = node_util["cpu_util"]
        node_mem = node_util["mem_util"]

        # Resource efficiency terms (projected balance if placed here)
        cpu_eff = 1.0 - abs(node_cpu + (req_cpu / max(alloc_cpu, 0.01)) - 0.5)
        mem_eff = 1.0 - abs(node_mem + (req_mem_bytes / max(alloc_mem, 1024)) - 0.5)

        # Telemetry proxy / metrics for disk_io, net_lat, node_temp
        disk_io = 0.1  # normalized disk IO
        # Network latency to peers of pod_name
        affinity_cost = self.comm_graph.calculate_communication_affinity(
            target_pod=pod_name,
            candidate_node=candidate_node,
            pod_locations=self.pod_locations
        )
        # Invert affinity to represent network latency/overhead (0.0 = low latency, 1.0 = high)
        net_lat = max(0.0, 1.0 / (1.0 + affinity_cost))
        node_temp = 0.35  # normalized temperature proxy (35-45C)

        state = np.array([cpu_eff, mem_eff, node_cpu, node_mem, disk_io, net_lat, node_temp], dtype=np.float32)
        return state

class TelemetryAggregator:
    def __init__(self, k8s_client: K8sClient, comm_graph: Optional[CommunicationGraph] = None):
        self.k8s_client = k8s_client
        self.comm_graph = comm_graph or CommunicationGraph()
        self._last_snapshot: Optional[ClusterSnapshot] = None
        self._cache_time = 0.0
        self.cache_ttl_seconds = 2.0

    def get_cluster_snapshot(self, force_refresh: bool = False) -> ClusterSnapshot:
        """Fetches and caches live cluster snapshot."""
        now = time.time()
        if not force_refresh and self._last_snapshot and (now - self._cache_time < self.cache_ttl_seconds):
            return self._last_snapshot

        nodes = self.k8s_client.get_nodes()
        pods = self.k8s_client.get_pods()
        node_metrics = self.k8s_client.get_node_metrics()
        pod_metrics = self.k8s_client.get_pod_metrics()

        # Decay stale communication records
        self.comm_graph.decay_old_metrics()

        snapshot = ClusterSnapshot(
            nodes=nodes,
            pods=pods,
            node_metrics=node_metrics,
            pod_metrics=pod_metrics,
            comm_graph=self.comm_graph,
            timestamp=now
        )
        self._last_snapshot = snapshot
        self._cache_time = now
        return snapshot
