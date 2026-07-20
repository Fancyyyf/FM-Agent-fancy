# Bug Report: _analyze_project_uncached

**Source file:** `fm_agent/extracted_functions/src/languages/erlang-py/_analyze_project_uncached.py`
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
    (including cases where no valid function symbols are returned for any file)

---

### Actual Behavior

After execution of the function _analyze_project_uncached, the program state is one of the following: (1) If _erlang_files(proj_dir) returns an empty list, the function returns early with an ErlangAnalysis built from empty functions and empty edges. (2) If _erlang_files(proj_dir) returns a nonempty list but any operation (reading a source file with Path.read_text, initializing the ElpClient, or making a client request) raises an exception, that exception propagates to the caller; no ErlangAnalysis is returned. (3) Otherwise, all files are processed via ElpClient and the function returns an ErlangAnalysis containing the functions and edges dictionaries built from the document symbols of the .erl files. During processing, malformed function symbols (those that cause _function_id to raise ValueError) are logged as warnings and ignored. Formal logic: Let FILES = _erlang_files(os.path.abspath(proj_dir)). post(proj_dir)  [ FILES = []    return ErlangAnalysis(functions={}, edges={}) ]  [ FILES  []  ( path  FILES . read_text(path) fails  ElpClient(proj_dir) init/request fails)  raise I/O or communication error ]  [ FILES  []  no read/client error  return ErlangAnalysis(functions=F, edges=E) where F and E are populated from successfully resolved function symbols across all FILES, with malformed symbols skipped and logged ].

---

## Code Evidence

Line 4: if not files:
Line 5:     return ErlangAnalysis(functions={}, edges={})
Line 8: spans: dict[str, list[tuple[str, int, int]]] = {}
Line 14: server_info = client.initialize(files[0], sources[files[0]])

---

## Trigger Condition

The specification requires the returned ErlangAnalysis to contain .spans and .server_info attributes, populated respectively with per-file span data and server initialization info. The code neither populates the spans dict nor stores or returns server_info; the early return (Line 5) also omits both attributes. Therefore, for any input (including an empty directory and one containing .erl files), the returned object violates the required attributes.

---

## How to trigger the bug

The bug report claims that the early return at line 491 (`return ErlangAnalysis(functions={}, edges={})`) omits the `.spans` and `.server_info` attributes from the returned object. However, the `ErlangAnalysis` dataclass defines defaults for both fields:

- `spans: dict[str, list[tuple[str, int, int]]] = field(default_factory=dict)`
- `server_info: dict | None = None`

Therefore, constructing `ErlangAnalysis(functions={}, edges={})` produces an object with `.spans = {}` and `.server_info = None`. Both attributes exist and have reasonable types. The bug could not be reproduced in 3 probe attempts.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | A temporary empty directory (no `.erl` files) |

### Expected (spec-correct) Output

`ErlangAnalysis` with `.spans` (an empty dict) and `.server_info` (None, since no ELP server was started)

### Actual (buggy) Output

`ErlangAnalysis` with `.spans = {}` and `.server_info = None` — identical to expected; the dataclass defaults handle the early return correctly.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from src.languages.erlang import _analyze_project_uncached

with tempfile.TemporaryDirectory() as tmpdir:
    result = _analyze_project_uncached(tmpdir)
    print('spans:', result.spans)          # actual (buggy) output: {}
    print('server_info:', result.server_info)  # actual (buggy) output: None
    # expected (correct) output: .spans is dict ({}), .server_info is None
    # dataclass defaults provide both — bug not reproducible
```

---

## Probe Script

```python
import sys
import tempfile

try:
    from src.languages.erlang import _analyze_project_uncached
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Attempt 3: Test empty directory — verify span/server_info existence
with tempfile.TemporaryDirectory() as tmpdir:
    try:
        result = _analyze_project_uncached(tmpdir)
    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)

    # Bug claim: early return ErlangAnalysis(functions={}, edges={}) omits spans/server_info
    # Dataclass defaults: spans=field(default_factory=dict), server_info=None
    missing = []
    if not hasattr(result, 'spans'):
        missing.append('spans')
    if not hasattr(result, 'server_info'):
        missing.append('server_info')
    if hasattr(result, 'spans') and not isinstance(result.spans, dict):
        missing.append('spans(wrong_type)')

    if missing:
        print(f'CONFIRMED — missing/malformed attributes: {missing}')
    else:
        print(f'NOT CONFIRMED — all required attributes present (spans={result.spans!r}, server_info={result.server_info!r})')
```

### Probe Output

```
NOT CONFIRMED — all required attributes present (spans={}, server_info=None)
```
