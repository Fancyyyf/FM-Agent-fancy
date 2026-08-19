"""Probe for bug: _add_resolved_extra_edge KeyError on callees_map/callers_map access.

Bug claim: Lines 463-464 (callees_map[caller_fqn].add(callee_fqn) and
callers_map[callee_fqn].add(caller_fqn)) raise KeyError when keys don't exist.

Verification: In the actual caller (_build_call_graph, lines 310-311),
callees_map and callers_map are always defaultdict(set), so the keys auto-create.
The function is private (_ prefix), only called from one place, always with
defaultdicts. The bug *cannot* manifest in real execution.
"""

import sys
import os
from collections import defaultdict

# Add repo root to sys.path so 'src' imports resolve
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from src.generate_topdown_layers import _add_resolved_extra_edge, _ResolvedExtraEdge


def test_with_defaultdict():
    """Test with defaultdict(set) — the actual usage pattern in _build_call_graph."""
    callees_map = defaultdict(set)
    callers_map = defaultdict(set)
    all_callees_map = defaultdict(set)
    edge_aliases_map = defaultdict(lambda: defaultdict(set))

    edge = _ResolvedExtraEdge(
        callee_fqn="target::func",
        info_names=("alias1", "alias2"),
        source="test",
    )
    phase_fqns = {"target::func", "other::func"}

    result = _add_resolved_extra_edge(
        caller_fqn="caller::func",
        edge=edge,
        phase_fqns=phase_fqns,
        callees_map=callees_map,
        callers_map=callers_map,
        all_callees_map=all_callees_map,
        edge_aliases_map=edge_aliases_map,
    )

    spec_satisfied = all([
        "target::func" in all_callees_map["caller::func"],
        "caller::func" in edge_aliases_map["target::func"],
        "target::func" in callees_map["caller::func"],
        "caller::func" in callers_map["target::func"],
        result is True,  # first time adding callee
    ])

    return spec_satisfied


def test_with_plain_dict():
    """Test with plain dict without required keys — the trigger condition."""
    callees_map = {}
    callers_map = {}
    all_callees_map = {"caller::func": set()}
    edge_aliases_map = {"target::func": {"caller::func": set()}}

    edge = _ResolvedExtraEdge(
        callee_fqn="target::func",
        info_names=("alias1",),
        source="test",
    )
    phase_fqns = {"target::func"}

    try:
        _add_resolved_extra_edge(
            caller_fqn="caller::func",
            edge=edge,
            phase_fqns=phase_fqns,
            callees_map=callees_map,
            callers_map=callers_map,
            all_callees_map=all_callees_map,
            edge_aliases_map=edge_aliases_map,
        )
        return False  # should have raised
    except KeyError as e:
        return True  # KeyError confirmed
    except Exception:
        return False


def main():
    errors = []

    try:
        defaultdict_ok = test_with_defaultdict()
    except Exception as e:
        defaultdict_ok = False
        errors.append(f"defaultdict test crashed: {e}")

    try:
        plain_dict_raises = test_with_plain_dict()
    except Exception as e:
        plain_dict_raises = False
        errors.append(f"plain dict test crashed: {e}")

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    # The bug is NOT CONFIRMED because the actual caller always uses
    # defaultdict(set), so the KeyError never occurs in real execution.
    # The plain_dict test shows the vulnerability exists in isolation,
    # but the function is private and its only call site guarantees
    # defaultdict arguments.
    if defaultdict_ok and plain_dict_raises:
        print(
            "NOT CONFIRMED — "
            "With defaultdict(set) (actual usage): spec IS satisfied, no KeyError. "
            "With plain dict (isolation): KeyError occurs. "
            "But the function is private and the sole caller provides defaultdict(set), "
            "so the bug does NOT manifest in practice."
        )
    elif defaultdict_ok and not plain_dict_raises:
        print("NOT CONFIRMED — defaultdict test passed, plain dict did not raise KeyError unexpectedly.")
    else:
        print("NOT CONFIRMED — unexpected behavior in tests.")


if __name__ == "__main__":
    main()
