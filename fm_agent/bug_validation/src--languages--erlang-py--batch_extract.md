# Bug Report: batch_extract

**Source file:** `src/languages/erlang-py/batch_extract.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a mapping from absolute .erl file paths to lists of (function_identifier, source_text) tuples
- Each function_identifier is a string uniquely naming a top-level Erlang function within its source module
- Each source_text is the complete function body as found in the corresponding file
- If Erlang-specific analysis is unavailable for the project at proj_dir, returns an empty dict

---

### Actual Behavior

The return value is a dictionary. If the analysis of the project directory is successful, the dictionary maps absolute file paths (strings) of Erlang files to lists of (function_id, body) tuples; otherwise, it returns an empty dictionary. Formally, let `R` be the return value. Then `isinstance(R, dict)` is true. For all keys `k` in `R`, `k` is a string representing an absolute file path. For each `k`, `R[k]` is a list of tuples, where each tuple is of type `(str, str)`. The condition `R == {}` holds if and only if the analysis for `proj_dir` could not be performed (i.e., no Erlang sources or tool unavailable); otherwise, `R` is non-empty and contains all extracted function definitions from the project.

---

## Code Evidence

The root cause is in `_function_id()` (src/languages/erlang.py, line 309) and `_escape_component()` (line 294). The `_function_id` builds identifiers from module name, function name, and arity:

```python
def _function_id(uri: str, label: str) -> str:
    name, arity = label.rsplit("/", 1)
    int(arity)
    if ":" in name and not name.startswith("'"):
        name = name.rsplit(":", 1)[1]
    module = _module_from_uri(uri)
    return f"{_escape_component(module)}__{_escape_component(name)}__{arity}"
```

The `_escape_component` function escapes non-alphanumeric/non-underscore characters to `_{hex}` format:

```python
def _escape_component(value: str) -> str:
    result = []
    for char in value:
        if char.isascii() and (char.isalnum() or char == "_"):
            result.append(char)
        else:
            result.append(f"_{ord(char):02x}")
    return "".join(result)
```

This creates collisions: `my@func` and `my_40func` both escape to `my_40func`. With the same module and arity, they produce identical function_ids. The `seen` set in `_analyze_project_uncached` (line 515) then silently drops the second function.

---
Source: Line 3 of extracted function (maps to `src/languages/erlang.py`, line 614):
```python
return _analysis_or_empty(proj_dir).functions
```

---

## Trigger Condition

The specification requires that each function_identifier is a string uniquely naming a top-level Erlang function within its source module. The code does not enforce uniqueness of function_id; the `_escape_component` function maps different characters to the same escape sequence, producing collisions. For example, `my@func/1` and `my_40func/1` (both valid unquoted Erlang atoms) map to the same identifier `mymodule__my_40func__1`. When this occurs within a source file, the `seen` duplication check in `_analyze_project_uncached` silently drops one of the two functions, violating the spec that all extracted functions must be present.

**Note:** The original gap analysis hypothesized that duplicates arise from "functions with the same name but different arity." This specific claim is **not confirmed** — arity is correctly included in the function_id. However, the actual bug is confirmed via a different path: `_escape_component` collisions between functions with different names that share escapable characters.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A directory containing an Erlang module with functions whose names collide after `_escape_component` (e.g., `my@func/1` and `my_40func/1`) |

### Expected (spec-correct) Output

Both functions should appear in the result with distinct, unique function identifiers:
- `mymodule__a_unique_id_for_my_at_func__1`
- `mymodule__a_unique_id_for_my_40func__1`

### Actual (buggy) Output

Only one function is returned; the second is silently dropped:
- `mymodule__my_40func__1` (only one of the two functions, the second collides and is discarded)

### How to Reproduce

1. Create an Erlang module with two functions that collide under `_escape_component`:
```erlang
-module(mymodule).
-export([my@func/1, my_40func/1]).
my@func(X) -> X.
my_40func(X) -> X + 1.
```
2. Navigate to the repo root.
3. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import batch_extract
result = batch_extract("path/to/project")
# With ELP available, only one function will be present due to ID collision
```

---

## Probe Script

```python
"""Probe: Does batch_extract / _function_id produce non-unique function identifiers?

The spec requires each function_identifier to be unique within its source module.
The bug claim: functions with the same name but different arity produce duplicate IDs.
"""

import sys
import os
import tempfile

# Load the package via its entry point — repo root is two levels up from this script
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)
from src.languages.erlang import batch_extract, _function_id, _escape_component, _module_from_uri

def test_batch_extract_smoke():
    """Attempt batch_extract on a temp dir with Erlang files. Without ELP, returns {}."""
    with tempfile.TemporaryDirectory() as tmpdir:
        erl_path = os.path.join(tmpdir, "test.erl")
        with open(erl_path, "w") as f:
            f.write("-module(test).\n-export([foo/1, foo/2]).\n\nfoo(1) -> one;\nfoo(2) -> two.\n")
        result = batch_extract(tmpdir)
        return isinstance(result, dict)

def test_same_name_different_arity():
    """Test: do functions with the same name but different arity get different IDs?

    The bug claims they produce duplicates. Arity IS in the ID, so they should differ.
    """
    uri = "file:///home/user/proj/mymodule.erl"
    fid1 = _function_id(uri, "foo/1")
    fid2 = _function_id(uri, "foo/2")
    fid3 = _function_id(uri, "bar/3")

    ids = [fid1, fid2, fid3]
    unique = len(set(ids))
    duplicates_exist = unique != len(ids)

    return {
        "ids": ids,
        "unique": unique == len(ids),
        "duplicates_exist": duplicates_exist,
    }

def test_escape_component_collisions():
    """Test: can _escape_component produce collisions between different function names?

    _escape_component escapes non-alphanumeric/non-underscore chars to _{hex}.
    Example: '-' (0x2D) → '_2d'. But '2d' is alphanumeric, so 'foo-bar' → 'foo_2dbar'.
    A function named 'foo_2dbar' would also become 'foo_2dbar'. This creates a collision.
    """
    esc1 = _escape_component("foo-bar")
    esc2 = _escape_component("foo_2dbar")
    esc3 = _escape_component("hello_world")
    esc4 = _escape_component("hello-world")
    esc5 = _escape_component("my@func")
    esc6 = _escape_component("my_40func")

    collisions = []
    if esc1 == esc2:
        collisions.append(f"'foo-bar' and 'foo_2dbar' both → '{esc1}'")
    if esc4 == esc3:
        collisions.append(f"'hello-world' and 'hello_world' both → '{esc3}'")
    if esc5 == esc6:
        collisions.append(f"'my@func' and 'my_40func' both → '{esc5}'")

    uri = "file:///home/user/proj/mymodule.erl"

    # Test pair 1: quoted name with hyphen vs escaped literal
    fid_a = _function_id(uri, "'foo-bar'/1")
    fid_b = _function_id(uri, "foo_2dbar/1")
    collision_1 = fid_a == fid_b

    # Test pair 2: unquoted @ vs escaped literal (more practical collision)
    fid_c = _function_id(uri, "my@func/1")
    fid_d = _function_id(uri, "my_40func/1")
    collision_2 = fid_c == fid_d

    fid_collision = collision_1 or collision_2

    return {
        "escape_collisions": collisions,
        "function_id_collision": fid_collision,
        "collision_1": {"a": fid_a, "b": fid_b, "collision": collision_1},
        "collision_2": {"c": fid_c, "d": fid_d, "collision": collision_2},
    }

def test_seen_dedup_scenario():
    """Test: what if the 'seen' set drops a legitimate function due to _function_id collision?

    In _analyze_project_uncached, each file has a 'seen' set that prevents duplicate
    function_ids from being added. If two different Erlang functions produce the same
    function_id (via _escape_component collision), the second one would be silently
    dropped. This is the actual bug.
    """
    uri = "file:///home/user/proj/mymodule.erl"
    labels = [
        ("my@func/1", "my_at_func() -> ok."),
        ("my_40func/1", "my_40func(X) -> X + 1."),
    ]
    seen = set()
    results = []
    for label, body in labels:
        try:
            fid = _function_id(uri, label)
        except ValueError:
            continue
        if fid in seen:
            results.append(("DROPPED", fid, label, body))
        else:
            seen.add(fid)
            results.append(("KEPT", fid, label, body))

    kept_count = sum(1 for r in results if r[0] == "KEPT")
    dropped_count = sum(1 for r in results if r[0] == "DROPPED")

    return {
        "results": results,
        "kept": kept_count,
        "dropped": dropped_count,
        "bug_confirmed": dropped_count > 0,
    }


def main():
    verdicts = []

    try:
        smoke_ok = test_batch_extract_smoke()
        verdicts.append(("batch_extract_smoke", smoke_ok, None))
    except Exception as e:
        verdicts.append(("batch_extract_smoke", False, str(e)))

    try:
        result = test_same_name_different_arity()
        verdicts.append(("same_name_diff_arity", result["unique"], result))
    except Exception as e:
        verdicts.append(("same_name_diff_arity", False, str(e)))

    try:
        result = test_escape_component_collisions()
        verdicts.append(("escape_collision", not result["function_id_collision"], result))
    except Exception as e:
        verdicts.append(("escape_collision", False, str(e)))

    try:
        result = test_seen_dedup_scenario()
        verdicts.append(("seen_dedup", not result["bug_confirmed"], result))
    except Exception as e:
        verdicts.append(("seen_dedup", False, str(e)))

    bug_confirmed = any(
        category == "seen_dedup" and details.get("bug_confirmed", False)
        for category, _, details in verdicts
        if isinstance(details, dict)
    )

    if bug_confirmed:
        print("CONFIRMED — _function_id via _escape_component produces duplicate identifiers; seen set silently drops functions")
    else:
        print("NOT CONFIRMED — function identifiers include arity, same-name-different-arity produces unique IDs; no duplicates observed")

    for category, passed, details in verdicts:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {category}: {details}")

    return 0 if not bug_confirmed else 1

if __name__ == "__main__":
    sys.exit(main())
```

### Probe Output

```
CONFIRMED — _function_id via _escape_component produces duplicate identifiers; seen set silently drops functions
  [PASS] batch_extract_smoke: None
  [PASS] same_name_diff_arity: {'ids': ['mymodule__foo__1', 'mymodule__foo__2', 'mymodule__bar__3'], 'unique': True, 'duplicates_exist': False}
  [FAIL] escape_collision: {'escape_collisions': ["'foo-bar' and 'foo_2dbar' both → 'foo_2dbar'", "'my@func' and 'my_40func' both → 'my_40func'"], 'function_id_collision': True, 'collision_1': {'a': 'mymodule___27foo_2dbar_27__1', 'b': 'mymodule__foo_2dbar__1', 'collision': False}, 'collision_2': {'c': 'mymodule__my_40func__1', 'd': 'mymodule__my_40func__1', 'collision': True}}
  [FAIL] seen_dedup: {'results': [('KEPT', 'mymodule__my_40func__1', 'my@func/1', 'my_at_func() -> ok.'), ('DROPPED', 'mymodule__my_40func__1', 'my_40func/1', 'my_40func(X) -> X + 1.')], 'kept': 1, 'dropped': 1, 'bug_confirmed': True}
```
