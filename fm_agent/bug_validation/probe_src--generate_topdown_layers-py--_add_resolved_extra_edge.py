import sys
from collections import defaultdict

try:
    from src.generate_topdown_layers import _add_resolved_extra_edge, _ResolvedExtraEdge
except ImportError as e:
    print(f"ERROR: Import failed: {e}")
    sys.exit(1)


def test_with_regular_dict():
    """Test where callees_map is a regular dict (not defaultdict).
    caller_fqn is NOT in callees_map, callee_fqn IS in phase_fqns -> should KeyError."""
    caller_fqn = "caller::func"
    callee_fqn = "callee::func"

    edge = _ResolvedExtraEdge(
        callee_fqn=callee_fqn,
        info_names=("alias1", "alias2"),
        source="test",
    )

    phase_fqns = {callee_fqn}  # S = true (callee in phase)

    # Regular dict: caller_fqn NOT present (K1 = false)
    callees_map = {}
    callers_map = {}
    all_callees_map = defaultdict(set)
    all_callees_map[caller_fqn]  # pre-condition: must be initialized
    edge_aliases_map = defaultdict(lambda: defaultdict(set))
    edge_aliases_map[callee_fqn][caller_fqn]  # pre-condition: must be initialized

    try:
        result = _add_resolved_extra_edge(
            caller_fqn,
            edge,
            phase_fqns,
            callees_map,
            callers_map,
            all_callees_map,
            edge_aliases_map,
        )
        # If we get here, no KeyError was raised
        print(f"NOT CONFIRMED (regular dict) — no KeyError, result={result!r}")
        return "no_error"
    except KeyError as e:
        print(f"CONFIRMED — actual: KeyError raised | args: {e!r}")
        return "KeyError"
    except Exception as e:
        print(f"ERROR (regular dict): {type(e).__name__}: {e}")
        return f"error: {e}"


def test_with_defaultdict():
    """With defaultdict(set), the function should auto-initialize missing keys.
    This is the actual usage in _build_call_graph."""
    caller_fqn = "caller::func2"
    callee_fqn = "callee::func2"

    edge = _ResolvedExtraEdge(
        callee_fqn=callee_fqn,
        info_names=("a",),
        source="test",
    )

    phase_fqns = {callee_fqn}

    callees_map = defaultdict(set)   # NOT pre-populated with caller_fqn
    callers_map = defaultdict(set)
    all_callees_map = defaultdict(set)
    all_callees_map[caller_fqn]
    edge_aliases_map = defaultdict(lambda: defaultdict(set))
    edge_aliases_map[callee_fqn][caller_fqn]

    try:
        result = _add_resolved_extra_edge(
            caller_fqn,
            edge,
            phase_fqns,
            callees_map,
            callers_map,
            all_callees_map,
            edge_aliases_map,
        )
        # defaultdict auto-creates, so this should succeed
        actual_callees = sorted(callees_map.get(caller_fqn, set()))
        print(f"defaultdict test: result={result!r}, callees_map[caller_fqn]={actual_callees}")
        # Verify spec: callee_fqn IS in phase_fqns, so it should be added
        if callee_fqn in callees_map.get(caller_fqn, set()):
            print("spec_satisfied: callee_fqn added to callees_map[caller_fqn]")
        return "ok"
    except KeyError as e:
        print(f"CONFIRMED (defaultdict) — unexpected KeyError: {e!r}")
        return "KeyError"
    except Exception as e:
        print(f"ERROR (defaultdict): {type(e).__name__}: {e}")
        return f"error: {e}"


# Main
if __name__ == "__main__":
    status = test_with_regular_dict()
    test_with_defaultdict()
    if status == "KeyError":
        pass  # already printed CONFIRMED
    elif status == "no_error":
        print("NOT CONFIRMED — function completed without KeyError on regular dict")
    else:
        print(f"ERROR: unexpected status: {status}")
        sys.exit(1)
