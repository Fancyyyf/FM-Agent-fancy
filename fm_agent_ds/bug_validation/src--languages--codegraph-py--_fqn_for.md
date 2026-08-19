# Bug Report: _fqn_for

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/codegraph-py/_fqn_for.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string composed of: (1) the non-empty segments of the file_path directory when split by '/', (2) the basename of file_path with its last occurrence of '.' replaced by '-' (unmodified when the basename contains no '.'), and (3) name. All components are joined by '::'. The returned string contains at least two '::' separators and no component in the returned string is empty.

---

### Actual Behavior

The function returns a string FQN formed by normalizing `file_path` (replacing `os.sep` with '/'), extracting its directory and base name via `os.path.dirname` and `os.path.basename`, then replacing the last '.' in the base name (if any) with '-' to produce a dashed base name. The final result is `'::'.join([comp for comp in dirname(normalized).split('/') if comp] + [dashed_basename, name])`, where `normalized = file_path.replace(os.sep, '/')`, `dirname = os.path.dirname(normalized)`, `base = os.path.basename(normalized)`, and `dashed_basename = base[:last_dot] + '-' + base[last_dot+1:] if (last_dot := base.rfind('.')) > 0 else base`. No side effects occur, and no exceptions are raised for the given valid pre-conditions.

---

## Code Evidence

Line 14: dashed = base[:last_dot] + "-" + base[last_dot + 1:] if last_dot > 0 else base

---

## Trigger Condition

The specification requires that the last occurrence of '.' in the basename is replaced by '-' regardless of its position. The code only performs the replacement when last_dot > 0, excluding the case where the dot is the first character (e.g., basename '.hidden'). For input file_path='dir/.hidden', name='func', the code returns 'dir::.hidden::func' while the spec would require 'dir::-hidden::func', violating the specification.

---

## How to trigger the bug

The condition `last_dot > 0` on line 14 (line 206 in the full source `src/languages/codegraph.py`) incorrectly excludes basenames where the last `.` is the first character (position 0). When `base = '.hidden'`, `base.rfind('.')` returns `0`, which fails the `> 0` guard, so the `.` is preserved instead of being replaced with `-`.

### Inputs

| Parameter | Value |
|-----------|-------|
| file_path | `'dir/.hidden'` |
| name | `'func'` |

### Expected (spec-correct) Output

`'dir::-hidden::func'`

### Actual (buggy) Output

`'dir::.hidden::func'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, os.path.abspath('.'))
from src.languages.codegraph import _fqn_for

actual   = _fqn_for('dir/.hidden', 'func')
expected = 'dir::-hidden::func'
print(f'actual: {actual!r}')    # 'dir::.hidden::func'
print(f'expected: {expected!r}')  # 'dir::-hidden::func'
```

---

## Probe Script

```python
"""Probe script for bug src--languages--codegraph-py--_fqn_for.

The bug: _fqn_for uses `last_dot > 0` to guard dot replacement, which
excludes basenames where the dot is the first character (e.g. '.hidden').
The spec requires replacing the last '.' with '-' regardless of its position.
"""
import sys
import os

# Ensure the repo root is on sys.path so the package entry point resolves.
# probe is at fm_agent/bug_validation/probe_...py → 3 levels up = repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.languages.codegraph import _fqn_for

    # Trigger condition: file_path='dir/.hidden', name='func'
    actual = _fqn_for("dir/.hidden", "func")

    # Spec-correct: last '.' in basename '.hidden' → '-hidden', yielding 'dir::-hidden::func'
    expected = "dir::-hidden::func"

    # The bug exists if actual != expected
    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: 'dir::.hidden::func' | expected: 'dir::-hidden::func'
```
