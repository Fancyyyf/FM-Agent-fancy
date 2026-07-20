# Bug Report: batch_extract_all

**Source file:** `src/languages/registry-py/batch_extract_all.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a tuple (funcs, langs) where:
      funcs is a dict mapping normalized absolute file paths (str) to lists
        of (func_name: str, func_body: str) tuples.
      langs is a set of language key strings.
  - Every registered handler's batch_extract is invoked exactly once with
    proj_dir as its sole argument.
  - For each handler whose batch_extract returns a truthy dict result: every
    key-value pair in that dict is included in funcs (with later handlers
    overwriting earlier entries for duplicate keys), and the handler's language
    key is included in langs.
  - A handler whose batch_extract returns a falsy result contributes nothing to
    funcs or langs.
  - If no handler returns a truthy result: funcs is an empty dict and langs is
    an empty set.
  - If any handler's batch_extract raises an exception, that exception
    propagates uncaught to the caller; funcs and langs are not returned.

---

### Actual Behavior

If any handler.batch_extract(proj_dir) raises an exception, that exception propagates and the function terminates abnormally. Otherwise (all calls complete without raising), the function returns a tuple (funcs, langs) where:

- funcs: dict | None? Actually funcs is always a dict (initialized as {}). It contains exactly the union of all key-value pairs from the results of handler.batch_extract(proj_dir) for each (lang, handler) in REGISTRY.items() for which the returned value was truthy (i.e., a nonempty dict mapping absolute file paths to lists of (func_name, body) tuples). If multiple handlers produce truthy results that share a key (absolute file path), the value from the last handler in REGISTRYs iteration order takes precedence (because dict.update overwrites existing keys).

- langs: set of strings, containing exactly the language keys lang for which the corresponding handler.batch_extract(proj_dir) returned a truthy result.

Formally: Let R_lang = handler.batch_extract(proj_dir) for each iteration. After the loop, funcs = initial_{} MERGED { (k, v) | lang: R_lang is truthy, (k,v)  R_lang }, where later assignments override earlier ones for repeated k. And langs = { lang | R_lang is truthy }.

The REGISTRY is assumed to be nonempty, and proj_dir is an existing directory as described in the precondition.

---

## Code Evidence

Line 11: funcs.update(result)

---

## Trigger Condition

The specification post-condition states that funcs must map normalized absolute file paths, but the code directly merges handler results without normalizing paths. A handler that returns an absolute but non-normalized path (still valid per its own contract) causes the output to violate the normalization requirement.

---

## How to trigger the bug

The `batch_extract_all` function merges handler results via `funcs.update(result)` without applying `os.path.normpath` to the keys. If any language handler's `batch_extract` returns a dict whose keys are absolute but non-normalized paths (e.g., containing `..` components), those non-normalized paths appear verbatim in the output, violating the spec's normalization post-condition.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `"/tmp"` |
| Mock handler's `batch_extract` return | `{"/tmp/a/../b/file.py": [("func1", "def func1():\n    pass")]}` |

### Expected (spec-correct) Output

`funcs` should map `"/tmp/b/file.py"` (normalized) to `[("func1", "def func1():\n    pass")]`

### Actual (buggy) Output

`funcs` maps `"/tmp/a/../b/file.py"` (non-normalized) to `[("func1", "def func1():\n    pass")]`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, ".")

from src.languages.registry import batch_extract_all, REGISTRY, LanguageHandler

original = dict(REGISTRY)
REGISTRY.clear()

non_normalized = os.path.join("/tmp", "a", "..", "b", "file.py")

def mock_batch_extract(proj_dir):
    return {non_normalized: [("func1", "def func1():\n    pass")]}

REGISTRY["mock"] = LanguageHandler(
    batch_extract=mock_batch_extract,
    call_edges=lambda _p: {},
    function_spans=lambda _p, _f: None,
)

funcs, langs = batch_extract_all("/tmp")
print(list(funcs.keys())[0])
# actual (buggy) output: /tmp/a/../b/file.py
# expected (correct) output: /tmp/b/file.py

REGISTRY.clear()
REGISTRY.update(original)
```

---

## Probe Script

```python
import sys
import os

# Ensure repo root is on sys.path so we can import src
repo_root = os.getcwd()
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.languages.registry import batch_extract_all, REGISTRY, LanguageHandler

    # Save original registry for restoration
    original_registry = dict(REGISTRY)

    # Clear real handlers and install a single mock handler
    REGISTRY.clear()

    # Construct a non-normalized absolute path (contains ".." component)
    non_normalized = os.path.join("/tmp", "a", "..", "b", "file.py")
    normalized = os.path.normpath(non_normalized)
    # non_normalized = "/tmp/a/../b/file.py"
    # normalized      = "/tmp/b/file.py"

    def mock_batch_extract(proj_dir):
        return {non_normalized: [("func1", "def func1():\n    pass")]}

    mock_handler = LanguageHandler(
        batch_extract=mock_batch_extract,
        call_edges=lambda _proj_dir: {},
        function_spans=lambda _proj_dir, _filepath: None,
    )
    REGISTRY["mock"] = mock_handler

    # Exercise the public API
    funcs, langs = batch_extract_all("/tmp")

    keys = list(funcs.keys())

    # Restore original registry before asserting
    REGISTRY.clear()
    REGISTRY.update(original_registry)

    if len(keys) != 1:
        print(f"NOT CONFIRMED — unexpected number of keys: {len(keys)} (expected 1)")
    elif keys[0] == non_normalized and keys[0] != normalized:
        print(f"CONFIRMED — actual: {keys[0]!r} | expected (normalized): {normalized!r}")
    elif keys[0] == normalized:
        print(f"NOT CONFIRMED — key is already normalized: {keys[0]!r}")
    else:
        print(f"NOT CONFIRMED — unexpected key: {keys[0]!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: '/tmp/a/../b/file.py' | expected (normalized): '/tmp/b/file.py'
```
