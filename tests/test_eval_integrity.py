"""Integrity tests for evaluation benchmarks and RL model usage."""

import pytest
import numpy as np
from src.rl.evaluate import run_simulation_benchmark
from src.rl.env.cluster_env import K8sClusterEnv

def test_rl_config_must_call_model_predict():
    """
    Test integrity guard: Any configuration claiming to be RL/PPO must actually
    invoke model.predict at least once during evaluation.
    """
    results = run_simulation_benchmark(episodes=1)
    
    for config_name, metrics in results.items():
        if "RL" in config_name or "PPO" in config_name:
            assert metrics.get("calls_model_predict", False) is True, (
                f"Integrity failure: Configuration '{config_name}' claims to be RL/PPO "
                f"but never invoked model.predict!"
            )

def test_observation_matches_env_space():
    """
    Verifies that the observation returned by the environment matches
    its declared observation_space shape.
    """
    env = K8sClusterEnv(num_nodes=3, num_pods=12)
    obs, _ = env.reset(seed=42)
    assert obs.shape == env.observation_space.shape, (
        f"Observation shape mismatch: expected {env.observation_space.shape}, got {obs.shape}"
    )

def test_no_silent_fallback_to_heuristic_when_labeled_rl():
    """
    Asserts that if a configuration is labeled RL, it cannot fall back silently
    to a greedy heuristic without raising an assertion.
    """
    results = run_simulation_benchmark(episodes=1)
    for config_name, metrics in results.items():
        if "Proposed (Comm-Aware Sched+Desched)" in config_name:
            # If the old mislabeled name is used, it must fail because it didn't call RL
            assert metrics.get("calls_model_predict", False) is True, (
                f"Silent fallback: '{config_name}' is using greedy search without RL"
            )
