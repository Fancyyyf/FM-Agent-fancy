"""Probe script for bug: _metadata_body returns user_id that is not stable across calls.

Bug ID: src--llm_client-py--_metadata_body

The spec requires _metadata_body() to return a stable, consistent user_id
across calls within the same installation. However, _metadata_body() calls
_stable_user_id(), which returns settings.inject.id when truthy. Because
settings.inject.id is mutable, the user_id can change between calls.
"""

import os
import sys

# Add repo root to sys.path so we can import the package
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

exit_code = 0
result_msg = ""

try:
    # Import through the package entry point
    import config as cfg
    import src.llm_client as llm

    # --- Call _metadata_body() once to get initial value ---
    first = llm._metadata_body()

    # Verify the structure matches the spec: {"metadata": {"user_id": <str>}}
    assert isinstance(first, dict), f"Expected dict, got {type(first).__name__}"
    assert "metadata" in first, "'metadata' key missing from result"
    assert isinstance(first["metadata"], dict), "'metadata' value is not a dict"
    assert "user_id" in first["metadata"], "'user_id' key missing from metadata"
    first_user_id = first["metadata"]["user_id"]
    assert isinstance(first_user_id, str), f"user_id is not a string: {type(first_user_id).__name__}"
    assert len(first_user_id) > 0, "user_id is empty"

    # --- Mutate settings.inject.id to simulate configuration change ---
    original_id = cfg.settings.inject.id
    cfg.settings.inject.id = "mutated-user-id-abc123"

    # --- Call _metadata_body() again after mutation ---
    second = llm._metadata_body()
    second_user_id = second["metadata"]["user_id"]

    # --- Restore original setting ---
    cfg.settings.inject.id = original_id

    # --- Verdict: did the user_id change? ---
    if first_user_id != second_user_id:
        result_msg = (
            "CONFIRMED — user_id changed across calls after settings mutation.\n"
            f"  First call  (settings.inject.id={original_id!r}): user_id={first_user_id!r}\n"
            f"  Second call (settings.inject.id='mutated-user-id-abc123'): user_id={second_user_id!r}\n"
            f"  Spec requires: user_id is a stable, consistent string that identifies\n"
            f"  the current environment across calls within the same installation.\n"
            f"  Bug: settings.inject.id is mutable, so _stable_user_id() (called by\n"
            f"  _metadata_body) can return different values between calls."
        )
    else:
        result_msg = (
            "NOT CONFIRMED — user_id remained stable across calls.\n"
            f"  user_id: {first_user_id!r}\n"
            f"  (settings.inject.id was {original_id!r} for both calls)"
        )

except Exception as exc:
    result_msg = f"ERROR: {type(exc).__name__}: {exc}"
    exit_code = 1
    import traceback
    traceback.print_exc()

print(result_msg)
sys.exit(exit_code)
