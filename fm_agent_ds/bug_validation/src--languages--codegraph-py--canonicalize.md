# Bug Report: canonicalize

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/codegraph-py/canonicalize.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string where every occurrence of '/' has been replaced with '_'. The returned string is safe for use as a filesystem path component and as a segment in a '::'-delimited fully-qualified name. If func_name is falsy, returns it unchanged.

---

### Actual Behavior

The function returns a string `r` such that: (1) if `func_name` is empty, `r` is empty; (2) if `func_name` contains any character from the set `_UNSAFE`, `r` is the result of applying the translation table `_SAFE_REPLACE` to `func_name` via `str.translate`, and `r` contains no character from `_UNSAFE`; (3) otherwise (i.e., `func_name` is non-empty and contains no character from `_UNSAFE`), `r` is identical to `func_name`. Formal logic: let `U` be the set of characters in `_UNSAFE`. Then the returned string `r` satisfies:
`(func_name == "" → r == "") ∧ ((∃c ∈ U: c ∈ func_name) → (r == func_name.translate(_SAFE_REPLACE) ∧ ¬∃c ∈ U: c ∈ r)) ∧ (¬∃c ∈ U: c ∈ func_name → r == func_name)`.

---

## Code Evidence

Line 12: for ch in _UNSAFE:
Line 14: return func_name.translate(_SAFE_REPLACE)

---

## Trigger Condition

The code only sanitizes characters that appear in the global _UNSAFE set. The specification requires that every '/' is replaced with '_'. If '/' is not included in _UNSAFE, an input containing '/' such as 'operator/' will be returned unchanged, violating the required replacement.

---

## How to trigger the bug

The reported bug was a false positive — the verification tool analysed only the extracted function body and did not see the module-level globals `_UNSAFE = set("/")` and `_SAFE_REPLACE = str.maketrans({"/": "_"})` defined at lines 23-24 of the original source file `src/languages/codegraph.py`. When the full module is imported, '/' IS in `_UNSAFE` and the function correctly replaces it with '_'. All test inputs containing '/' are properly sanitized.

### Inputs

| Parameter | Value |
|-----------|-------|
| func_name | `"operator/"` |
| func_name | `"ns::operator/"` |
| func_name | `"a/b/c"` |
| func_name | `"normal_function"` |
| func_name | `""` (empty string) |

### Expected (spec-correct) Output

- `"operator/"` → `"operator_"`
- `"ns::operator/"` → `"ns::operator_"`
- `"a/b/c"` → `"a_b_c"`
- `"normal_function"` → `"normal_function"`
- `""` → `""`

### Actual (buggy) Output

- `"operator/"` → `"operator_"` (matches expected)
- `"ns::operator/"` → `"ns::operator_"` (matches expected)
- `"a/b/c"` → `"a_b_c"` (matches expected)
- `"normal_function"` → `"normal_function"` (matches expected)
- `""` → `""` (matches expected)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.codegraph import canonicalize

# The reported bug claims '/' may not be in _UNSAFE and inputs with '/'
# won't be sanitized. But actual _UNSAFE = set("/"), so:
actual = canonicalize("operator/")
expected = "operator_"
print(f"actual={actual!r}, expected={expected!r}, matches={actual == expected}")
# actual (buggy) output: 'operator_'
# expected (correct) output: 'operator_'
```

---

## Probe Script

```python
import sys
import tempfile
import os
from pathlib import Path

# Ensure the repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Create a fresh temporary directory for the probe workspace
# (as required by FM-Agent self-validation guard)
_probe_workspace = tempfile.mkdtemp(prefix="canonicalize_probe_")

try:
    from src.languages.codegraph import canonicalize
except ImportError as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: Cannot import canonicalize: {e}')
    sys.exit(1)

test_inputs = [
    ("operator/", "operator_"),
    ("ns::operator/", "ns::operator_"),
    ("normal_function", "normal_function"),
    ("", ""),
    ("a/b/c", "a_b_c"),
]

all_passed = True
details = []

for input_val, expected in test_inputs:
    actual = canonicalize(input_val)
    if actual == expected:
        details.append(f"OK: {input_val!r} -> {actual!r}")
    else:
        details.append(f"FAIL: {input_val!r} -> {actual!r} (expected {expected!r})")
        all_passed = False

# The bug claim: '/' might not be in _UNSAFE, so inputs with '/' would not be sanitized.
# We test directly: if canonicalize("operator/") returns "operator_", the bug is NOT CONFIRMED.
passed = canonicalize("operator/") != "operator_"

if passed:
    print(f'CONFIRMED — canonicalize("operator/") returned {canonicalize("operator/")!r}, not "operator_"')
else:
    print(f'NOT CONFIRMED — canonicalize("operator/") returned {canonicalize("operator/")!r}')
    for d in details:
        print(f'  {d}')

# Cleanup probe workspace
try:
    os.rmdir(_probe_workspace)
except OSError:
    pass
```

### Probe Output

```
NOT CONFIRMED — canonicalize("operator/") returned 'operator_'
  OK: 'operator/' -> 'operator_'
  OK: 'ns::operator/' -> 'ns::operator_'
  OK: 'normal_function' -> 'normal_function'
  OK: '' -> ''
  OK: 'a/b/c' -> 'a_b_c'
```
