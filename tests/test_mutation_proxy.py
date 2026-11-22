"""
Mutation test for per-config ModelCountingProxy isolation (T0.12-a).

This test deliberately creates a scenario where two configs both declare uses_model=True,
but only ONE of them actually calls predict().  The integrity guard must FAIL (i.e.
raise AssertionError) for the config whose proxy counter is still zero.

We demonstrate:
  1. The mutation (broken variant) → test FAILS as expected.
  2. The correct variant → test PASSES (all uses_model=True configs have counter >= 1).
"""

import pytest
from src.rl.evaluate import ModelCountingProxy


class DummyModel:
    """A trivial model that returns a fixed action."""
    def predict(self, obs, **kwargs):
        return 0, None


def _run_guard(results: dict):
    """
    Re-implement Guard 1 logic (same as test_eval_integrity.py) so we can call it
    directly with hand-crafted results dicts.
    """
    for config_name, metrics in results.items():
        uses_model = metrics.get("uses_model", False)
        call_count = metrics.get("model_call_count", 0)
        if uses_model:
            assert call_count >= 1, (
                f"Integrity failure: Configuration '{config_name}' has uses_model=True "
                f"but its own model_call_count is {call_count} (per-config proxy)!"
            )


# ---------------------------------------------------------------------------
# MUTATION: two configs with uses_model=True; only one calls predict → FAIL
# ---------------------------------------------------------------------------

def test_mutation_one_of_two_uses_model_configs_never_calls_predict__must_fail():
    """
    MUTATION TEST — this test asserts that the guard FAILS when one of two
    uses_model=True configs has never had predict() called on its proxy.

    Broken scenario:
      - Config A: uses_model=True, proxy called once  → counter = 1 ✓
      - Config B: uses_model=True, proxy NEVER called  → counter = 0 ✗ (guard fires)
    """
    model = DummyModel()
    proxy_a = ModelCountingProxy(model)
    proxy_b = ModelCountingProxy(model)  # separate instance; never called

    # Only call predict on proxy_a
    proxy_a.predict(obs=None)
    # proxy_b.predict is intentionally NOT called (the mutation)

    results = {
        "Config-A (uses_model, calls predict)": {
            "uses_model": True,
            "model_call_count": proxy_a.call_count,  # 1
        },
        "Config-B (uses_model, NO predict call)": {
            "uses_model": True,
            "model_call_count": proxy_b.call_count,  # 0  ← broken
        },
    }

    # The guard MUST raise here because Config-B has count=0 but uses_model=True.
    with pytest.raises(AssertionError) as exc_info:
        _run_guard(results)

    assert "Config-B" in str(exc_info.value), (
        "AssertionError should name the offending config (Config-B)."
    )
    print("\n[MUTATION TEST OUTPUT — expected failure]\n", exc_info.value)


# ---------------------------------------------------------------------------
# CORRECT variant: both configs call predict → PASS
# ---------------------------------------------------------------------------

def test_correct_both_uses_model_configs_call_predict__must_pass():
    """
    CORRECT variant: both configs declare uses_model=True and both proxies
    have predict() called at least once.  Guard must pass silently.
    """
    model = DummyModel()
    proxy_a = ModelCountingProxy(model)
    proxy_b = ModelCountingProxy(model)

    proxy_a.predict(obs=None)
    proxy_b.predict(obs=None)

    results = {
        "Config-A (uses_model, calls predict)": {
            "uses_model": True,
            "model_call_count": proxy_a.call_count,  # 1
        },
        "Config-B (uses_model, calls predict)": {
            "uses_model": True,
            "model_call_count": proxy_b.call_count,  # 1
        },
    }

    # Should not raise.
    _run_guard(results)
