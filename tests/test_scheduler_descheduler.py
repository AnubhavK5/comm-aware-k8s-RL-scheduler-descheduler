"""Unit and integration tests for RL Scheduler & Descheduler."""

import pytest
import numpy as np

from src.telemetry.comm_graph import CommunicationGraph
from src.scheduler.scorer import NodeScorer
from src.rl.env.cluster_env import K8sClusterEnv
from src.common.k8s_client import K8sClient

def test_communication_graph():
    graph = CommunicationGraph(intra_node_latency_ms=0.2, inter_node_latency_ms=5.0)
    graph.record_communication("podA", "podB", count=50, bytes_transferred=10240)

    # Co-located affinity test
    locations = {"podA": "worker1", "podB": "worker1"}
    aff_colocated = graph.calculate_communication_affinity("podA", "worker1", locations)

    # Remote node affinity test
    aff_remote = graph.calculate_communication_affinity("podA", "worker2", locations)

    assert aff_colocated > aff_remote, "Affinity for co-located candidate node must be higher than remote node"

def test_node_scorer_heuristic():
    scorer = NodeScorer(resource_weight=0.5, comm_weight=0.5)

    # State vector: [cpu_eff, mem_eff, node_cpu, node_mem, disk_io, net_lat, node_temp]
    state_good = np.array([0.9, 0.9, 0.4, 0.4, 0.1, 0.1, 0.35], dtype=np.float32)
    state_bad = np.array([0.2, 0.2, 0.9, 0.9, 0.8, 0.9, 0.7], dtype=np.float32)

    score_good = scorer._compute_heuristic_score(state_good, "podA", "worker1", None)
    score_bad = scorer._compute_heuristic_score(state_bad, "podA", "worker2", None)

    assert score_good > score_bad, "Favorable node state must yield higher score than overloaded/distant node"

def test_k8s_cluster_gym_env():
    env = K8sClusterEnv(num_nodes=3, num_pods=6, max_steps=10)
    obs, info = env.reset(seed=42)

    assert obs.shape == env.observation_space.shape
    assert len(env.pod_nodes) == 6

    # Test step with No-Op
    next_obs, reward, term, trunc, info = env.step(0)
    assert not info["evicted"]
    assert not term

    # Test step with eviction
    next_obs, reward, term, trunc, info = env.step(1)
    assert info["evicted"]

def test_cpu_memory_parsers():
    assert K8sClient._parse_cpu("500m") == 0.5
    assert K8sClient._parse_cpu("2") == 2.0
    assert K8sClient._parse_cpu("1000000000n") == 1.0

    assert K8sClient._parse_memory("128Mi") == 128 * 1024 * 1024
    assert K8sClient._parse_memory("1Gi") == 1024 ** 3

def test_dashboard_api():
    from src.dashboard.app import app
    with app.test_client() as client:
        res = client.get('/api/state')
        assert res.status_code == 200
        data = res.get_json()
        assert "metrics" in data
        assert "nodes" in data
        assert len(data["nodes"]) == 3

