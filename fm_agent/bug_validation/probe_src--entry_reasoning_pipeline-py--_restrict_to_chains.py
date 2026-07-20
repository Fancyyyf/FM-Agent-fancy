"""Probe script for bug: _restrict_to_chains includes nodes not reachable from entry_func.

The function only does reverse BFS from end_funcs but never verifies forward
reachability from entry_func. Nodes not reachable from entry_func that can reach
an end_func are incorrectly included in the output.
"""
import sys
import os

# Add project root to path so we can import src modules
# The probe is at fm_agent/bug_validation/probe_*.py, so three dirs up is the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.entry_reasoning_pipeline import _restrict_to_chains

# Counterexample call graph:
#   A -> B -> C -> D
#   E -> C           (E is NOT reachable from A)
# With entry_func='A' and end_funcs=['C']:
#   Spec requires: only nodes on paths A -> ... -> C → {A, B, C}
#   Buggy code includes E because reverse BFS from C finds E as a caller,
#   without checking whether E is reachable from A.
call_graph = {
    'A': ['B'],
    'B': ['C'],
    'C': ['D'],
    'D': [],
    'E': ['C'],  # E can reach C but is NOT reachable from A
}
entry_func = 'A'
end_funcs = ['C']

# Spec-correct expected output: nodes must satisfy BOTH
#   1. Reachable from entry_func (A → ... → node exists in call_graph)
#   2. Can reach an end_func (node → ... → C exists in call_graph)
# Only A, B, C satisfy both. E satisfies (2) but NOT (1).
expected_keys = {'A', 'B', 'C'}

try:
    result = _restrict_to_chains(call_graph, entry_func, end_funcs)
    actual_keys = set(result.keys())

    # The bug: E should NOT be present
    passed = actual_keys != expected_keys

    if passed:
        extra = actual_keys - expected_keys
        missing = expected_keys - actual_keys
        details = []
        if extra:
            details.append(f"extra (incorrectly included): {sorted(extra)!r}")
        if missing:
            details.append(f"missing (incorrectly excluded): {sorted(missing)!r}")
        print(f"CONFIRMED — {', '.join(details)}")
        print(f"  actual keys:   {sorted(actual_keys)!r}")
        print(f"  expected keys: {sorted(expected_keys)!r}")
        print(f"  full result:   {result!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {sorted(actual_keys)!r}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
