# Bug Report: _extracted_file_to_source_rel

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_extracted_file_to_source_rel.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the source-file relative path obtained by scanning the path
    components from right to left (skipping the filename) to find the
    extraction directory component. Once found, the component's last hyphen
    and its following extension are replaced by a dot and the extension
    (e.g., "loader-cpp" -> "loader.cpp"). The resulting filename is
    prepended with any leading directory prefix (components before the
    extraction directory component), and the function file component is
    dropped. If no extraction directory component is found (i.e., no
    component whose hyphen-suffix is in EXT_TO_LANG), falls back to using
    the immediate parent directory: its last hyphen is replaced with a dot
    (if a hyphen exists after the first character), and the result is
    prefixed with the parent directory of that parent, or used as is if no
    grandparent exists.
  - The returned path uses the OS-native path separator (os.sep).

---

### Actual Behavior

The function returns a relative path string `source_rel` that is the source file corresponding to `extracted_rel` under the extraction layout mapping. If the loop in lines 13-19 finds a component `comp = parts[i]` (with `i` ranging from `len(parts)-2` down to 0) that contains a hyphen at index `h>0` and `comp[h+1:]` is a key in `EXT_TO_LANG`, then the returned string is `os.path.join(src_dir, source_base)` (or `source_base` if `src_dir` is empty) where `src_dir = os.sep.join(parts[:i])` and `source_base = comp[:h] + '.' + comp[h+1:]`. In this case, `source_rel` is exactly the result of dropping all components of `extracted_rel` after the extraction directory component and replacing the extraction directory component `<base>-<ext>` with `<base>.<ext>`. If no such component is found, the fallback on lines 21-26 returns `os.path.join(src_dir, source_base)` (or `source_base`) where `func_dir = os.path.dirname(extracted_rel)`, `src_dir = os.path.dirname(func_dir)`, `dir_name = os.path.basename(func_dir)`, `h = dir_name.rfind('-')`, and `source_base = dir_name[:h] + '.' + dir_name[h+1:]` if `h > 0` else `dir_name`. Under the given pre-condition (that `extracted_rel` contains at least one extraction directory component whose suffix after the last hyphen matches a key in `EXT_TO_LANG`), the early return always executes, and the returned path satisfies the following formal property:  
Let `P = split(extracted_rel, sep)` where `sep` is the OS path separator. 
Then there exists an index `i` with `0  i  len(P)-2` such that for `c = P[i]`, `h = c.rfind('-')`, we have `h > 0  c[h+1:]  EXT_TO_LANG` and for all `j` with `i < j  len(P)-2`, either `P[j]` does not contain `-` or `P[j][rfind('-')+1:]  EXT_TO_LANG`. 
The returned value `R` satisfies `R = join(P[:i], c[:h] + '.' + c[h+1:])` where `join` is `os.sep.join` except that if `P[:i]` is empty, the result is just `c[:h] + '.' + c[h+1:]`.

---

## Code Evidence

Line 16: if hyphen > 0 and comp[hyphen + 1:] in EXT_TO_LANG:

---

## Trigger Condition

The specification requires any component whose suffix after the last hyphen is in EXT_TO_LANG to be treated as the extraction directory, without requiring the hyphen index to be greater than 0. The code's condition 'hyphen > 0' on line 16 excludes components like '-cpp' where the hyphen is at the start. For input '-cpp/func.cpp', the specification would identify '-cpp' as the extraction directory and return '.cpp', but the code's loop skips it, falls back to the immediate parent, and returns '-cpp', violating the specification.

---

## How to trigger the bug

The bug occurs when a path component representing an extraction directory starts with a hyphen (e.g., `-cpp`). The code's guard `hyphen > 0` on line 101 of `src/entry_reasoning_pipeline.py` incorrectly excludes such components, even though `rfind('-')` returns 0 (a valid index). The specification states that any component whose suffix after the last hyphen matches a key in `EXT_TO_LANG` should be treated as the extraction directory — it does not require the hyphen to be at position > 0.

### Inputs

| Parameter | Value |
|-----------|-------|
| extracted_rel | `-cpp/func.cpp` |

### Expected (spec-correct) Output

`.cpp`

### Actual (buggy) Output

`-cpp`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
from src.entry_reasoning_pipeline import _extracted_file_to_source_rel

input_path = "-cpp" + os.sep + "func.cpp"
result = _extracted_file_to_source_rel(input_path)
# actual (buggy) output: '-cpp'
# expected (correct) output: '.cpp'
```

---

## Probe Script

```python
import sys
import os

# Add the repo root to sys.path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.entry_reasoning_pipeline import _extracted_file_to_source_rel

    # Trigger: a path where a directory component starts with a hyphen
    # e.g., "-cpp/func.cpp" — the component "-cpp" has hyphen at index 0,
    # so "hyphen > 0" is False and the loop skips it.
    input_path = "-cpp" + os.sep + "func.cpp"
    actual = _extracted_file_to_source_rel(input_path)

    # Per spec: "-cpp" should be recognized as extraction dir,
    # producing empty base + ".cpp" => ".cpp"
    expected = ".cpp"

    # Bug is reproduced if actual != expected
    passed = actual != expected

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: '-cpp' | expected: '.cpp'
```
