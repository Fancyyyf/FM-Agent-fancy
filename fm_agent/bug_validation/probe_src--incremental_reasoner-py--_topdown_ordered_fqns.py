"""Probe for _topdown_ordered_fqns sort-order bug.

Bug: The function sorts layers in ascending order (layer 0, 1, 2, ...),
but generate_topdown_layers assigns callees to lower-numbered layers.
Therefore ascending sort produces bottom-up order (callees first),
violating the spec claim that "callers precede the callees they depend on
(top-down order)."

This probe creates a minimal work_dir with a two-layer topdown JSON:
  Layer 0: callee_a, callee_b
  Layer 1: caller_x, caller_y

If the bug exists, the function returns callee_a, callee_b, caller_x, caller_y
(bottom-up).  If it were correct (spec-adherent), it would return
caller_x, caller_y, callee_a, callee_b (top-down).

Because the spec itself also says "ascending layer number", the correct
interpretation is:
  "callers precede callees" -> top-down (the primary claim) takes precedence,
  and the ascending-layer claim is secondary / contradictory.
The bugs validator's trigger_condition confirms this: ascending sort is the
root of the bottom-up result.
"""
import sys
import os
import json
import tempfile
from unittest import mock

# ---------------------------------------------------------------------------
# Setup: ensure the project root is on the path so `from src.incremental_reasoner`
# and `from config import ...` resolve correctly.
# ---------------------------------------------------------------------------
# probe is at fm_agent/bug_validation/probe_*.py; go up 3 levels to repo root
_PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJ_ROOT)

try:
    from src.incremental_reasoner import _topdown_ordered_fqns
except Exception as e:
    print(f"ERROR: could not import _topdown_ordered_fqns: {e}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Build a minimal work_dir with:
#   phases.json          – one phase
#   spec_prompts/phase_01_topdown_layers.json – two layers: callees first
# ---------------------------------------------------------------------------

def _build_work_dir(base):
    work = os.path.join(base, "fm_agent")
    spec_dir = os.path.join(work, "spec_prompts")
    os.makedirs(spec_dir, exist_ok=True)

    # phases.json
    phases = {
        "project": "test_proj",
        "languages": ["python"],
        "file_extensions": {},
        "phases": [
            {
                "phase": 1,
                "name": "test",
                "description": "Test phase",
                "modules": [],
            }
        ],
    }
    with open(os.path.join(work, "phases.json"), "w") as f:
        json.dump(phases, f, indent=2)

    # topdown layers — callees in layer 0, callers in layer 1
    topdown = {
        "phase": 1,
        "phase_name": "test",
        "total_functions": 4,
        "total_layers": 2,
        "layers": [
            {
                "layer": 0,
                "functions": [
                    {"name": "callee_a", "file": "callee_a.py"},
                    {"name": "callee_b", "file": "callee_b.py"},
                ],
            },
            {
                "layer": 1,
                "functions": [
                    {"name": "caller_x", "file": "caller_x.py"},
                    {"name": "caller_y", "file": "caller_y.py"},
                ],
            },
        ],
    }
    with open(os.path.join(spec_dir, "phase_01_topdown_layers.json"), "w") as f:
        json.dump(topdown, f, indent=2)

    return work


# ---------------------------------------------------------------------------
# Run the probe
# ---------------------------------------------------------------------------
def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = _build_work_dir(tmpdir)

        # Mock generate_topdown_layers – it's a side effect that regenerates
        # the layer files, but our pre-created file is sufficient.
        # Mock _load_phases – we already put the right phases.json; just stop
        # it from wiping our setup.  Actually _load_phases just reads the
        # file, so it's fine.
        with mock.patch("src.incremental_reasoner.generate_topdown_layers"):
            try:
                actual = _topdown_ordered_fqns(work_dir, extra_call_edges=None)
            except Exception as e:
                print(f"ERROR: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)

    # expected under the bug: ascending layer sort -> callees first
    expected = ["callee_a", "callee_b", "caller_x", "caller_y"]

    # The spec says "callers precede callees" (top-down).
    # The correct (spec-adherent) order would be ["caller_x", "caller_y", "callee_a", "callee_b"].
    # The actual (buggy) order is callees first, so actual != spec-correct order -> bug CONFIRMED.
    # confirmed when actual == expected (i.e. the buggy behavior), NOT the spec-correct order.
    passed = actual == expected

    if passed:
        print(
            "CONFIRMED — ascending layer sort gives bottom-up order: "
            f"{actual} (expected: {expected})"
        )
    else:
        print(f"NOT CONFIRMED — actual: {actual} | expected: {expected}")


if __name__ == "__main__":
    main()
