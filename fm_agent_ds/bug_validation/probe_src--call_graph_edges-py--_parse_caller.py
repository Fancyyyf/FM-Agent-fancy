import sys
import tempfile
import os
import json

# Ensure the repo root is on sys.path so 'src' is importable
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.call_graph_edges import load_call_edges, CallerSelector

    # Create temp dir and JSON file with integer fqn (should be accepted per spec)
    tmpdir = tempfile.mkdtemp()
    json_path = os.path.join(tmpdir, "test_edges.json")
    with open(json_path, "w") as f:
        json.dump({"edges": [{"caller": {"fqn": 123}}]}, f)

    try:
        result = load_call_edges(json_path)

        # If we get here, the code did NOT raise — check if fqn was converted from int
        if result and len(result) > 0:
            actual = result[0].caller.fqn
            # spec says fqn should be converted to canonical form
            # normalize_fqn_label expects a string; but the fact we got here means
            # the code accepted the integer and produced something
            print(
                "NOT CONFIRMED — load_call_edges returned successfully"
                f" (unexpected); caller.fqn={actual!r}"
            )
        else:
            print("NOT CONFIRMED — load_call_edges returned empty result")
    except ValueError as e:
        err_msg = str(e)
        if "caller.fqn" in err_msg or "must be a string" in err_msg:
            print(
                "CONFIRMED — ValueError raised for integer fqn:"
                f" {err_msg} | expected: CallerSelector with fqn='123'"
            )
        else:
            print(
                f"NOT CONFIRMED — unexpected ValueError (not fqn-related): {err_msg}"
            )
    finally:
        # Clean up temp files
        if os.path.exists(json_path):
            os.unlink(json_path)
        if os.path.exists(tmpdir):
            os.rmdir(tmpdir)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
