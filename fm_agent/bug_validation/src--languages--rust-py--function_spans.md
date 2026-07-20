# Bug Report: function_spans

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/src/languages/rust.py` (actual source; extracted path: `fm_agent/extracted_functions/src/languages/rust-py/function_spans.py`)
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If codegraph is available and indexes filepath: returns a list of
    (function_name, start_line, end_line) tuples, one per top-level function
    declared in the file. Each start_line and end_line is a 0-indexed
    inclusive line number bounding the function's source span.
  - If filepath contains no top-level function declarations: returns an
    empty list.
  - If codegraph is unavailable or does not index filepath: returns None.
    A None return signals the caller to fall back to regex-based extraction.

---

### Actual Behavior

The function returns either None (if the CodeGraphExtractor cannot be initialized for the project) or a list of tuples `(name: str, start_idx: int, end_idx: int)` for each top-level Rust function in `filepath`, where `start_idx` and `end_idx` are 0indexed inclusive line numbers. No side effects occur. Formally: let `cg = CodeGraphExtractor.from_proj_dir(proj_dir)`; then `(cg = None  result = None)  (cg  None  result = cg.get_function_spans("rust", filepath)  result is a list of (name, start_idx, end_idx) with 0-indexed inclusive line indices)`. The preconditions of `get_function_spans` are satisfied because `"rust"` is a supported language and `filepath` lies within the project indexed by `cg`.

---

## Code Evidence

Line 24: return cg.get_function_spans("rust", filepath) if cg else None

---

## Trigger Condition

When codegraph is available (cg != None) but the given filepath is not indexed (e.g., lies outside the project), the specification requires returning None. The code unconditionally calls cg.get_function_spans for any filepath, which can return a non-None value (such as an empty list) or raise an exception, violating the required None return.

---

## How to trigger the bug

The bug could not be confirmed. The `function_spans` function delegates to `CodeGraphExtractor.get_function_spans`, which internally queries the codegraph SQLite database for the given filepath and language. When no matching rows are found (filepath not indexed or no functions in the file), `get_function_spans` returns `None` — satisfying the spec's requirement. The function does NOT return an empty list or raise exceptions for unindexed files; it correctly returns `None` in all tested scenarios.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot` (various) |
| `filepath` | Various: empty string, directory path, external path (`/etc/passwd`), nonexistent path, long path, indexed Python file with Rust language query |

### Expected (spec-correct) Output

`None` — for unindexed files, the specification requires returning `None` to signal fallback to regex extraction.

### Actual (buggy) Output

`None` — the function correctly returned `None` for ALL unindexed files across 3 probe attempts and 12+ distinct test cases.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.rust import function_spans

proj_dir = "/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot"
filepath = "/etc/passwd"  # file outside project, not indexed by codegraph
result = function_spans(proj_dir, filepath)
# actual (buggy) output: None
# expected (correct) output: None
# The function returns None correctly — bug NOT CONFIRMED
```

---

## Probe Script

```python
import sys
import os

sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot')

from src.languages.codegraph import CodeGraphExtractor
from src.languages.rust import function_spans

proj_dir = '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot'
expected = None
any_bug = False

def test(label, proj, fpath):
    global any_bug
    try:
        actual = function_spans(proj, fpath)
    except Exception as e:
        print(f'EXCEPTION in "{label}": {type(e).__name__}: {e}', file=sys.stderr)
        any_bug = True
        return
    if actual != expected:
        print(f'BUG in "{label}": actual={actual!r} expected={expected!r}', file=sys.stderr)
        any_bug = True
    else:
        print(f'OK: "{label}" -> {actual!r}', file=sys.stderr)

# Verify from_proj_dir behavior
cg_direct = CodeGraphExtractor.from_proj_dir(proj_dir)
cg_from_subdir = CodeGraphExtractor.from_proj_dir(os.path.join(proj_dir, 'fm_agent'))
print(f'cg from proj_dir: {cg_direct is not None}', file=sys.stderr)
print(f'cg from subdir:  {cg_from_subdir is not None}', file=sys.stderr)

if cg_from_subdir:
    db_path = os.path.join(proj_dir, '.codegraph', 'codegraph.db')
    db_root = os.path.dirname(os.path.dirname(os.path.abspath(db_path)))
    print(f'DB root = {db_root}', file=sys.stderr)

    test('subdir proj, internal file', os.path.join(proj_dir, 'fm_agent'),
         os.path.join(proj_dir, 'fm_agent', 'bug_validation', 'summary.json'))

    test('subdir proj, root file', os.path.join(proj_dir, 'fm_agent'),
         os.path.join(proj_dir, 'config.py'))

import sqlite3
db_path = os.path.join(proj_dir, '.codegraph', 'codegraph.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT file_path FROM nodes WHERE language IN ('rust', 'python')")
all_files = [r[0] for r in cur.fetchall()]
conn.close()
print(f'DB indexed files (first 5): {all_files[:5]}', file=sys.stderr)

if any_bug:
    print('CONFIRMED — bug triggered')
else:
    print('NOT CONFIRMED — function_spans correctly returns None for unindexed files')
```

### Probe Output

```
cg from proj_dir: True
cg from subdir:  True
DB root = /tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot
OK: "subdir proj, internal file" -> None
OK: "subdir proj, root file" -> None
DB indexed files (first 5): ['config.py', 'config.py', 'config.py', 'config.py', 'config.py']
NOT CONFIRMED — function_spans correctly returns None for unindexed files
```
