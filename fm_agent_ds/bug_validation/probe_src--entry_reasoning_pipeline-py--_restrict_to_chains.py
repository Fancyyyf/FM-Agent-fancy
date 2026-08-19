import sys
import os
import tempfile

# Ensure the repo root is on sys.path so 'from src...' resolves.
# Python 3 adds the script's directory as sys.path[0], not the CWD,
# when the script path contains a directory component.
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.entry_reasoning_pipeline import _restrict_to_chains
except Exception as e:
    print(f'ERROR: import failed: {e}')
    sys.exit(1)

# Build a call_graph where D is NOT reachable from entry_func "A",
# but D CAN reach end_func "C" (via D -> C).
# The spec requires only functions on a directed path FROM entry_func TO end_func
# to be retained. The buggy code only checks reverse reachability from end_funcs
# and ignores entry_func entirely, so D is incorrectly included.
# Every FQN must be a key in call_graph (the spec says "FQN keys mapping to lists
# of callee FQN strings"). C must be a key so it passes the `ef in call_graph`
# filter on line 30, and D must be a key so the reverse adjacency loop visits it.
call_graph = {
    "A": ["B"],
    "B": ["C"],
    "C": [],       # end_func target — no outgoing edges
    "D": ["C"],    # D not reachable from A, but CAN reach C
}
entry_func = "A"
end_funcs = ["C"]

# Use a fresh temp dir as the probe workspace (FM-Agent self-validation guard).
tmpdir = tempfile.mkdtemp(prefix="probe_restrict_to_chains_")
os.chdir(tmpdir)  # isolate file I/O from repo

try:
    actual = _restrict_to_chains(call_graph, entry_func, end_funcs)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Expected (spec-correct): only functions on A -> ... -> C chain.
# That is A, B, C. D is NOT reachable from A, so D should NOT appear.
expected = {"A": ["B"], "B": ["C"], "C": []}

# The bug is confirmed if D (not on A->C path) appears in the output.
passed = "D" in actual

if passed:
    print(f'CONFIRMED — D incorrectly included in output: actual={actual!r} | expected (spec)=no D')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
