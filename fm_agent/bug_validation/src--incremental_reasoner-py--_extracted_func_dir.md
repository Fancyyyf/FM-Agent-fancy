# Bug Report: _extracted_func_dir

**Source file:** `/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot/fm_agent/extracted_functions/src/incremental_reasoner-py/_extracted_func_dir.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the absolute directory path where extracted-function files for the source
    file identified by src_rel are (or would be) stored, following the naming convention
    that mirrors the extraction mapping
  - The returned path is formed by joining extracted_base, the directory portion of
    src_rel (if any), and a directory name derived from the basename of src_rel
  - The directory name derivation rule: the last dot in the source file basename is
    replaced with a hyphen; if the basename contains no dot, it is used as-is
  - Example: for src_rel = "src/engine/loader.cpp" and extracted_base pointing to
    extracted_functions/, the returned path ends with "src/engine/loader-cpp"
  - The returned path uses the platform-native path separator

---

### Actual Behavior

The function returns a string that is the path (constructed via os.path.join) to the directory where extracted-function files for the source file `src_rel` are stored. The directory consists of `extracted_base` followed by the directory part of `src_rel` (if any) and a derived directory name. The derived directory name is obtained from the base name of `src_rel` by locating the last dot at index > 0; if found, the dot is replaced with a hyphen (e.g., `"foo.ext"` becomes `"foo-ext"`), otherwise the base name is used unchanged (e.g., `"Makefile"` stays `"Makefile"`). No side effects occur, and no exceptions are raised under the pre-condition. Formally: Let `src_dir = os.path.dirname(src_rel)`, `src_base = os.path.basename(src_rel)`, `i = src_base.rfind('.')`. Define `dir_name = src_base[:i] + '-' + src_base[i+1:]` if `i > 0`, else `dir_name = src_base`. The return value `result` satisfies `result == os.path.join(extracted_base, src_dir, dir_name)`.

---

## Code Evidence

Line 13: if last_dot > 0:

---

## Trigger Condition

The specification states that the last dot in the basename is always replaced with a hyphen. For a basename that starts with a dot and has no other dots (e.g., '.gitignore'), the last dot is at index 0. The code only replaces the dot when last_dot > 0, so it leaves the basename unchanged, producing the directory name '.gitignore' instead of the expected '-gitignore'.

---

## How to trigger the bug

Describes the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `extracted_base` | `/fake/extracted_functions` |
| `src_rel` | `.gitignore` |

### Expected (spec-correct) Output

The returned path's basename should be `-gitignore` (the leading dot replaced with a hyphen).

### Actual (buggy) Output

The returned path's basename is `.gitignore` (the leading dot is not replaced, because `last_dot = 0` and the condition `last_dot > 0` is `False`).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.incremental_reasoner import _extracted_func_dir
import os

result = _extracted_func_dir("/fake/extracted_functions", ".gitignore")
print(os.path.basename(result))
# actual (buggy) output: '.gitignore'
# expected (correct) output: '-gitignore'
```

---

## Probe Script

```python
"""Probe for _extracted_func_dir: verify that the last dot in a basename is always
replaced with a hyphen, including when it is the first character (e.g. '.gitignore').

Bug claim: when the basename starts with a dot and has no other dots,
rfind('.') returns 0, but the code only replaces when last_dot > 0.
So '.gitignore' remains '.gitignore' instead of becoming '-gitignore'.

Spec claim (from [SPEC] post-condition):
  "the last dot in the source file basename is replaced with a hyphen"
"""
import sys
import os

_script_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(os.path.dirname(_script_dir))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

error_occurred = False
error_msg = ""

try:
    from src.incremental_reasoner import _extracted_func_dir

    extracted_base = "/fake/extracted_functions"
    src_rel = ".gitignore"

    actual = _extracted_func_dir(extracted_base, src_rel)

    actual_basename = os.path.basename(actual)

    # Spec says: the last dot is replaced with a hyphen
    # For ".gitignore", that means: "" + "-" + "gitignore" = "-gitignore"
    expected_basename = "-gitignore"

    passed = actual_basename != expected_basename  # True -> bug reproduced (mismatch)

    if passed:
        print(
            f"CONFIRMED — actual basename: {actual_basename!r} | "
            f"expected basename (per spec): {expected_basename!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — actual basename matched expected: {actual_basename!r}"
        )

except Exception as exc:
    error_occurred = True
    error_msg = str(exc)
    print(f"ERROR: {type(exc).__name__}: {exc}")
```

### Probe Output

```
CONFIRMED — actual basename: '.gitignore' | expected basename (per spec): '-gitignore'
```
