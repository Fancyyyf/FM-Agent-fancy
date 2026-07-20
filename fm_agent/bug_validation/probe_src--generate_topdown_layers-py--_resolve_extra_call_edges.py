"""Probe script for bug: _resolve_extra_call_edges truthiness check on edge.caller.fqn.

Bug: The code uses 'if edge.caller.fqn:' (truthiness check) before checking
membership in phase_fqns. This skips falsy values (like empty string) even
when they ARE members of phase_fqns. The spec requires that any caller FQN
present in phase_fqns appears as a key, without exempting falsy values.
"""

import sys

try:
    from src.generate_topdown_layers import _resolve_extra_call_edges, _ResolvedExtraEdge
    from src.call_graph_edges import CallEdge, CallerSelector, CalleeTarget

    # Construct an edge where caller.fqn is an empty string (falsy).
    # The callee.fqn must be in known_fqns for the edge to be processed at all.
    edge = CallEdge(
        caller=CallerSelector(fqn="", callsite_names=()),
        callee=CalleeTarget(fqn="callee_func", info_names=()),
        source="test",
    )

    # phase_fqns includes the empty string — the spec says it MUST appear as a key.
    phase_fqns = [""]
    known_fqns = ["callee_func"]

    by_caller_fqn, by_callsite = _resolve_extra_call_edges(
        [edge], phase_fqns=phase_fqns, known_fqns=known_fqns
    )

    # Spec-correct behavior: "" should be a key in by_caller_fqn
    # Buggy behavior: "" is NOT a key because 'if edge.caller.fqn:' is False for ""
    has_empty_key = "" in by_caller_fqn

    if has_empty_key:
        entries = by_caller_fqn[""]
        actual_repr = repr([(e.callee_fqn, e.info_names) for e in entries])
        print(f"NOT CONFIRMED — bug not triggered: empty string key present with {len(entries)} entry(ies): {actual_repr}")
    else:
        # Bug confirmed: empty string is in phase_fqns but NOT in by_caller_fqn
        all_keys = list(by_caller_fqn.keys())
        print(f"CONFIRMED — actual: by_caller_fqn has keys {all_keys!r} | expected: key '' (empty string) should be present because '' is in phase_fqns")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
