# Bug Report: _entry_func_source_rel

**Source file:** `/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot/fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_entry_func_source_rel.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a source-file relative path (using "/" separators) derived by
    reversing the FQN-to-extracted-file-path mapping convention, regardless of
    the host OS path separator
  - The returned path identifies the source file that contains the function
    named by entry_func

---

### Actual Behavior

The function returns a string representing the project-relative path to the source file that defined `entry_func`, using forward slashes ('/') as separators. The path is obtained by splitting `entry_func` on '::', joining all components into a relative extracted-file path, reversing the extraction naming convention (converting the second-to-last component `<basename>-<ext>` back to `<basename>.<ext>`, and removing the final function-name component), and finally replacing any backslashes with forward slashes (though the intermediate call already guarantees '/' separators). Formally:

Let C = entry_func.split('::'), k = len(C)  2, and let extracted_rel = os.path.join(*C).
Let intermediate = _extracted_file_to_source_rel(extracted_rel) (which already uses '/' as separator).
Then the return value R = intermediate.replace(os.sep, '/').

Given the pre-condition on `entry_func`:
- C[-1] is a function name.
- C[-2] is an extraction directory name of the form `<basename>-<ext>` (where `<basename>` and `<ext>` are non-empty strings and `<ext>` contains no '.').

Then R satisfies:
R = '/'.join(C[0], C[1], ..., C[k-3], '<basename>.<ext>') with the convention that if k=2 the path is just '<basename>.<ext>'.

In other words, R is the original source file relative path with '/' separator, corresponding to the FQN, and contains no function-name component.

---

## Code Evidence

Line 8: extracted_rel = os.path.join(*entry_func.split("::"))
Line 9: return _extracted_file_to_source_rel(extracted_rel).replace(os.sep, "/")

---

## Trigger Condition

The code does not handle FQNs with a leading "::" separator, which produces an empty first component. When joined with os.path.join, this yields an absolute path (e.g., "/loader.cpp" on Unix) instead of a project-relative path, violating the specification that requires a relative path.

---

## How to trigger the bug

The claimed trigger condition — that a leading "::" in the FQN would produce an absolute path via `os.path.join` — does not reproduce on this platform (Linux). CPython's `os.path.join` explicitly ignores empty string components. When `entry_func = "::loader-cpp::loadData"` is split and joined, `os.path.join("", "loader-cpp", "loadData")` produces `"loader-cpp/loadData"` — still a relative path. The `_extracted_file_to_source_rel` call then correctly reverses this to `"loader.cpp"`, satisfying the specification's requirement for a relative path.

### Inputs

| Parameter | Value |
|-----------|-------|
| entry_func (leading ::) | `"::loader-cpp::loadData"` |
| entry_func (leading :: with src) | `"::src::loader-cpp::loadData"` |
| entry_func (leading :: general) | `"::module-py::loadData"` |

### Expected (spec-correct) Output

`"loader.cpp"`, `"src/loader.cpp"`, `"module.py"` — all relative paths with `/` separators.

### Actual (buggy) Output

`"loader.cpp"`, `"src/loader.cpp"`, `"module.py"` — all relative paths with `/` separators. Identical to expected.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, sys
sys.path.insert(0, os.path.abspath('.'))
from src.entry_reasoning_pipeline import _entry_func_source_rel

# Bug should produce absolute path like "/loader.cpp"
# but instead produces relative path "loader.cpp"
result = _entry_func_source_rel("::loader-cpp::loadData")
print(repr(result))   # 'loader.cpp' — relative, NOT absolute
print(os.path.isabs(result))  # False — bug NOT reproduced
```

---

## Probe Script

```python
import os
import sys

# Script is at fm_agent/bug_validation/probe_...py; repo root is 3 levels up
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from src.entry_reasoning_pipeline import _entry_func_source_rel
except ImportError as e:
    print(f'ERROR (import): {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

TEST_CASES = [
    ("::loader-cpp::loadData", "loader.cpp",
     "Leading :: with two components after"),
    ("::src::loader-cpp::loadData", "src/loader.cpp",
     "Leading :: with three components after"),
    ("::module-py::loadData", "module.py",
     "Leading :: general case"),
]

confirmed = False
for entry_func, expected_rel, desc in TEST_CASES:
    try:
        actual = _entry_func_source_rel(entry_func)
        is_absolute = os.path.isabs(actual)
        is_correct = actual == expected_rel
        bug_reproduced = is_absolute or not is_correct

        if bug_reproduced:
            print(f'BUG [{desc}] (is_absolute={is_absolute}, is_correct={is_correct})')
            print(f'  entry_func  = {entry_func!r}')
            print(f'  actual      = {actual!r}')
            print(f'  expected    = {expected_rel!r}')
            confirmed = True
        else:
            print(f'OK [{desc}]: {entry_func!r} -> {actual!r} (relative, correct)')
    except Exception as e:
        print(f'ERROR [{desc}]: {e}')

if confirmed:
    print('CONFIRMED — buggy behavior detected')
else:
    print('NOT CONFIRMED — all test cases returned correct relative paths')
```

### Probe Output

```
OK [Leading :: with two components after]: '::loader-cpp::loadData' -> 'loader.cpp' (relative, correct)
OK [Leading :: with three components after]: '::src::loader-cpp::loadData' -> 'src/loader.cpp' (relative, correct)
OK [Leading :: general case]: '::module-py::loadData' -> 'module.py' (relative, correct)
NOT CONFIRMED — all test cases returned correct relative paths
```
