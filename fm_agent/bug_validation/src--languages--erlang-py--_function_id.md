# Bug Report: _function_id

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/_function_id.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a function identifier string of the form
    "<module>__<unqualified_name>__<arity>" where:
      - <module> is the escaped module identifier derived from uri
      - <unqualified_name> is the escaped function name with any
        colon-separated module qualifier prefix stripped (unless the
        name starts with a single-quote character, in which case the
        full name including the prefix is preserved)
      - <arity> is the exact decimal string from label (after the last
        "/"), stripped of any leading sign
  - The double-underscore ("__") separator between <module>,
    <unqualified_name>, and <arity> is unambiguous for splitting the
    identifier back into its three components
  - Raises ValueError when label does not contain a "/" character, or
    when the substring after the last "/" is not parsable as an integer
    (including empty string, non-numeric characters, or values with a
    fractional part)

---

### Actual Behavior

Under the given precondition, the function returns a string `r` constructed as follows:

Let `name` and `arity` be the result of `label.rsplit("/", 1)`, i.e. the substring before the last `'/'` and the substring after it. Because the precondition guarantees that `arity` is a nonnegative integer represented as a decimal string, `int(arity)` succeeds and no exception is raised.

If `name` contains a colon (`':'`) and does not start with a single quote (`"'"`), let `name'` be the substring after the last colon in `name` (i.e. `name.rsplit(':', 1)[1]`); otherwise let `name' = name`.

Let `module = _module_from_uri(uri)`.

Then the returned value is

`r = _escape_component(module) + "__" + _escape_component(name') + "__" + arity`.

The two helper functions `_module_from_uri` and `_escape_component` guarantee that the components `module` and `name'` contain no doubleunderscore sequence, so the only `"__"` substrings in `r` are the two explicit separators. The returned string is nonempty and is the final result of the call; no exception is raised.

Formally:

 uri, label satisfying pre:
  let (name, arity) = label.rsplit('/', 1) in
  (int(arity) succeeds 
   name' = (if ':'  name  name[0]  '\'' then name.rsplit(':', 1)[1] else name) 
   module = _module_from_uri(uri) 
   r = _escape_component(module) + "__" + _escape_component(name') + "__" + arity) 
  the function terminates normally with result r.

---

## Code Evidence

Line 10: return f"{_escape_component(module)}__{_escape_component(name)}__{arity}"

---

## Trigger Condition

The specification requires <arity> to be the decimal string stripped of any leading sign. The code uses arity directly from label without stripping the '+' or '-' sign, so for label = 'myfunc/+2' the returned identifier contains __+2 instead of __2, violating the specification.

---

## How to trigger the bug

The function `_function_id` uses `arity` from the label directly without stripping any leading `+` or `-` sign. The `int(arity)` call succeeds for signed decimal strings (e.g., `int("+2")` returns `2`), but the raw string `"+2"` is passed to the f-string, producing an identifier with `__+2` instead of the spec-correct `__2`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `uri` | `file:///tmp/dummy/src/my_module.erl` |
| `label` | `myfunc/+2` |

### Expected (spec-correct) Output

`'my_module__myfunc__2'`

### Actual (buggy) Output

`'my_module__myfunc__+2'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import _function_id

result = _function_id("file:///tmp/dummy/src/my_module.erl", "myfunc/+2")
# actual (buggy) output: 'my_module__myfunc__+2'
# expected (correct) output: 'my_module__myfunc__2'
```

---

## Probe Script

```python
"""Probe: Does _function_id retain leading '+'/'-' signs in arity from label?

Spec claims arity must be "stripped of any leading sign".
Code evidence (Line 318): uses arity directly without stripping.
Trigger: label = 'myfunc/+2' → result contains __+2 not __2.
"""
import sys
from src.languages.erlang import _function_id

label = "myfunc/+2"
uri = "file:///tmp/dummy/src/my_module.erl"

try:
    result = _function_id(uri, label)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# The spec requires arity stripped of leading sign.
# The buggy code returns __<raw_arity>, so we look for '+' or '-' in the arity portion.
parts = result.rsplit("__", 2)
if len(parts) != 3:
    print(f"ERROR: unexpected result format: {result!r} — expected exactly two '__' separators")
    sys.exit(1)

module, name, arity_str = parts
expected_arity = arity_str.lstrip("+-")

if arity_str.startswith("+") or arity_str.startswith("-"):
    print(f"CONFIRMED — arity has leading sign: {arity_str!r} (expected: {expected_arity!r}) | full result: {result!r}")
else:
    print(f"NOT CONFIRMED — arity has no leading sign: {arity_str!r} | full result: {result!r}")
```

### Probe Output

```
CONFIRMED — arity has leading sign: '+2' (expected: '2') | full result: 'my_module__myfunc__+2'
```
