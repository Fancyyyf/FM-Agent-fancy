import sys
import os

# Ensure the repo root is on sys.path so 'import src' resolves
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from unittest.mock import patch
from dataclasses import dataclass, field

try:
    from src.languages.erlang import call_edges, ErlangAnalysis

    # ── Bug Description ────────────────────────────────────────────────
    # Spec claim: "Returns a mapping from caller fully-qualified names to
    #   sets of callee fully-qualified names" where "FQNs follow the format:
    #   path::components::delimited::by::double::colons"
    # Actual:     call_edges returns ErlangAnalysis.edges directly, which
    #   has dict[tuple[str, str], set[str]] keys — tuples of
    #   (function_id, caller_module), NOT FQN strings.
    #   Additionally, the function performs zero validation that callees
    #   are functions that exist within the analyzed Erlang project.
    # Code:       Line 644: return _analysis_or_empty(_callgraph_project_root(proj_dir)).edges
    # ────────────────────────────────────────────────────────────────────

    # Create a mock ErlangAnalysis with tuple-keyed edges — this is the
    # actual data shape produced by _analyze_project_uncached (line 494 of erlang.py:
    #   edges: dict[tuple[str, str], set[str]] = {})
    mock_analysis = ErlangAnalysis(
        functions={},
        edges={
            ("module__function__0", "module-erl"): {"callee__helper__0"},
        },
    )

    with patch(
        "src.languages.erlang._analysis_or_empty",
        return_value=mock_analysis,
    ):
        result = call_edges("/some/proj_dir")

    # ── Verification ───────────────────────────────────────────────────
    # The spec requires FQN string keys like "module::function::0"
    # The actual code returns tuple keys like ("module__function__0", "module-erl")
    keys = list(result.keys())

    # Bug 1: Keys are tuples, not FQN strings
    has_tuple_keys = any(isinstance(k, tuple) for k in keys)
    # Bug 2: No validation — callee "callee__helper__0" accepted without
    # checking it exists in the project (ErlangAnalysis.functions is empty!)

    if has_tuple_keys:
        actual_desc = (
            f"keys are tuples (e.g. {keys[0]!r}), not FQN strings; "
            f"no callee-existence validation performed"
        )
        expected_desc = (
            "keys must be FQN strings (e.g. 'module::function::0'); "
            "callees must be validated against project functions"
        )
        passed = True
    else:
        actual_desc = f"keys are strings: {keys}"
        expected_desc = "keys must be FQN strings"
        passed = False

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print("CONFIRMED")
    print(f"  actual:   {actual_desc!r}")
    print(f"  expected: {expected_desc!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual_desc!r}")
