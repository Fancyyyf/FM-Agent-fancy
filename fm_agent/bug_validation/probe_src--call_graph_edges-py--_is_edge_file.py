import sys
import json
import tempfile
import os

repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.call_graph_edges import load_call_edges
except Exception as e:
    print(f'ERROR: import failed — {e}')
    sys.exit(1)

# Create a temp directory with a .json file that is valid JSON
# but NOT parseable CallEdge data — it has no "edges" list.
with tempfile.TemporaryDirectory() as tmpdir:
    probe_file = os.path.join(tmpdir, "not_call_edge_data.json")
    with open(probe_file, 'w') as f:
        json.dump({"some": "irrelevant data"}, f)

    try:
        result = load_call_edges(tmpdir)
        # If we reach here without exception, _is_edge_file must have
        # correctly returned False and the file was skipped — the bug
        # is NOT present (or the test failed to trigger it).
        print(f'NOT CONFIRMED — load_call_edges returned {result} (file skipped, _is_edge_file was correct)')
    except ValueError as e:
        # BUG CONFIRMED: _is_edge_file returned True for a non-CallEdge
        # .json file, causing _load_json_edges to fail when it found
        # no "edges" list.
        print(f'CONFIRMED — _is_edge_file allowed non-CallEdge .json file through; ValueError: {e}')
    except Exception as e:
        print(f'ERROR: unexpected exception — {e}')
        sys.exit(1)
