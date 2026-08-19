import sys
import tempfile
import json
from pathlib import Path

try:
    from src.call_graph_edges import load_call_edges
except Exception as e:
    print(f'ERROR: Failed to import load_call_edges: {e}')
    sys.exit(1)

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    # Create a file with non-empty, non-whitespace, invalid JSON content
    invalid_json_file = tmp / "invalid.json"
    invalid_json_file.write_text("this is not valid json at all", errors="replace")

    try:
        result = load_call_edges(str(invalid_json_file))
        # No exception raised when one was expected for invalid JSON
        print("NOT CONFIRMED — no exception was raised for invalid JSON input; result: {result!r}")
    except json.JSONDecodeError:
        # This is the spec-correct behavior
        print("NOT CONFIRMED — JSONDecodeError raised as required by specification")
    except ValueError as e:
        # Buggy behavior: _load_json_edges catches JSONDecodeError and wraps as ValueError
        print(f"CONFIRMED — _load_call_edge_file raises ValueError instead of JSONDecodeError: {e}")
    except Exception as e:
        print(f"ERROR: Unexpected exception type: {type(e).__name__}: {e}")
        sys.exit(1)
