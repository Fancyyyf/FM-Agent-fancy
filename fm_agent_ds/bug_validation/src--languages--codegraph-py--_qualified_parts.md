# Bug Report: _qualified_parts

**Source file:** `src/languages/codegraph-py/_qualified_parts.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a non-empty list of identifier component strings whose final element is name. If qualified_name is empty or does not end with name, the result is [name]. Otherwise, the portion of qualified_name that precedes name is split on each occurrence of '::' or '.', empty components are discarded, and the surviving non-empty components form the prefix of the returned list in the left-to-right order they appear in qualified_name.

---

### Actual Behavior

The function returns a list of strings R. Let s = (qualified_name or '').strip(). If s == '' or not s.endswith(name): R = [name]. Otherwise, define scope = s[:-len(name)].rstrip(':.'). If scope == '': R = [name]. Else, let parts be the non-empty segments obtained by splitting scope on occurrences of '::' or '.' (using re.split); then R = parts + [name]. No exceptions are raised, and the list contains at least one element (name). Formally, R  [name]  ({[p for p in re.split(r'::|\\.', scope) if p] + [name]} where scope = (qualified_name or '').strip()[:-len(name)].rstrip(':.') and (qualified_name or '').strip().endswith(name)).

---

## Code Evidence

Line 14: q = (qualified_name or "").strip()
Line 15: if not q or not q.endswith(name):

---

## Trigger Condition

Specification requires checking whether qualified_name (without stripping) ends with name. The code strips whitespace first, so for '   Foo::bar   ' it does not end with 'bar', but after stripping it does, causing the code to incorrectly return ['Foo', 'bar'] instead of the required ['bar'].

---

## How to trigger the bug

The bug occurs when `qualified_name` has leading and/or trailing whitespace. The specification requires checking whether the raw `qualified_name` string ends with `name` (without any preprocessing). The code strips whitespace first via `q = (qualified_name or "").strip()`, which can change the result: a string like `"   Foo::bar   "` does not end with `"bar"` (it ends with spaces), but `"Foo::bar"` (the stripped version) does, causing the code to split the scope and include it in the result.

### Inputs

| Parameter | Value |
|-----------|-------|
| name | `"bar"` |
| qualified_name | `"   Foo::bar   "` |

### Expected (spec-correct) Output

`['bar']`

### Actual (buggy) Output

`['Foo', 'bar']`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.codegraph import _qualified_parts

result = _qualified_parts("bar", "   Foo::bar   ")
print(result)
# actual (buggy) output: ['Foo', 'bar']
# expected (correct) output: ['bar']
```

---

## Probe Script

```python
"""Probe for _qualified_parts bug: code strips whitespace from qualified_name
before checking endswith(name), while the spec requires checking the raw
qualified_name. For input '   Foo::bar   ' with name='bar', the spec says
the raw string does NOT end with 'bar', so the result should be ['bar'];
the buggy code strips first, finds it ends with 'bar', and returns ['Foo', 'bar'].
"""

import os
import sys
import tempfile

# Ensure the repo root is importable
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Create a fresh temporary directory for the probe workspace
# (as required by FM-Agent self-validation guard)
_probe_workspace = tempfile.mkdtemp(prefix="qualified_parts_probe_")

try:
    from src.languages.codegraph import _qualified_parts

    # Trigger condition: qualified_name with leading/trailing whitespace.
    # The raw string "   Foo::bar   " does NOT end with "bar" (it ends with "   "),
    # so per spec the result should be [name] = ["bar"].
    # The buggy code strips whitespace first, yielding "Foo::bar" which DOES
    # end with "bar", producing ["Foo", "bar"] instead.
    name = "bar"
    qualified_name = "   Foo::bar   "

    actual = _qualified_parts(name, qualified_name)

    # Spec-correct expectation: raw qualified_name does not end with name
    expected = ["bar"]

    passed = actual != expected

    if passed:
        print(
            f"CONFIRMED — actual: {actual!r} | expected: {expected!r} "
            f"(code strips whitespace before endswith check, "
            f"spec requires checking raw qualified_name)"
        )
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except ImportError as e:
    import traceback

    traceback.print_exc()
    print(f"ERROR: Cannot import _qualified_parts: {e}")
    sys.exit(1)
except Exception:
    import traceback

    traceback.print_exc()
    print("ERROR: probe script failed with an unhandled exception")
    sys.exit(1)
finally:
    # Cleanup probe workspace
    try:
        os.rmdir(_probe_workspace)
    except OSError:
        pass
```

### Probe Output

```
CONFIRMED — actual: ['Foo', 'bar'] | expected: ['bar'] (code strips whitespace before endswith check, spec requires checking raw qualified_name)
```
