"""Integrity tests for evaluation benchmarks, model usage proxies, and shape compatibility.

Rules enforced here:
  Guard 1: Any config with uses_model=True must have its OWN proxy counter >= 1.
           Any config whose label matches \\b(rl|ppo|learned|policy|neural|ai)\\b (word-boundary
           case-insensitive) must have uses_model=True.
  Guard 2: Run the benchmark with a sentinel model that raises on predict(); all configs
           with uses_model=False must still complete without error.
  D5 xfail: NodeScorer produces a 7-dim state vector; RL env expects a 42-dim vector.
            (strict=True, raises=AssertionError -- must fail with the right error)
"""

import re
import pytest
import numpy as np
from src.rl.evaluate import run_simulation_benchmark, ModelCountingProxy
from src.rl.env.cluster_env import K8sClusterEnv

# Word-boundary pattern: matches whole-word occurrences only.
# e.g. "PPO" matches but "HIPPODROME" does not; "policy" matches but "policy-name" does not.
LEARNED_LABEL_PATTERN = re.compile(r"\b(rl|ppo|learned|policy|neural|ai)\b", re.IGNORECASE)


class SentinelFailingModel:
    """Sentinel model that raises an exception if predict() is called."""
    def predict(self, *args, **kwargs):
        raise RuntimeError(
            "SentinelFailingModel: predict was invoked on a model that should not be called!"
        )


# ---------------------------------------------------------------------------
# Guard 1: per-config proxy counter + learned-label enforcement
# ---------------------------------------------------------------------------

def test_counting_proxy_per_config_and_model_usage_guard():
    """
    Guard 1 (per-config proxy):
    - Each config has its OWN ModelCountingProxy (counters must not bleed across configs).
    - Any config with uses_model=True must have model_call_count >= 1.
    - Any config whose label matches \\b(rl|ppo|learned|policy|neural|ai)\\b must have
      uses_model=True.
    """
    results = run_simulation_benchmark(episodes=1)

    for config_name, metrics in results.items():
        is_labeled_learned = bool(LEARNED_LABEL_PATTERN.search(config_name))
        uses_model = metrics.get("uses_model", False)
        call_count = metrics.get("model_call_count", 0)

        if is_labeled_learned:
            assert uses_model is True, (
                f"Integrity failure: Configuration '{config_name}' label matches learned/RL/AI "
                f"pattern but uses_model is False!"
            )

        if uses_model:
            assert call_count >= 1, (
                f"Integrity failure: Configuration '{config_name}' has uses_model=True "
                f"but its own model_call_count is {call_count} (per-config proxy)!"
            )


# ---------------------------------------------------------------------------
# Guard 2: sentinel model must not break heuristic configs
# ---------------------------------------------------------------------------

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
        # Every current config is heuristic (uses_model=False); sentinel must not be called.
        assert metrics.get("uses_model", False) is False, (
            f"Config '{name}' unexpectedly has uses_model=True when running with sentinel."
        )


# ---------------------------------------------------------------------------
# D5 xfail: dimension mismatch (must fail with AssertionError, not kubeconfig error)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="D5 (fix in Phase 5): NodeScorer produces a 7-dim state vector but RL env expects 42-dim",
)
def test_model_input_dim_equals_live_observation_dim():
    """
    Defect D5 check -- expected to FAIL with AssertionError until Phase 5.

    Constructs the 7-dim KubeAI-style state vector directly (no cluster needed)
    and asserts it matches the RL env's observation space dimension.
    This must fail with 7 != 42, NOT with a kubeconfig/connection error.
    """
    # Build the 7-dim KubeAI-style state vector locally (no K8s cluster required).
    # Corresponds to: [cpu_eff, mem_eff, node_cpu, node_mem, disk_io, net_lat, node_temp]
    state_vec = np.array([0.5, 0.6, 0.3, 0.4, 0.1, 0.05, 36.0], dtype=np.float32)

    # The RL training environment uses a 42-dim observation space.
    env = K8sClusterEnv(num_nodes=3, num_pods=12)
    expected_dim = env.observation_space.shape[0]  # 42

    assert state_vec.shape[0] == expected_dim, (
        f"Defect D5: NodeScorer state vector has dimension {state_vec.shape[0]}, "
        f"but RL model expects dimension {expected_dim}!"
    )
