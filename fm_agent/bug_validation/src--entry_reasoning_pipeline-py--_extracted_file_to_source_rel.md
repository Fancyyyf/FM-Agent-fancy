# Bug Report: _extracted_file_to_source_rel

**Source file:** `/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot/fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_extracted_file_to_source_rel.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the source-file relative path obtained by replacing the last hyphen
    in the parent directory name with a dot and stripping the function-name file
    component
  - When the parent directory name contains no hyphen after its first character,
    the directory name is returned unchanged and no parent directory prefix is
    prepended
  - The returned path uses "/" as the path separator

---

### Actual Behavior

If the input extracted_rel satisfies the pre-condition (a relative path whose last component is a function file and whose immediate parent directory name was formed by replacing the last '.' of a source filename with '-'), the function returns a relative path that is the original source file: it is the grandparent directory (if any) joined with a name obtained from the parent directory name by reversing the replacementlocating the last hyphen (which is guaranteed to exist and have index > 0) and substituting it with a dot. Formally, let func_dir = os.path.dirname(extracted_rel), src_dir = os.path.dirname(func_dir), dir_name = os.path.basename(func_dir), and h = dir_name.rfind('-'). If h > 0 then source_base = dir_name[:h] + '.' + dir_name[h+1:]; else source_base = dir_name. Then return = os.path.join(src_dir, source_base) if src_dir != '' else source_base. Under the pre-condition, h > 0 and the transformation recovers the original source filename, so return = (os.path.dirname(func_dir) + os.sep if os.path.dirname(func_dir) else '') + (the source filename before extraction).

---

## Code Evidence

Line 13: if hyphen > 0:

---

## Trigger Condition

When the parent directory name starts with a hyphen (e.g., '-loader' from a source file '.loader'), hyphen is 0, so the code treats it as having no hyphen after the first character. It returns 'proj/-loader', but the specification says: if no hyphen after first character, return the directory name unchanged with no parent prefix, yielding just '-loader'. Thus the code incorrectly retains the parent directory and fails to handle this edge case.

---

## How to trigger the bug

The function reverses the extraction layout: a source filename like `loader.cpp` becomes directory `loader-cpp` during extraction, and `_extracted_file_to_source_rel` reverses this by replacing the last hyphen with a dot. However, when the original source filename starts with a dot (e.g., `.loader`), the extraction directory becomes `-loader`. The `rfind('-')` returns 0, and the condition `if hyphen > 0` evaluates to `False`. The `else` branch sets `source_base = dir_name` but still prepends `src_dir` via `os.path.join`, violating the spec clause that says the directory name should be returned unchanged with NO parent prefix prepended.

### Inputs

| Parameter | Value |
|-----------|-------|
| entry_func (via `_entry_func_source_rel`) | `proj::-loader::some_func` |
| extracted_rel (derived) | `proj/-loader/some_func` |
| func_dir | `proj/-loader` |
| dir_name | `-loader` |
| rfind('-') | `0` |

### Expected (spec-correct) Output

`-loader`

### Actual (buggy) Output

`proj/-loader`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.entry_reasoning_pipeline import _entry_func_source_rel

# _entry_func_source_rel calls _extracted_file_to_source_rel internally
result = _entry_func_source_rel("proj::-loader::some_func")
# actual (buggy) output: 'proj/-loader'
# expected (correct) output: '-loader'
```

---

## Probe Script

```python
import sys
import os

# Add repo root to sys.path so the 'src' package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.entry_reasoning_pipeline import _entry_func_source_rel

    # Test: parent directory starts with a hyphen (e.g. '-loader' from source '.loader')
    # The FQN "proj::-loader::some_func" is split by "::" then joined to form a path.
    # extracted_rel = "proj/-loader/some_func"
    # func_dir = "proj/-loader", dir_name = "-loader", rfind('-') = 0
    # hyphen > 0 is False -> source_base = '-loader'
    # Returns os.path.join("proj", "-loader") = "proj/-loader"
    # Spec says: when no hyphen after first character, return dir_name unchanged
    # with NO parent prefix -> expected = "-loader"

    entry_func = "proj::-loader::some_func"

    actual = _entry_func_source_rel(entry_func)
    expected = '-loader'

    passed = actual != expected

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: 'proj/-loader' | expected: '-loader'
```
