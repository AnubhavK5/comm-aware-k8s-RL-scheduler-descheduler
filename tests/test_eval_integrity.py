"""Integrity tests for evaluation benchmarks, model usage proxies, and shape compatibility."""

import re
import pytest
import numpy as np
from src.rl.evaluate import run_simulation_benchmark, ModelCountingProxy
from src.rl.env.cluster_env import K8sClusterEnv
from src.scheduler.scorer import NodeScorer
from src.telemetry.aggregator import TelemetryAggregator
from src.common.k8s_client import K8sClient

# Keywords implying a trained/learned model policy
LEARNED_LABEL_PATTERN = re.compile(r"(rl|ppo|learned|policy|neural|ai)", re.IGNORECASE)

class SentinelFailingModel:
    """Sentinel model that raises an exception if predict() is called."""
    def predict(self, *args, **kwargs):
        raise RuntimeError("SentinelFailingModel: predict was invoked on a model that should not be called!")

def test_counting_proxy_and_model_usage_guard():
    """
    Guard 1:
    - Any config with uses_model=True must have proxy counter >= 1.
    - Any config whose label contains RL/PPO/learned/policy/neural/AI must have uses_model=True.
    """
    results = run_simulation_benchmark(episodes=1)

    for config_name, metrics in results.items():
        is_labeled_learned = bool(LEARNED_LABEL_PATTERN.search(config_name))
        uses_model = metrics.get("uses_model", False)
        call_count = metrics.get("model_call_count", 0)

        if is_labeled_learned:
            assert uses_model is True, (
                f"Integrity failure: Configuration '{config_name}' is labeled as learned/RL/AI "
                f"but uses_model is False!"
            )

        if uses_model:
            assert call_count >= 1, (
                f"Integrity failure: Configuration '{config_name}' has uses_model=True "
                f"but model predict counter is {call_count}!"
            )

def test_sentinel_model_does_not_break_heuristic_configs():
    """
    Guard 2:
    Run the benchmark with a sentinel model that raises on predict().
    All configurations with uses_model=False must still run without raising an error.
    """
    sentinel = SentinelFailingModel()
    results = run_simulation_benchmark(episodes=1, model_override=sentinel)
    assert len(results) > 0
    for name, metrics in results.items():
        assert metrics.get("uses_model", False) is False

def test_observation_matches_env_space():
    """
    Guard 3:
    Verifies that the observation returned by the environment matches
    its declared observation_space shape.
    """
    env = K8sClusterEnv(num_nodes=3, num_pods=12)
    obs, _ = env.reset(seed=42)
    assert obs.shape == env.observation_space.shape, (
        f"Observation shape mismatch: expected {env.observation_space.shape}, got {obs.shape}"
    )

@pytest.mark.xfail(reason="D5, fix in Phase 5: Scorer feeds 7D state vector to 42D model")
def test_model_input_dim_equals_live_observation_dim():
    """
    Guard 4 (Defect D5 check):
    Checks whether the node scorer's state vector dimension matches
    the PPO model's expected observation input dimension.
    Currently expected to fail because NodeScorer produces a 7-dim vector
    while PPO was trained on a 42-dim vector.
    """
    aggregator = TelemetryAggregator(K8sClient())
    snapshot = aggregator.get_cluster_snapshot()
    # Compute 7D vector from aggregator
    state_vec = snapshot.compute_state_vector(pod_name="test-pod", candidate_node="node-1")

    # ClusterEnv observation dimension is 42
    env = K8sClusterEnv(num_nodes=3, num_pods=12)
    expected_dim = env.observation_space.shape[0]

    assert state_vec.shape[0] == expected_dim, (
        f"Defect D5: NodeScorer state vector has dimension {state_vec.shape[0]}, "
        f"but RL model expects dimension {expected_dim}!"
    )
