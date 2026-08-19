import sys
import os
import tempfile

# FM-Agent self-validation guard: use a temp dir as the probe workspace.
TMP = tempfile.mkdtemp(prefix="probe_normalize_fqn_")
os.chdir(TMP)

# We need to add the repo root to sys.path so we can import src.call_graph_edges.
# The probe is run from the repo root; TMP is different, so add the original cwd.
# We capture the original cwd from the first argument if provided, else use the
# standard relative path assumption.
if len(sys.argv) > 1:
    REPO_ROOT = sys.argv[1]
else:
    # When run from repo root, the repo root is os.getcwd() before we chdir'd.
    # Since we chdir'd to TMP, we need a fallback. We'll use the path relative to
    # where this script lives.
    REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

sys.path.insert(0, REPO_ROOT)

try:
    from src.call_graph_edges import normalize_fqn_label
except Exception as e:
    print(f"ERROR: Failed to import normalize_fqn_label: {e}")
    sys.exit(1)

# --- Test case: path/to/file.c::func ---
# Specification claims:
#   - Every '/' replaced by '::'
#   - File-extension dot immediately preceding a '::' function separator
#     is replaced by a hyphen '-'
#   - No '/' characters remain
#   - '::' is the segment delimiter throughout
#
# Trigger condition input: "path/to/file.c::func"
# Expected (spec-correct) output: "path::to::file-c::func"
#
# The bug report claims the code produces: "path::to::file.c::func"
# We verify whether the actual code matches the spec or the buggy output.

input_label = "path/to/file.c::func"
expected = "path::to::file-c::func"
buggy_output = "path::to::file.c::func"  # what the bug report claims

try:
    actual = normalize_fqn_label(input_label)
except Exception as e:
    print(f"ERROR: normalize_fqn_label raised: {e}")
    sys.exit(1)

# Does the actual output match the spec (i.e., no bug)?
spec_match = actual == expected
# Does the actual output match the buggy output (i.e., bug confirmed)?
bug_confirmed = actual == buggy_output

if bug_confirmed:
    print(f"CONFIRMED — actual: {actual!r} | expected (spec): {expected!r}")
elif spec_match:
    print(f"NOT CONFIRMED — actual matches specification: {actual!r}")
else:
    print(f"NOT CONFIRMED — actual: {actual!r} matches neither expected ({expected!r}) nor buggy ({buggy_output!r})")
