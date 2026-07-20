# Bug Report: call_edges

**Source file:** `src/languages/typescript-py/call_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When a codegraph backend initializes successfully from proj_dir, returns a dict whose keys are (caller_stem, caller_module) pairs — where caller_stem is a function‑level identifier and caller_module is the containing module identifier — and whose values are sets of callee function stem strings that the corresponding caller directly invokes within the project's TypeScript source
- When no codegraph backend is available, returns None
- Every callee stem in the returned value sets corresponds to a function reachable from at least one TypeScript source file in the project

---

### Actual Behavior

If the function returns normally, it returns either None (when no compatible codegraph backend exists for proj_dir) or a dictionary mapping each caller identity tuple (caller_stem, caller_module) to the set of callee stem strings for all call relationships detected in the TypeScript source files of proj_dir. If an exception is raised by CodeGraphExtractor.from_proj_dir or CodeGraphExtractor.get_call_edges, the function does not return normally and propagates the exception.

---

## Code Evidence

Line 4: `return cg.get_call_edges("typescript") if cg else None`

---

## Trigger Condition

The specification requires that every callee stem corresponds to a function reachable from at least one TypeScript source file in the project. CodeGraphExtractor.get_call_edges may include callee stems for external functions that are not defined in any project source file, causing the returned dictionary to violate this condition.

---

## How to trigger the bug

The function `get_call_edges` in `CodeGraphExtractor` does not validate that callee stems correspond to functions defined in project TypeScript source files. When a project contains a symlinked TypeScript file pointing to an external location (outside the project directory), codegraph indexes the symlinked file and resolves call edges to functions defined in that external file. The function includes these external callee stems in the result, violating the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `/tmp/ts_test_proj` (contains main.ts importing from symlinked external.ts) |

### Expected (spec-correct) Output

An empty dict `{}` (or dict where all callee stems correspond to project-source functions only)

### Actual (buggy) Output

`{'main-ts::compute': {'linked::external-ts::externalHelper'}}` — includes `externalHelper` from `/tmp/external_ts/external.ts` which is outside the project, only reachable via symlink

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Create a project directory with a TypeScript file that imports from a symlinked external file.
2. Run `codegraph init` in the project directory.
3. Call `call_edges(proj_dir)` from `src.languages.typescript`.
4. Observe that callee stems include functions from the external symlinked file.

```python
from src.languages.typescript import call_edges
result = call_edges('/tmp/ts_test_proj')
# actual (buggy) output: {'main-ts::compute': {'linked::external-ts::externalHelper'}}
# expected (correct) output: {} or only project-source callees
```

---

## Probe Script

```python
"""Probe script for bug src--languages--typescript-py--call_edges.

The spec requires that every callee stem in the returned call_edges dict
corresponds to a function reachable from at least one TypeScript source file
in the project. But CodeGraphExtractor.get_call_edges may include callee
stems for external functions that are not defined in any project source file.

This probe tests with a project where a TypeScript file imports from a
symlinked external TypeScript file. If the callee is included in the result,
the bug is confirmed.
"""

import os
import sys

# Ensure the repo root is on the import path
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.languages.typescript import call_edges
except ImportError as e:
    print(f'ERROR: could not import src.languages.typescript: {e}')
    sys.exit(1)

# Use a pre-prepared test project at /tmp/ts_test_proj
# It contains:
#   main.ts — imports externalHelper from ./linked/external
#   linked/external.ts — symlink to /tmp/external_ts/external.ts (OUTSIDE project)
# A codegraph index has been built for this project.

TEST_PROJ_DIR = '/tmp/ts_test_proj'
EXTERNAL_FILE = '/tmp/external_ts/external.ts'

passed = False
actual = None
error_msg = None

try:
    actual = call_edges(TEST_PROJ_DIR)

    if actual is None:
        print('NOT CONFIRMED — call_edges returned None (no codegraph backend)')
        sys.exit(0)

    if not actual:
        print('NOT CONFIRMED — call_edges returned empty dict')
        sys.exit(0)

    # Check if any callee FQN refers to the external file
    for caller_fqn, callee_set in actual.items():
        for callee_fqn in callee_set:
            if 'external' in callee_fqn.lower():
                from src.languages.codegraph import CodeGraphExtractor
                cg = CodeGraphExtractor.from_proj_dir(TEST_PROJ_DIR)
                if cg:
                    import sqlite3
                    conn = sqlite3.connect(cg._db)
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT file_path FROM nodes WHERE kind IN ('function','method') AND name='externalHelper'"
                    )
                    rows = cur.fetchall()
                    conn.close()
                    for (file_path,) in rows:
                        abs_path = os.path.join(TEST_PROJ_DIR, file_path)
                        real_path = os.path.realpath(abs_path)
                        if real_path == os.path.realpath(EXTERNAL_FILE):
                            passed = True
                            print(
                                f'CONFIRMED — callee "{callee_fqn}" resolved to '
                                f'external file {real_path} (not in project)'
                            )
                break
        if passed:
            break

    if not passed:
        print('NOT CONFIRMED — no external callee stems found in result')

except Exception as e:
    error_msg = f'{type(e).__name__}: {e}'
    print(f'ERROR: {error_msg}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — callee "linked::external-ts::externalHelper" resolved to external file /tmp/external_ts/external.ts (not in project)
```
