# Bug Report: batch_extract

**Source file:** `src/languages/java.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dict mapping each absolute file path (str) to a list of (function_name: str, function_body: str) tuples for all discovered functions in Java source files under proj_dir. Each function_name is a canonicalized fully-qualified name using '::' as the separator with path-unsafe characters translated. Each function_body contains the complete source text of that function. Returns an empty dict if the CodeGraph backend cannot be initialized for the project.

---

### Actual Behavior

If an exception is raised during CodeGraphExtractor.from_proj_dir(proj_dir), the function batch_extract terminates with that exception and no further state holds. Otherwise, the function returns normally. Let result be the returned value. If the call from_proj_dir(proj_dir) returned a falsy value (None or otherwise), result is the empty dict {}. If it returned a truthy CodeGraphExtractor instance cg, result is the dict produced by cg.get_functions_by_file('java', proj_dir). This dict maps each absolute file path (str) for a Java source file in proj_dir to a list of (function_name: str, function_body: str) tuples. Each function_name is a canonicalized fully-qualified name using '::' as separator. No other keys or values are present, and proj_dir remains unchanged.

---

## Code Evidence

Line 3: cg = CodeGraphExtractor.from_proj_dir(proj_dir)

---

## Trigger Condition

The specification requires that batch_extract returns an empty dict if the CodeGraph backend cannot be initialized, which implies graceful handling of any initialization failure, including exceptions. The code does not catch exceptions from from_proj_dir, so if that call raises an exception (e.g., FileNotFoundError for a nonexistent directory), the function propagates the exception instead of returning an empty dict, violating the specification.

---

## How to trigger the bug

When `proj_dir` is `None`, `CodeGraphExtractor.from_proj_dir()` calls `os.path.abspath(proj_dir)`, which raises `TypeError: expected str, bytes or os.PathLike object, not NoneType`. Since `batch_extract` does not catch this exception, it propagates to the caller instead of returning an empty dict `{}` as the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `None` |

### Expected (spec-correct) Output

`{}`

### Actual (buggy) Output

`TypeError: expected str, bytes or os.PathLike object, not NoneType`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.java import batch_extract

result = batch_extract(None)
# actual (buggy) output: TypeError: expected str, bytes or os.PathLike object, not NoneType
# expected (correct) output: {}
```

---

## Probe Script

```python
"""Probe for bug: batch_extract() propagates exception instead of returning {} when from_proj_dir fails.

Spec claim: Returns an empty dict if the CodeGraph backend cannot be initialized for the project.
Actual: if from_proj_dir raises an exception (e.g. TypeError for None input), the function crashes.
Trigger: call batch_extract with an input that causes from_proj_dir to raise.
"""

import sys
import traceback

# FM-Agent self-validation guard: do NOT invoke run_pipeline, main.py, or any FM-Agent workflow.
# Test only the smallest relevant unit.

try:
    from src.languages.java import batch_extract
except Exception as e:
    print(f"ERROR: Failed to import batch_extract: {e}")
    sys.exit(1)

# The spec claims: "Returns an empty dict if the CodeGraph backend cannot be initialized"
# If from_proj_dir raises, the code does not catch it — the exception propagates.
# Test with None: os.path.abspath(None) raises TypeError.

all_passed = True
results = []

# Test case 1: proj_dir = None (causes TypeError in os.path.abspath)
try:
    actual = batch_extract(None)  # type: ignore — testing runtime behavior
    # If we got here, the function handled it (returned something)
    spec_expected = {}
    if actual == spec_expected:
        results.append(f"PASS: batch_extract(None) returned {{}} as spec requires")
    else:
        results.append(f"NOT CONFIRMED: batch_extract(None) returned {actual!r} instead of {{}}")
        all_passed = False
except TypeError as e:
    # Bug confirmed: exception propagated instead of returning {}
    results.append(f"CONFIRMED: batch_extract(None) raised TypeError: {e}")
    results.append("Spec requires returning {}; got exception instead")
    all_passed = False
except Exception as e:
    results.append(f"CONFIRMED: batch_extract(None) raised {type(e).__name__}: {e}")
    all_passed = False

# Test case 2: proj_dir with null byte (causes ValueError in os.path.abspath)
try:
    actual = batch_extract("/tmp/\x00test")  # type: ignore
    spec_expected = {}
    if actual == spec_expected:
        results.append(f"PASS: batch_extract('/tmp/\\x00test') returned {{}} as spec requires")
    else:
        results.append(f"NOT CONFIRMED: batch_extract('/tmp/\\x00test') returned {actual!r} instead of {{}}")
        all_passed = False
except ValueError as e:
    results.append(f"CONFIRMED: batch_extract('/tmp/\\x00test') raised ValueError: {e}")
    results.append("Spec requires returning {}; got exception instead")
    all_passed = False
except Exception as e:
    results.append(f"CONFIRMED: batch_extract('/tmp/\\x00test') raised {type(e).__name__}: {e}")
    all_passed = False

# Final verdict
for line in results:
    print(line)

if all_passed:
    print("NOT CONFIRMED — batch_extract correctly returns {} on all edge cases tested")
else:
    print("CONFIRMED — batch_extract propagates exception(s) instead of returning {}")
```

### Probe Output

```
CONFIRMED: batch_extract(None) raised TypeError: expected str, bytes or os.PathLike object, not NoneType
Spec requires returning {}; got exception instead
PASS: batch_extract('/tmp/\x00test') returned {} as spec requires
CONFIRMED — batch_extract propagates exception(s) instead of returning {}
```
