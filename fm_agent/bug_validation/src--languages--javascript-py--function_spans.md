# Bug Report: function_spans

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/javascript-py/function_spans.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns None when the codegraph backend is unavailable for the project, or when the
    backend exists but does not index the given file.
  - Otherwise returns a list of (name, start_idx, end_idx) tuples, one per function
    defined in the file.
  - start_idx and end_idx are 0-indexed inclusive line numbers.
  - The list is ordered by appearance (ascending start_idx).
  - The list is empty when no functions are defined in the file.

---

### Actual Behavior

Returns a list of tuples (name: str, start_idx: int, end_idx: int) for each function found in the JavaScript source file, where start_idx and end_idx are 0-indexed inclusive line numbers; or None if the codegraph backend is unavailable (CodeGraphExtractor.from_proj_dir returns None) or the backend does not index the given file. No side effects. Formally: let r be the return value. r = None if CodeGraphExtractor.from_proj_dir(proj_dir) is None; otherwise, r = cg.get_function_spans('javascript', filepath) where cg is the returned codegraph instance, so r is either None or a list of tuples (name, s, e) with s  e, non-negative integers.

---

## Code Evidence

Line 8: return cg.get_function_spans('javascript', filepath) if cg else None

---

## Trigger Condition

Specification B requires the returned list to be ordered by appearance (ascending start_idx). The code simply passes through the list from get_function_spans without enforcing any order. If the backend returns an unsorted list, the code's output violates the ordering requirement. The counterexample shows a concrete scenario where the backend returns tuples in non-ascending start_idx order, causing a mismatch between A and B.

---

## How to trigger the bug

The bug claims that `function_spans` does not explicitly sort its results by `start_idx`, relying instead on the backend's behavior. However, the backend (`CodeGraphExtractor.get_function_spans` in `src/languages/codegraph.py`) already uses `ORDER BY start_line` in its SQL query (line 289), and the `start_line` column is `INTEGER NOT NULL`. SQLite always sorts integers numerically, so the backend inherently guarantees ascending `start_idx` order. The ordering requirement is satisfied by the backend, making the bug unreproducible in practice.

Furthermore, no JavaScript files exist in the codegraph database (only Python files are indexed), so the JavaScript `function_spans` handler always returns `None` (correctly, per the spec's availability clause). Even testing the identical code pattern with Python data (33 files with 2+ functions) confirmed all results are sorted.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Repository root (`/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot`) |
| `filepath` | Various Python source files with 2+ functions (no JS files exist in codegraph index) |
| Backend | `CodeGraphExtractor` via `src/languages/codegraph.py` |

### Expected (spec-correct) Output

A list of `(name, start_idx, end_idx)` tuples sorted by ascending `start_idx`, or `None` if the backend is unavailable.

### Actual (buggy) Output

The actual output always matches the expected output. `get_function_spans` returns rows ordered by `ORDER BY start_line` (SQL), producing sorted results. The wrapper `function_spans` passes these through without modification.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, '.')
from src.languages.codegraph import CodeGraphExtractor

cg = CodeGraphExtractor.from_proj_dir('.')
spans = cg.get_function_spans('python', 'src/languages/erlang.py')
# Check if spans are sorted by start_idx (index 1):
for i in range(1, len(spans)):
    if spans[i][1] < spans[i-1][1]:
        print('UNSORTED!')
        break
else:
    print('ALL SORTED')
# Output: ALL SORTED — the SQL ORDER BY start_line guarantees ordering.
```

---

## Probe Script

```python
"""Probe script for bug: function_spans not sorting results by start_idx.

Bug ID: src--languages--javascript-py--function_spans
Spec claim: The returned list must be ordered by appearance (ascending start_idx).
Actual behavior: The code passes through the list from get_function_spans without enforcing any order.

Attempt 3: Direct verification of the backend's ordering guarantee.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

from src.languages.codegraph import CodeGraphExtractor

def is_sorted_by_start_idx(spans):
    for i in range(1, len(spans)):
        if spans[i][1] < spans[i-1][1]:
            return False
    return True

proj_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

try:
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    if cg is None:
        print("ERROR: CodeGraphExtractor.from_proj_dir returned None")
        sys.exit(1)
    
    # Test get_function_spans directly for Python files (same backend, same ORDER BY)
    import sqlite3
    conn = sqlite3.connect(os.path.join(proj_dir, '.codegraph', 'codegraph.db'))
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT file_path FROM nodes
        WHERE kind IN ('function', 'method') AND language = 'python'
        ORDER BY file_path
    """)
    all_files = [row[0] for row in cur.fetchall()]
    conn.close()
    
    total_tested = 0
    unsorted_files = []
    
    for filepath in all_files:
        abs_path = os.path.join(proj_dir, filepath)
        if not os.path.exists(abs_path):
            continue
        spans = cg.get_function_spans("python", abs_path)
        if spans is None or len(spans) < 2:
            continue
        total_tested += 1
        if not is_sorted_by_start_idx(spans):
            unsorted_files.append((filepath, [s[1] for s in spans]))
            if len(unsorted_files) >= 1:
                break  # One unsorted file is enough to confirm
    
    if unsorted_files:
        print(f"CONFIRMED — get_function_spans returned unsorted results for: {unsorted_files[0]}")
    else:
        print(f"NOT CONFIRMED — get_function_spans returned sorted results for all {total_tested} files with 2+ functions.")
        print("The SQL query in get_function_spans uses 'ORDER BY start_line' with INTEGER column,")
        print("which guarantees numeric ordering. All language modules (javascript, python, go, etc.)")
        print("delegate to this same method without additional sorting, but the backend's ORDER BY")
        print("clause already satisfies the ordering requirement from the spec.")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — get_function_spans returned sorted results for all 33 files with 2+ functions.
The SQL query in get_function_spans uses 'ORDER BY start_line' with INTEGER column,
which guarantees numeric ordering. All language modules (javascript, python, go, etc.)
delegate to this same method without additional sorting, but the backend's ORDER BY
clause already satisfies the ordering requirement from the spec.
```
