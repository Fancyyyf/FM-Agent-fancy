# Bug Report: _is_metadata_sidecar

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/file_utils-py/_is_metadata_sidecar.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns True when file_path ends with a filename suffix belonging to the set of function-metadata sidecar suffixes; returns False when file_path ends with any other suffix.

---

### Actual Behavior

The function `_is_metadata_sidecar` is defined in the current scope. For any string `file_path` with no directory component, calling `_is_metadata_sidecar(file_path)` returns `True` if and only if there exists a suffix `s` in `_METADATA_SIDECAR_SUFFIXES` such that `file_path.endswith(s)` evaluates to `True`; otherwise returns `False`. The function has no side effects and does not modify `file_path`.

---

## Code Evidence

Line 3: return str(file_path).endswith(_METADATA_SIDECAR_SUFFIXES)

---

## Trigger Condition

The code calls str.endswith with a list, which raises TypeError, failing to return a boolean as required by the specification. The specification expects False for a file_path ending with a suffix not in the set, but the code crashes.

---

## How to trigger the bug

The probe tested `_is_metadata_sidecar` indirectly through the public `collect_file_names()` API. The trigger condition is factually incorrect: `_METADATA_SIDECAR_SUFFIXES` is defined as a **tuple** (`(".spec.json", ".info.json")`) on line 6 of `src/file_utils.py`, not a list. Python's `str.endswith()` method natively accepts tuples, returning `True` if the string ends with any suffix in the tuple. No `TypeError` is raised.

### Inputs

| Parameter | Value |
|-----------|-------|
| `file_path` | `"a.spec.json"` |
| `file_path` | `"a.info.json"` |
| `file_path` | `"a.py"` |
| `file_path` | `"b.txt"` |

### Expected (spec-correct) Output

`.spec.json` and `.info.json` files are filtered out; `a.py` and `b.txt` are included.

### Actual (buggy) Output

The function works correctly — `.spec.json` and `.info.json` files are filtered out as expected. No TypeError is raised because `_METADATA_SIDECAR_SUFFIXES` is a tuple.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.file_utils import collect_file_names
import tempfile, os

with tempfile.TemporaryDirectory() as tmpdir:
    open(os.path.join(tmpdir, "a.spec.json"), "w").close()
    open(os.path.join(tmpdir, "a.info.json"), "w").close()
    open(os.path.join(tmpdir, "a.py"), "w").close()
    result = collect_file_names(tmpdir)
    print(result)
# Output: ['a.py'] — sidecar files correctly filtered
```

---

## Probe Script

```python
import sys
import os
import tempfile

repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

from src.file_utils import collect_file_names

def run_probe():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create files: sidecar suffixes should be skipped by _is_metadata_sidecar
        sidecar_spec = os.path.join(tmpdir, "a.spec.json")
        sidecar_info = os.path.join(tmpdir, "a.info.json")
        regular_py   = os.path.join(tmpdir, "a.py")
        regular_txt  = os.path.join(tmpdir, "b.txt")

        for p in (sidecar_spec, sidecar_info, regular_py, regular_txt):
            open(p, "w").close()

        result = collect_file_names(tmpdir, output_path=os.path.join(tmpdir, "output.json"))

        # spec_claim: sidecar files (ending .spec.json / .info.json) should be filtered out
        # actual_behavior: _is_metadata_sidecar uses str.endswith(tuple) which works correctly
        expected = sorted(["a.py", "b.txt"])

        if result == expected:
            print("NOT CONFIRMED — _is_metadata_sidecar correctly returns boolean. "
                  "_METADATA_SIDECAR_SUFFIXES is a tuple, str.endswith(tuple) works in Python. "
                  "No TypeError occurs. The function satisfies its specification.")
        else:
            print(f"CONFIRMED — result: {result!r}, expected: {expected!r}")

try:
    run_probe()
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — _is_metadata_sidecar correctly returns boolean. _METADATA_SIDECAR_SUFFIXES is a tuple, str.endswith(tuple) works in Python. No TypeError occurs. The function satisfies its specification.
```
