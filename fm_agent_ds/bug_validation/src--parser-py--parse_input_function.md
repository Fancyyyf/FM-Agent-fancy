# Bug Report: parse_input_function

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/parser-py/parse_input_function.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a 3-tuple (func, nl_spec, knowledge) where: func is the source file content with all comments removed (preserving string literals) and each line prefixed by "Line N: " for the 1-indexed line number N, retaining the original line structure; nl_spec is a reasoner-formatted specification string derived from the adjacent .spec.json sidecar, or an empty string if the sidecar is absent or cannot be loaded; knowledge is a FunctionSpecMap containing callee entries derived from the adjacent .info.json sidecar, or an empty FunctionSpecMap if the sidecar is absent or cannot be loaded.

---

### Actual Behavior

If file_path is readable and no exceptions occur during execution, the function returns a 3-tuple (func, nl_spec, knowledge). Here func is the content of file_path with all comments removed (preserving string literals), split into lines, each line prepended with 'Line <N>: ' (1-indexed), and joined back with newlines. nl_spec is the result of format_spec_for_reasoner(spec) if _load_sidecar_json(file_path, '.spec.json') returned a dict with keys 'signature', 'pre_condition', and 'post_condition'; otherwise, if _load_sidecar_json returns None, nl_spec is an empty string. If _load_sidecar_json returns a dict but any required key is missing, format_spec_for_reasoner raises a KeyError, which propagates and no return occurs. knowledge is a FunctionSpecMap built by format_info_for_reasoner(info) if _load_sidecar_json(file_path, '.info.json') returned a dict with a 'callees' key whose value is a list of callee entries each containing 'name', 'signature', 'pre_condition', 'post_condition'; if _load_sidecar_json returns None, knowledge is an empty FunctionSpecMap with no entries and an empty signatures dict. If the returned dict from _load_sidecar_json does not conform to the expected structure (e.g., missing 'callees' or malformed callee entries), format_info_for_reasoner may raise a KeyError or other exception, which propagates. No other side effects occur. If file_path cannot be opened for reading (violating the pre-condition of being readable), an OSError (FileNotFoundError, PermissionError) is raised and no value is returned.

---

## Code Evidence

Line 14:     nl_spec = format_spec_for_reasoner(spec) if spec else ""

---

## Trigger Condition

The code treats an empty dict returned by _load_sidecar_json as falsy and substitutes an empty string, while the specification requires derivation (via format_spec_for_reasoner) whenever the sidecar file is present and loadable, even if it parses to an empty object. The sidecar is not absent and not unloadable, so returning an empty string breaches the post-condition.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `file_path` | `/tmp/<tmpdir>/test_func.py` — a readable source file with an adjacent `.spec.json` containing `{}` (empty JSON object) |

### Expected (spec-correct) Output

`nl_spec = '\n\nPre-condition:\n\n\nPost-condition:\n'` (result of calling `format_spec_for_reasoner({})`)

### Actual (buggy) Output

`nl_spec = ''` (empty string, because the empty dict `{}` is falsy in the truthiness check)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os
from src.parser import parse_input_function, format_spec_for_reasoner

with tempfile.TemporaryDirectory() as tmpdir:
    source_path = os.path.join(tmpdir, "test_func.py")
    spec_path = source_path + ".spec.json"

    with open(source_path, "w") as f:
        f.write("def foo():\n    return 42\n")
    with open(spec_path, "w") as f:
        f.write("{}")

    func, nl_spec, knowledge = parse_input_function(source_path)
    expected = format_spec_for_reasoner({})
    # actual (buggy) output: nl_spec = ''
    # expected (correct) output: nl_spec = '\n\nPre-condition:\n\n\nPost-condition:\n'
    assert nl_spec != expected, "Bug NOT reproduced"
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile

# Ensure the repo root is on sys.path for package import
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.parser import parse_input_function, format_spec_for_reasoner
except Exception as e:
    print(f"ERROR: Could not import src.parser: {e}")
    sys.exit(1)

try:
    # Create a temporary directory for test fixtures
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = os.path.join(tmpdir, "test_func.py")
        spec_path = source_path + ".spec.json"

        # Write a minimal source file
        with open(source_path, "w") as f:
            f.write("def foo():\n    return 42\n")

        # Write an empty .spec.json — file exists and parses, but yields {}
        with open(spec_path, "w") as f:
            f.write("{}")

        # Call the function under test via public entry point
        func, nl_spec, knowledge = parse_input_function(source_path)

        # Expected behavior per spec: sidecar present and loadable, so
        # format_spec_for_reasoner should be called with {}
        expected = format_spec_for_reasoner({})

        # Bug check: if nl_spec is empty string but expected is not, bug confirmed
        passed = (nl_spec != expected)

        if passed:
            print(f"CONFIRMED — actual (buggy) nl_spec: {nl_spec!r} | expected (spec-correct): {expected!r}")
        else:
            print(f"NOT CONFIRMED — actual nl_spec matches expected: {nl_spec!r}")
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual (buggy) nl_spec: '' | expected (spec-correct): '\n\nPre-condition:\n\n\nPost-condition:\n'
```
