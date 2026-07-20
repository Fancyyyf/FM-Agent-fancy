# Bug Report: _name_parts

**Source file:** `fm_agent/extracted_functions/src/scope-py/_name_parts.py` (live source: `src/scope.py:208-233`)
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a set of lowercased string components derived from name
  - The full lowercased name is always included as one component
  - The name is split on underscore characters ("_"); each resulting token
    whose length is at least 2 is included as a component
  - Every consecutive pair of underscore-separated tokens is joined by "_"
    and included as a component (in addition to the individual tokens)
  - The name is split at each uppercase-to-lowercase transition boundary
    and at each leading underscore, lowercased, and each resulting token
    whose length is at least 2 is included as a component
  - A token that appears in both the underscore split and the
    case-transition split is included only once (set semantics)
  - All components are in lowercase
  - The returned set is never empty; it contains at minimum the full
    lowercased name

---

### Actual Behavior

The function returns a set of strings containing: (1) the lowercased input name; (2) all tokens from splitting the lowercased name by underscores that have length greater than 1; (3) all consecutive pairs of those tokens joined by an underscore; (4) all tokens of length greater than 1 obtained by inserting underscores before each uppercase letter in the original name, lowercasing, stripping leading/trailing underscores, and splitting by underscores. Formally: let L = name.lower(); let T = [t for t in L.split('_') if len(t) > 1]; let P = {f'{T[i]}_{T[i+1]}' for i in range(len(T) - 1)}; let C = {p for p in re.sub(r'([A-Z])', r'_\\1', name).lower().strip('_').split('_') if len(p) > 1}; then the result = {L}  set(T)  P  C.

---

## Code Evidence

Line 13:     toks = [t for t in lower.split('_') if len(t) > 1]
Line 16:     for i in range(len(toks) - 1):
Line 17:         parts.add(f"{toks[i]}_{toks[i+1]}")

---

## Trigger Condition

The code filters underscore-split tokens to those with length > 1 (Line 13), then generates consecutive pairs using only those filtered tokens (Lines 16-17). For input "a_b_c", the split tokens ['a','b','c'] have length 1, so no tokens qualify, resulting in no pairs. However, the specification requires that every consecutive pair of underscore-separated tokens be included, which for "a_b_c" are "a_b" and "b_c". Thus the code's output {"a_b_c"} does not satisfy the required set {"a_b_c", "a_b", "b_c"}.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| name | `"a_b_c"` |

### Expected (spec-correct) Output

`{"a_b_c", "a_b", "b_c"}`

### Actual (buggy) Output

`{"a_b_c"}`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.scope import _name_parts

# actual (buggy) output: {'a_b_c'}
# expected (correct) output: {'a_b_c', 'a_b', 'b_c'}
print(_name_parts("a_b_c"))
```

---

## Probe Script

```python
import sys
import os

# Ensure repo root is on sys.path so 'src' package is importable.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.scope import _name_parts
except Exception as e:
    print(f'ERROR: Failed to import _name_parts from src.scope: {e}')
    sys.exit(1)

# Trigger condition from the bug report: input "a_b_c"
# Spec claim: every consecutive pair of underscore-separated tokens must be included.
# For "a_b_c", the underscore-split tokens are ["a", "b", "c"].
# Expected (spec-correct): {"a_b_c", "a_b", "b_c"}
# Actual (buggy): {"a_b_c"} — all tokens have length 1, filtered out, no pairs generated.

test_inputs = [
    ("a_b_c", {"a_b_c", "a_b", "b_c"}),
    ("x_y_z_w", {"x_y_z_w", "x_y", "y_z", "z_w"}),
    ("n1_n2", {"n1_n2"}),  # len(n1)=2, len(n2)=2, single pair "n1_n2"
]

all_passed = True

for name, expected in test_inputs:
    try:
        actual = _name_parts(name)
    except Exception as e:
        print(f'ERROR: _name_parts("{name}") raised: {e}')
        sys.exit(1)

    missing = expected - actual
    extra = actual - expected

    if missing:
        all_passed = False
        print(f'BUG REPRODUCED for "{name}"')
        print(f'  missing from actual: {missing}')
        print(f'  extra in actual: {extra}')
    else:
        print(f'OK for "{name}"')

if all_passed:
    print('NOT CONFIRMED — all test cases produced the expected output')
else:
    print('CONFIRMED — bug reproduced: consecutive underscore-separated pairs are missing when individual tokens have length <= 1')
```

### Probe Output

```
BUG REPRODUCED for "a_b_c"
  missing from actual: {'b_c', 'a_b'}
  extra in actual: set()
BUG REPRODUCED for "x_y_z_w"
  missing from actual: {'y_z', 'x_y', 'z_w'}
  extra in actual: set()
OK for "n1_n2"
CONFIRMED — bug reproduced: consecutive underscore-separated pairs are missing when individual tokens have length <= 1
```
