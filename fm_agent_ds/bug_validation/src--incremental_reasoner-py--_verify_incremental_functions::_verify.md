# Bug Report: _verify

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_verify_incremental_functions::_verify.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a pair (rel, verdict) where the first element equals the input argument unchanged, and verdict is the verification outcome for the function at extracted_dir/rel. When the function's .spec.json and .info.json sidecars both exist and are well-formed, verdict is a dict whose 'verdict' key is either 'MATCH' (the implementation satisfies the spec) or 'MISMATCH' (the implementation violates the spec); a MISMATCH verdict additionally contains non-empty 'counterexample' and 'offending_statements' strings. When required sidecar files are absent or malformed, verdict is None.

---

### Actual Behavior

The function _verify either completes normally, returning a 2-tuple (rel, verdict), or propagates any exception raised by _verify_single_file. If _verify_single_file does not raise an exception, the tuple's first element is the input relative path rel (unchanged), and the second element, verdict, is the second component of the tuple returned by _verify_single_file (as specified in its own post-condition: None or a dict containing at least the key 'verdict' with value 'MATCH' or 'MISMATCH'; when 'MISMATCH' the dict also contains non-empty strings under 'counterexample' and 'offending_statements'). The call to _verify_single_file may create verification artefacts inside output_dir, but leaves the original extracted function file (fpath) and its associated .spec.json and .info.json sidecars unchanged. If _verify_single_file raises an exception (e.g., due to missing or malformed sidecars), the exception propagates unmodified and no return occurs. Formally, let E be the exception type and R be the return value: ( ( _verify_single_file(fpath, extracted_dir, output_dir, language, work_dir)  (_, v)    R = (rel, v)    output_dir  output_dir'  files unmodified )    ( _verify_single_file raises E    _verify raises E ) ).

---

## Code Evidence

Line 4:         _, verdict = _verify_single_file(fpath, extracted_dir, output_dir, language, work_dir=work_dir)

---

## Trigger Condition

Specification B requires returning (rel, None) when required sidecar files are absent or malformed. The code unconditionally calls _verify_single_file, which when sidecars are missing raises an exception (e.g., FileNotFoundError) that propagates unmodified, violating the specification.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `func_path` | `<tmpdir>/extracted_functions/test_func-py/test_func.py` (exists, no sidecars) |
| `input_dir` | `<tmpdir>/extracted_functions` |
| `output_dir` | `<tmpdir>/output` |
| `language` | `"Python"` |

### Expected (spec-correct) Output

`(func_path, None)` — verdict is `None` because required sidecar files are absent.

### Actual (buggy) Output

`(func_path, 'SKIPPED')` — no exception was raised. `_verify_single_file` handled the missing sidecars by catching the missing-file condition internally and returning `"SKIPPED"` as the verdict string.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile
from src.verification import _verify_single_file

with tempfile.TemporaryDirectory() as tmpdir:
    func_dir = os.path.join(tmpdir, "extracted_functions", "test_func-py")
    os.makedirs(func_dir)
    func_path = os.path.join(func_dir, "test_func.py")
    with open(func_path, "w") as f:
        f.write("def test_func():\n    return 42\n")
    output_dir = os.path.join(tmpdir, "output")
    os.makedirs(output_dir)
    result_path, verdict = _verify_single_file(
        func_path, os.path.join(tmpdir, "extracted_functions"),
        output_dir, "Python"
    )
    # actual (buggy) output: verdict = 'SKIPPED' (not None, no exception)
    # expected (correct) output: verdict = None
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe script: test whether _verify_single_file raises exceptions on missing sidecars."""
import sys
import os
import tempfile

# Add repo root to path so 'import src' works from the repo root
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.verification import _verify_single_file

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an extracted function file WITHOUT .spec.json / .info.json sidecars
        func_dir = os.path.join(tmpdir, "extracted_functions", "test_func-py")
        os.makedirs(func_dir, exist_ok=True)

        func_path = os.path.join(func_dir, "test_func.py")
        with open(func_path, "w") as f:
            f.write("def test_func():\n    return 42\n")

        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(output_dir, exist_ok=True)

        input_dir = os.path.join(tmpdir, "extracted_functions")

        raised = False
        exc_message = ""
        try:
            result_path, verdict = _verify_single_file(
                func_path, input_dir, output_dir, "Python"
            )
        except Exception as e:
            raised = True
            exc_message = str(e)

        if raised:
            print(f"CONFIRMED — exception raised: {exc_message}")
        else:
            expected = None  # per spec: verdict should be None when sidecars absent
            if verdict is None:
                print("NOT CONFIRMED — verdict is None (matches spec); no exception raised")
            else:
                print(
                    f"NOT CONFIRMED — _verify_single_file returned {verdict!r} "
                    f"without raising; spec expects None for missing sidecars"
                )
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — _verify_single_file returned 'SKIPPED' without raising; spec expects None for missing sidecars
```
