# Bug Report: _function_id

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a canonical function identifier string formed from the module identifier derived from uri, the unqualified function name extracted from label, and the arity extracted from label, joined with double underscores in the form <module>__<name>__<arity>. Each component (<module>, <name>) has any characters that would conflict with the double-underscore separator deterministically replaced. The unqualified function name is the portion of label before the final forward slash; when that portion contains a colon and does not begin with a single quote character, only the substring after the last colon is used as the unqualified name. Raises ValueError when label is not a string, label does not contain a forward slash separator, or the portion of label after the final forward slash is not parseable as a non-negative integer.

---

### Actual Behavior

If the label string contains a slash '/' and the substring after the last slash is a valid nonnegative integer, the function returns a string formed by (1) computing a module identifier from uri via `_module_from_uri(uri)`, (2) extracting a function name from the part before the last slash: if that part contains a colon ':' and does not start with a single quote, the function name is taken as the substring after the last colon; otherwise it is the entire part before the slash, (3) applying `_escape_component` to the module identifier and to the function name, and (4) concatenating them with double underscores and the integer arity: `f"{escaped_module}__{escaped_name}__{arity}"`. If the label does not contain a slash or the substring after the slash cannot be converted to a nonnegative integer, a `ValueError` is raised with the message `"ELP function label has no valid arity: {label!r}"`, chained from the original exception. The functions `_module_from_uri` and `_escape_component` are assumed to always produce a deterministic result under the given preconditions; any exceptions they raise propagate directly. Formally, for all `uri`, `label` satisfying the precondition: ( name, arity_s : label = name + '/' + arity_s  arity_s  )  result = concat(_escape_component(_module_from_uri(uri)), "__", _escape_component(name_without_module), "__", arity_s) where name_without_module = if (':'  name  name[0]  ''') then rsplit(name, ':', 1)[1] else name; otherwise the function raises ValueError with the stated message.

---

## Code Evidence

Line 4: int(arity)

---

## Trigger Condition

The code does not validate that the arity substring represents a non-negative integer. int('-1') succeeds, so label='foo/-1' returns a string containing '__-1__' instead of raising ValueError as required. Additionally, the code does not handle the case where label is not a string (e.g., label=42) and raises AttributeError instead of ValueError.

---

## How to trigger the bug

The bug manifests in two independent failure modes, both confirmed through the probe:

### Inputs

| Parameter | Value (Bug 1) | Value (Bug 2) |
|-----------|--------------|--------------|
| uri | `"file:///src/module.erl"` | `"file:///src/module.erl"` |
| label | `"foo/-1"` | `42` |

### Expected (spec-correct) Output

Bug 1: `_function_id("file:///src/module.erl", "foo/-1")` should raise `ValueError` because `-1` is not a non-negative integer.
Bug 2: `_function_id("file:///src/module.erl", 42)` should raise `ValueError` because `label` is not a string.

### Actual (buggy) Output

Bug 1: `_function_id("file:///src/module.erl", "foo/-1")` returns `'module__foo__-1'` — the negative arity passes through `int()` unchecked.
Bug 2: `_function_id("file:///src/module.erl", 42)` raises `AttributeError: 'int' object has no attribute 'rsplit'` — the `except (ValueError, TypeError)` clause does not catch `AttributeError`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, ".")
from src.languages.erlang import _function_id

# Bug 1: Negative arity should raise ValueError
try:
    result = _function_id("file:///src/module.erl", "foo/-1")
    print(f"BUG: Negative arity not rejected, returned: {result!r}")
except ValueError:
    print("OK: ValueError correctly raised")

# Bug 2: Non-string label should raise ValueError
try:
    result = _function_id("file:///src/module.erl", 42)
    print(f"BUG: Non-string label not rejected, returned: {result!r}")
except ValueError:
    print("OK: ValueError correctly raised")
except AttributeError as e:
    print(f"BUG: Got AttributeError instead of ValueError: {e}")
```

---

## Probe Script

```python
"""Probe script for bug ID: src--languages--erlang-py--_function_id

Tests that _function_id properly validates:
1. Arity must be a non-negative integer (label="foo/-1" should raise ValueError)
2. Label must be a string (label=42 should raise ValueError, not AttributeError)
"""
import os
import sys

# Ensure the repository root is on the Python path
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# FM-Agent self-validation: import the smallest relevant unit directly.
# _function_id is a pure function with no FM-Agent workflow dependencies.
from src.languages.erlang import _function_id

results = []

# --- Bug 1: Negative arity ---
# Spec: raises ValueError when arity is not a non-negative integer
# Code: int('-1') succeeds, so returns a string instead of raising
try:
    result = _function_id("file:///src/module.erl", "foo/-1")
    # If we reach here, no exception was raised - bug confirmed
    results.append(("negative_arity", "CONFIRMED",
        f"CONFIRMED — Negative arity not rejected. "
        f"label='foo/-1' returned {result!r} instead of raising ValueError"))
except ValueError:
    # ValueError raised as spec requires - bug NOT confirmed
    results.append(("negative_arity", "NOT CONFIRMED",
        "NOT CONFIRMED — ValueError correctly raised for negative arity"))
except Exception as e:
    results.append(("negative_arity", "ERROR",
        f"ERROR — Unexpected exception type for negative arity: {type(e).__name__}: {e}"))

# --- Bug 2: Non-string label ---
# Spec: raises ValueError when label is not a string
# Code: int.rsplit() raises AttributeError, not caught by except (ValueError, TypeError)
try:
    result = _function_id("file:///src/module.erl", 42)
    # If we reach here, no exception - unexpected
    results.append(("non_string_label", "NOT CONFIRMED",
        f"NOT CONFIRMED — Non-string label unexpectedly accepted. "
        f"label=42 returned {result!r}"))
except ValueError:
    # ValueError raised as spec requires - bug NOT confirmed
    results.append(("non_string_label", "NOT CONFIRMED",
        "NOT CONFIRMED — ValueError correctly raised for non-string label"))
except AttributeError:
    # AttributeError raised instead of ValueError - bug CONFIRMED
    results.append(("non_string_label", "CONFIRMED",
        "CONFIRMED — Non-string label raises AttributeError instead of ValueError "
        "(spec requires ValueError)"))
except Exception as e:
    results.append(("non_string_label", "ERROR",
        f"ERROR — Unexpected exception type for non-string label: {type(e).__name__}: {e}"))

# Print results
all_confirmed = all(status == "CONFIRMED" for _, status, _ in results)
for name, status, msg in results:
    print(f"[{name}] {msg}")

if all_confirmed:
    print("CONFIRMED — All bug aspects reproduced")
else:
    confirmed_count = sum(1 for _, s, _ in results if s == "CONFIRMED")
    total = len(results)
    print(f"NOT CONFIRMED — Only {confirmed_count}/{total} bug aspects reproduced")
```

### Probe Output

```
[negative_arity] CONFIRMED — Negative arity not rejected. label='foo/-1' returned 'module__foo__-1' instead of raising ValueError
[non_string_label] CONFIRMED — Non-string label raises AttributeError instead of ValueError (spec requires ValueError)
CONFIRMED — All bug aspects reproduced
```
