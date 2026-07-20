# Bug Report: _is_edge_file

**Source file:** `src/call_graph_edges-py/_is_edge_file.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True exactly when the file at file_path contains parseable CallEdge data

---

### Actual Behavior

The function returns True if the file extension (suffix) of the given path object, when lowercased, equals '.json'; otherwise returns False. The path object is not modified. No side effects occur. Formalized: (result == (path.suffix.lower() == '.json'))

---

## Code Evidence

Line 2: return path.suffix.lower() == ".json"

---

## Trigger Condition

The code checks only the file extension, returning True for any .json file regardless of content. Specification requires True exactly when the file contains parseable CallEdge data. An empty .json file (empty.json) causes the code to return True, but the specification demands False because there is no parseable CallEdge data.

---

## How to trigger the bug

The public function `load_call_edges()` uses `_is_edge_file` as a filter when iterating a directory of supplemental edge files. Because `_is_edge_file` returns `True` for _any_ `.json` file, a `.json` file with valid JSON but without valid CallEdge structure (e.g., missing the `"edges"` list) passes the filter and reaches `_load_json_edges()`, which raises a `ValueError`. If `_is_edge_file` correctly returned `False` for non-parseable files, the file would be silently skipped.

### Inputs

| Parameter | Value |
|-----------|-------|
| `path` (to `load_call_edges`) | A temporary directory containing a `.json` file with content `{"some": "irrelevant data"}` |

### Expected (spec-correct) Output

`[]` — the file should be skipped because it does not contain parseable CallEdge data.

### Actual (buggy) Output

`ValueError: /tmp/.../not_call_edge_data.json: expected an 'edges' list`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, tempfile, os
from src.call_graph_edges import load_call_edges

with tempfile.TemporaryDirectory() as tmpdir:
    with open(os.path.join(tmpdir, "bad.json"), "w") as f:
        json.dump({"some": "data"}, f)
    load_call_edges(tmpdir)
# actual (buggy) output: ValueError: .../bad.json: expected an 'edges' list
# expected (correct) output: [] (file silently skipped)
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — _is_edge_file allowed non-CallEdge .json file through; ValueError: /tmp/tmpjo1mv76_/not_call_edge_data.json: expected an 'edges' list
```
