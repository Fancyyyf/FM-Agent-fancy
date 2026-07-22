# Bug Report: _analyze_project_uncached

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/_analyze_project_uncached.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns an ErlangAnalysis object whose .functions attribute is a dict
    mapping each .erl file absolute path to a list of (function_id, source_text)
    tuples, where function_id is a canonical string identifier and source_text
    is the source code of that function
  - Returns an ErlangAnalysis whose .edges attribute is a dict mapping
    (function_id, caller_module) tuples to sets of callee function_ids
  - Returns an ErlangAnalysis whose .spans attribute is a dict mapping each
    .erl file absolute path to a list of (function_id, start_line, end_line)
    tuples, where start_line and end_line are 1-based inclusive line numbers
  - Returns an ErlangAnalysis whose .server_info attribute is populated from
    the ELP server initialization response
  - When no .erl files exist under the directory tree rooted at proj_dir after
    resolution to an absolute path, returns an ErlangAnalysis with all three
    dict attributes empty
  - Raises an exception when the ELP backend process cannot be started, the LSP
    communication channel fails, or the project at proj_dir cannot be analyzed

---

### Actual Behavior

The function returns an ErlangAnalysis object when it terminates normally; otherwise a TimeoutError or RuntimeError is raised and no value is returned.

**Normal termination (no exception)**
1. If `proj_dir` contains no `.erl` files (recursively), the function returns `ErlangAnalysis(functions={}, edges={})`. No ElpClient is started, no files are read.
2. If there is at least one `.erl` file,
   - All `.erl` files under `os.path.abspath(proj_dir)` are collected into `files`; their contents are read into the `sources` dict (UTF-8, errors replaced).
   - An ElpClient is created and entered, starting the language-server subprocess; after the `with` block the subprocess is stopped and the client closed.
   - The server is initialised with the first file and its source; all other files are opened via `open_document`.
   - For each file:
     * A source index is built.
     * The caller module name is determined.
     * Document symbols are requested from the server.
     * Function symbols (kind == FUNCTION_KIND) with a valid range are processed. Malformed or duplicate symbols (by canonical function ID within the same file) are silently skipped. A warning is logged for malformed ones.
     * The canonical function ID is obtained from the symbol's URI and name. Valid symbols produce tuples added to the `functions` dictionary: `functions[function_id]` becomes a nonempty list of `(caller_module, source_text_of_function)` where the source text is extracted from the original file using the range of the function definition.
     * `edges` and `spans` are populated similarly  `spans` maps a file path to `[(function_name, start_line, end_line)]` for every recognised function, and `edges` captures callercallee relationships.
   - After all files have been processed, the function returns `ErlangAnalysis(functions=functions, edges=edges, spans=spans)`.
   - All file reads and server communications succeeded; no unhandled ValueError occurs bec...

---

## Code Evidence

Line 5: return ErlangAnalysis(functions={}, edges={})

---

## Trigger Condition

When no .erl files exist the specification requires the returned ErlangAnalysis to have all three dict attributes (functions, edges, spans) empty; the code returns an object without a spans attribute, violating the specification.

---

## How to trigger the bug

The bug could not be reproduced. The `ErlangAnalysis` class is a Python `@dataclass` with `spans` defined as `field(default_factory=dict)`. When the code constructs `ErlangAnalysis(functions={}, edges={})`, Python dataclass mechanics automatically populate `spans` with a new empty dict via the `default_factory`. The actual runtime behavior matches the specification: all three dict attributes (`functions`, `edges`, `spans`) are empty dicts.

The logic verifier appears to have analyzed the extracted function in isolation, where the `ErlangAnalysis` class definition (including field defaults) resides in a different file, and concluded that the `spans` attribute is missing. This is a false positive.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A directory with no `.erl` files (empty temp directory) |

### Expected (spec-correct) Output

`ErlangAnalysis(functions={}, edges={}, spans={})` — all three dict attributes empty

### Actual (buggy) Output

`ErlangAnalysis(functions={}, edges={}, spans={})` — all three dict attributes empty (dataclass default provides `spans={}`)


### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from dataclasses import asdict
from src.languages.erlang import ErlangAnalysis, batch_extract

# Direct construction test
obj = ErlangAnalysis(functions={}, edges={})
print(asdict(obj))
# actual output: {'functions': {}, 'edges': {}, 'spans': {}, 'server_info': None}
# spans IS present and empty — bug NOT reproduced

# Public API test via batch_extract
with tempfile.TemporaryDirectory() as tmpdir:
    result = batch_extract(tmpdir)
    print(result)
    # actual output: {}
    # expected: {} — returns empty dicts for all three attributes
```

---

## Probe Script

```python
"""Probe attempt 3: Verify ErlangAnalysis spans via dataclasses.asdict and _analysis_or_empty."""
import sys
import os
import tempfile
from dataclasses import asdict
from unittest.mock import patch

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))

try:
    from src.languages.erlang import ErlangAnalysis

    # Test 1: Direct construction — verify via asdict that all 3 dict attrs are present and empty
    obj = ErlangAnalysis(functions={}, edges={})
    obj_dict = asdict(obj)

    has_functions = 'functions' in obj_dict and obj_dict['functions'] == {}
    has_edges = 'edges' in obj_dict and obj_dict['edges'] == {}
    has_spans = 'spans' in obj_dict and obj_dict['spans'] == {}
    all_three_empty = has_functions and has_edges and has_spans

    # Test 2: Verify _analysis_or_empty fallback path (exception case)
    from src.languages import erlang as erlang_mod
    with patch.object(erlang_mod, '_analyze_project', side_effect=RuntimeError("simulated failure")):
        result = erlang_mod._analysis_or_empty(tempfile.mkdtemp())
        fallback_dict = asdict(result)
        fallback_has_spans = 'spans' in fallback_dict and fallback_dict['spans'] == {}
        fallback_has_functions = 'functions' in fallback_dict and fallback_dict['functions'] == {}
        fallback_has_edges = 'edges' in fallback_dict and fallback_dict['edges'] == {}
        fallback_ok = fallback_has_spans and fallback_has_functions and fallback_has_edges

    # Bug confirmed only if EITHER direct construction OR fallback path lacks spans
    bug_confirmed = not all_three_empty or not fallback_ok

    if bug_confirmed:
        print(
            f'CONFIRMED — direct: functions={has_functions}, edges={has_edges}, '
            f'spans={has_spans} | fallback: functions={fallback_has_functions}, '
            f'edges={fallback_has_edges}, spans={fallback_has_spans}'
        )
    else:
        print(
            f'NOT CONFIRMED — ErlangAnalysis(functions={{}}, edges={{}}) '
            f'asdict shows all three: functions={has_functions}, edges={has_edges}, '
            f'spans={has_spans}. Fallback path also correct: '
            f'functions={fallback_has_functions}, edges={fallback_has_edges}, '
            f'spans={fallback_has_spans}. DataClass field(default_factory=dict) '
            f'always provides spans={{}}.'
        )

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
WARNING:root:ELP Erlang analysis unavailable for /tmp/tmp8yhhcvxf: simulated failure
NOT CONFIRMED — ErlangAnalysis(functions={}, edges={}) asdict shows all three: functions=True, edges=True, spans=True. Fallback path also correct: functions=True, edges=True, spans=True. DataClass field(default_factory=dict) always provides spans={}.
```
