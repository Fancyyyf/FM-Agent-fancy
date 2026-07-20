"""Probe script for bug src--call_graph_edges-py--_parse_caller.

Bug claim: _parse_caller raises ValueError when "fqn" holds a non-string value
(e.g., integer 1) because _optional_string rejects non-string inputs, even when
"callsite_names" provides a nonempty list. Per spec, a non-string fqn should be
treated as empty, and the function should still return a CallerSelector when
callsite_names is nonempty.
"""

import json
import os
import sys
import tempfile

# Ensure the project's src/ directory is on the Python path so the public
# entry-point import works from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    from src.call_graph_edges import load_call_edges
except Exception as e:
    print(f"ERROR: import failed: {e}")
    sys.exit(1)

# Build a minimal JSON edge file with fqn = 1 (non-string, triggers the bug)
# and a nonempty callsite_names so the spec says it should succeed.
payload = {
    "edges": [
        {
            "caller": {
                "fqn": 1,
                "callsite_names": ["test_fn"],
            },
            "callee": {
                "fqn": "some::callee::func",
            },
        }
    ]
}

fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="probe_parse_caller_")
try:
    with os.fdopen(fd, "w") as f:
        json.dump(payload, f)

    # Spec-correct behavior: fqn=1 should be treated as empty, callsite_names
    # is nonempty → should return a CallEdge with CallerSelector("", ("test_fn",)).
    # Actual (buggy) behavior: _optional_string raises ValueError on non-string.
    try:
        result = load_call_edges(tmp_path)
        # If we reach here, the code did NOT raise → NOT CONFIRMED
        print(
            f"NOT CONFIRMED — load_call_edges succeeded unexpectedly, "
            f"returned {len(result)} edge(s)"
        )
    except ValueError as exc:
        # Bug reproduced: ValueError was raised for non-string fqn
        print(f"CONFIRMED — actual (buggy): ValueError raised: {exc}")
    except Exception as exc:
        # Unexpected error type
        print(f"NOT CONFIRMED — unexpected exception: {type(exc).__name__}: {exc}")
finally:
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
