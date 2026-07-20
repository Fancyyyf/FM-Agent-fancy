import sys
import os

# Ensure the repo root is on sys.path so that `from src.xxx` resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.generate_topdown_layers import _tarjan_scc

    # Simple DAG: 1 -> 2 (edge from 1 to 2, no cycles)
    # Tarjan produces SCCs in reverse topological order:
    #   Node 2 (sink, no outgoing) processed first  → SCC {2}
    #   Node 1 processed second                     → SCC {1}
    #   Result: [{2}, {1}]
    #
    # Spec claim: for edge from SCC at i to SCC at j, i ≤ j
    # Edge 1→2: i=1 (SCC {1}), j=0 (SCC {2})
    # Spec requires: 1 ≤ 0  →  False
    # Violation → bug confirmed

    nodes = [1, 2]
    edges = {1: {2}, 2: set()}

    actual = _tarjan_scc(nodes, edges)

    # Map node to SCC index in result
    idx_of = {}
    for idx, scc in enumerate(actual):
        for node in scc:
            idx_of[node] = idx

    i = idx_of[1]
    j = idx_of[2]

    # Does the spec hold? Spec requires i <= j for edge 1->2
    spec_holds = i <= j
    # Bug is confirmed if the spec does NOT hold
    bug_reproduced = not spec_holds

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if bug_reproduced:
    print(f'CONFIRMED — actual result: {actual} | got i={i}, j={j} for edge 1→2 | spec requires i <= j but {i} <= {j} = {spec_holds}')
else:
    print(f'NOT CONFIRMED — spec requirement i <= j was met: {i} <= {j} = {spec_holds}')
