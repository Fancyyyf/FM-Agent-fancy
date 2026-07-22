# Bug Report: batch_extract

**Source file:** `src/languages/c-py/batch_extract.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dictionary mapping absolute file paths to lists of
    (function_name, function_body) tuples for every C function extracted
    from the project using codegraph analysis
  - Returns an empty dictionary {} when codegraph initialization fails

---

### Actual Behavior

The function returns a dictionary. If CodeGraphExtractor.from_proj_dir(proj_dir) returns a valid extractor object C (i.e., not None), the result equals C.get_functions_by_file('c', proj_dir): a dict mapping absolute file paths (strings) to lists of (func_name, body) tuples for all C files under proj_dir that could be successfully read; unreadable files are omitted. If initialization fails (C is None), the result is an empty dict {}. Formally: let C = CodeGraphExtractor.from_proj_dir(proj_dir). Then result = (C.get_functions_by_file('c', proj_dir) if C is not None else {}).

---

## Code Evidence

Line 4: return cg.get_functions_by_file("c", proj_dir) if cg else {}

---

## Trigger Condition

The code uses the truthiness of cg (if cg) to check whether initialization succeeded, but the specification of from_proj_dir only guarantees it returns an initialized CodeGraphExtractor or None; it does not guarantee the returned object is truthy. An initialized extractor could evaluate to False (e.g., if it defines __len__ to return 0), causing the function to erroneously return {} and violate the requirement to return the extracted functions when initialization succeeds.

---

## How to trigger the bug

The code at `src/languages/c.py:7` uses `if cg` (truthiness check) to decide whether `CodeGraphExtractor.from_proj_dir` succeeded, rather than an explicit `if cg is not None` check. Although `CodeGraphExtractor` currently does not define `__bool__` or `__len__` (so all instances are truthy by default), the contract of `from_proj_dir` only guarantees it returns either a `CodeGraphExtractor` or `None`. If any subclass or future modification adds a `__bool__` returning `False` or a `__len__` returning `0`, a successfully initialized extractor would be treated as a failure, causing `batch_extract` to incorrectly return `{}` instead of the extracted functions.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Any project directory with a valid `.codegraph/codegraph.db` where `from_proj_dir` returns a non-None but falsy `CodeGraphExtractor` |

### Expected (spec-correct) Output

`{'/fake/path.c': [('main', 'int main(void) {}\n')]}` — the extracted functions when initialization succeeded.

### Actual (buggy) Output

`{}` — empty dict because the truthiness guard `if cg` treated the non-None extractor as falsy.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.codegraph import CodeGraphExtractor
from src.languages.c import batch_extract

# Create a falsy-but-valid extractor
class FalsyExtractor(CodeGraphExtractor):
    def __bool__(self):
        return False
    def get_functions_by_file(self, lang_key, proj_dir=None):
        return {"/fake/path.c": [("main", "int main(void) {}\n")]}

# Monkey-patch from_proj_dir to return it
CodeGraphExtractor.from_proj_dir = classmethod(
    lambda cls, proj_dir: FalsyExtractor.__new__(FalsyExtractor)
)

result = batch_extract("/dummy/proj_dir")
# actual (buggy) output: {}
# expected (correct) output: {'/fake/path.c': [('main', 'int main(void) {}\n')]}
```

---

## Probe Script

```python
"""Probe: verify batch_extract uses truthiness check (if cg) instead of explicit None check."""

import sys
import os
from unittest.mock import MagicMock, patch

# Ensure repo root is on the path so the package entry point resolves.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.languages.codegraph import CodeGraphExtractor
    from src.languages.c import batch_extract
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Build a mock extractor that is deliberately non-None but falsy.
# The spec guarantees from_proj_dir returns CodeGraphExtractor | None.
# A truthiness-based guard (if cg) would incorrectly reject this object.
class FalsyExtractor(CodeGraphExtractor):
    def __bool__(self) -> bool:
        return False

    def get_functions_by_file(self, lang_key: str, proj_dir: str = None) -> dict:
        return {"/fake/path.c": [("main", "int main(void) {}\n")]}


# Expected result if the code used a proper `is not None` check:
# the mock extractor's get_functions_by_file result.
expected = {"/fake/path.c": [("main", "int main(void) {}\n")]}

# Monkey-patch from_proj_dir to return a non-None, falsy extractor.
original_from_proj_dir = CodeGraphExtractor.from_proj_dir

try:
    CodeGraphExtractor.from_proj_dir = classmethod(
        lambda cls, proj_dir: FalsyExtractor.__new__(FalsyExtractor)
    )
    actual = batch_extract("/dummy/proj_dir")
    passed = actual != expected  # bug reproduced if actual is {} instead of expected dict
finally:
    CodeGraphExtractor.from_proj_dir = original_from_proj_dir

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: {} | expected: {'/fake/path.c': [('main', 'int main(void) {}\n')]}
```
