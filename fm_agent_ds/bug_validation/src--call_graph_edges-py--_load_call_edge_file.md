# Bug Report: _load_call_edge_file

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/call_graph_edges-py/_load_call_edge_file.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When the file content is empty or consists solely of Unicode whitespace characters, returns an empty list. When the file content is non-empty valid JSON, returns a list containing one CallEdge object for each element in the 'edges' array, in the same order the elements appear in the array. If the 'edges' array is present but contains zero elements, returns an empty list. Raises FileNotFoundError if edge_path does not refer to an existing file. Raises JSONDecodeError (or a subclass thereof) if the file content is non-empty but is not valid JSON conforming to the expected schema.

---

### Actual Behavior

The function returns a list of CallEdge objects. Let file_contents = the string obtained by reading edge_path with replacement errors. If file_contents.strip() == "", then the returned list is empty ([]). Otherwise, file_contents is a nonempty, nonwhitespace string containing valid JSON with a toplevel key 'edges' whose value is a JSON array of valid edge objects, and the function returns _load_json_edges(file_contents, str(edge_path)), which produces a list of CallEdge objects in onetoone order with the elements of the 'edges' array. Formally:

( f  Files  f = edge_path  readable(f)  (content(f) =   content(f) = whitespace  validJSONEdges(content(f)))) 
result = (if strip(read_text(f, errors='replace')) =  then [] else (let t = read_text(f, errors='replace') in let edges_list = decodeEdgesArray(t) in [CallEdge(e) | e  edges_list]))

where content(f) is the raw file content,  denotes empty/whitespaceonly text, and decodeEdgesArray(t) extracts the 'edges' array from the JSON in t, preserving order.

---

## Code Evidence

Lines 3-5: the code only checks for empty/whitespace content and otherwise calls _load_json_edges without validating JSON conformance; it fails to raise JSONDecodeError when the file contains invalid JSON.

---

## Trigger Condition

Specification requires raising JSONDecodeError (or subclass) if the file content is non-empty but not valid JSON conforming to the expected schema. The code does not guarantee this behavior; it passes the text directly to _load_json_edges, whose pre-condition requires valid JSON, leading to undefined behavior for invalid JSON input.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| edge_path (via load_call_edges) | Path to a temp `.json` file containing `"this is not valid json at all"` |

### Expected (spec-correct) Output

`json.JSONDecodeError` (or a subclass thereof) should be raised.

### Actual (buggy) Output

`ValueError` is raised instead — `_load_json_edges` catches the `json.JSONDecodeError` and wraps it in a `ValueError`, which is not a subclass of `JSONDecodeError`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
import json
from pathlib import Path
from src.call_graph_edges import load_call_edges

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    invalid_json_file = tmp / "invalid.json"
    invalid_json_file.write_text("this is not valid json at all", errors="replace")

    try:
        result = load_call_edges(str(invalid_json_file))
        print("no exception raised")
    except json.JSONDecodeError:
        print("JSONDecodeError raised — spec correct")
    except ValueError as e:
        # actual (buggy) output: ValueError instead of JSONDecodeError
        print(f"ValueError: {e}")
    # expected (correct) output: JSONDecodeError
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — _load_call_edge_file raises ValueError instead of JSONDecodeError: /tmp/tmp_pj275qt/invalid.json: invalid JSON: Expecting value: line 1 column 1 (char 0)
```
