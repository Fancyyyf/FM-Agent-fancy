# Bug Report: _resolve_callee_fqns

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a (possibly empty) set of callee FQN strings.
  - Every returned FQN belongs to callees_map[caller_fqn].
  - A callee FQN is included if and only if its final "::"-separated component (the stem)
    matches any string in callee_names, case-insensitively, OR any alias in
    edge_aliases_map for that (callee FQN, caller_fqn) pair matches any string in
    callee_names, case-insensitively.
  - A callee FQN whose stem or alias matches more than one name in callee_names is
    included exactly once (duplicate callee FQNs are not returned).

---

### Actual Behavior

The function `_resolve_callee_fqns` returns a `set` of callee FQNs from `callees_map[caller_fqn]` that match any of the given callee names (case-insensitively), considering both the stem (final `::`-separated component) of each callee FQN and any aliases provided by `edge_aliases_map`. The desired names are cleaned by stripping whitespace; empty or blank entries are discarded. The function does not mutate its inputs. Formally, let \\( W = \\{ \\text{strip}(n) \\mid n \\in \\text{callee\\_names},\\ n \\neq \\text{empty},\\ \\text{strip}(n) \\neq \\text{empty} \\} \\). Then the returned set \\( \\text{resolved} \\) satisfies: \\( \\text{resolved} = \\{ c \\mid c \\in \\text{callees\\_map}[\\text{caller\\_fqn}] \\land \\big( \\exists w \\in W: \\big( (\\text{stem} = c.\\text{split}(\\text{'::'})[-1]) \\land (\\text{stem} = w \\lor \\text{stem.lower}() = w.\\text{lower}()) \\big) \\lor \\big( \\text{edge\\_aliases\\_map} \\neq \\text{None} \\land \\exists a \\in \\text{edge\\_aliases\\_map}.\\text{get}(c, \\{\\}).\\text{get}(\\text{caller\\_fqn}, ()): a = w \\lor a.\\text{lower}() = w.\\text{lower}() \\big) \\big) \\} \\).

---

## Code Evidence

Line 10: wanted = {n.strip() for n in callee_names if n and n.strip()}

---

## Trigger Condition

The specification requires matching against the original strings in callee_names, case-insensitively, without stripping whitespace or discarding empty strings. The code strips whitespace from names, changing the matching criteria. For the given input, the stem is '  foo  ' and callee_names contains '  foo  '. The spec expects a match, but the code strips the name to 'foo', causing stem.lower() = '  foo  ' not to be in wanted_lower = {'foo'}, so the callee FQN is not returned.

---

## How to trigger the bug

The bug manifests when callee_names contains strings with surrounding whitespace that matches the stem (final `::`-separated component) of a callee FQN. The specification requires a case-insensitive comparison against the original strings. However, the code calls `.strip()` on each name before matching, so if the original stem also contains whitespace, the stripped version no longer matches.

### Inputs

| Parameter | Value |
|-----------|-------|
| `caller_fqn` | `"module::function"` |
| `callee_names` | `["  foo  "]` |
| `callees_map` | `{"module::function": ["path::to::  foo  "]}` |
| `edge_aliases_map` | `None` |

### Expected (spec-correct) Output

`{'path::to::  foo  '}`

### Actual (buggy) Output

`set()` (empty)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.incremental_reasoner import _resolve_callee_fqns

caller_fqn = "module::function"
callee_names = ["  foo  "]
callees_map = {"module::function": ["path::to::  foo  "]}

result = _resolve_callee_fqns(caller_fqn, callee_names, callees_map)
# actual (buggy) output: set()
# expected (correct) output: {'path::to::  foo  '}
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on sys.path so 'src' is importable as a package.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.incremental_reasoner import _resolve_callee_fqns
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Trigger condition: callee_names contains strings with surrounding whitespace,
# and the callee FQN's stem also contains whitespace. The spec requires a
# case-insensitive match against the original strings in callee_names (without
# stripping). The code strips whitespace, so the match fails.

caller_fqn = "module::function"
callee_names = ["  foo  "]
callees_map = {
    "module::function": ["path::to::  foo  "]
}

try:
    actual = _resolve_callee_fqns(caller_fqn, callee_names, callees_map)
    # Per the spec, "  foo  " should case-insensitively match "  foo  " -> the FQN should be included.
    expected = {"path::to::  foo  "}
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED -- actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED -- actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED -- actual: set() | expected: {'path::to::  foo  '}
```
