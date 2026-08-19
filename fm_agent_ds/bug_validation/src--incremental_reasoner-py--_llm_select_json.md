# Bug Report: _llm_select_json

**Source file:** `src/incremental_reasoner.py` (function `_llm_select_json`)
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Sends prompt_content to the configured LLM. Returns the parsed and validated result when the LLM produces output that can be parsed as JSON, conforms to schema_description, and passes validator. Returns None when the LLM produces no output, output that cannot be parsed as JSON, output that does not conform to schema_description, or output that fails validator. The exchange is traced under work_dir with stage and trace_meta as identifying labels. On return with None, an error-level log entry is produced noting the stage.

---

### Actual Behavior

After execution of _llm_select_json, the function either terminates normally with a return value v, or raises an exception that propagates to the caller. 

Normal termination post-condition: 
(1) (v is None)  (v is not None  validator(v)[0] = True  v is a JSON-parsed object that conforms to schema_description). 
(2) The directory os.path.join(work_dir, 'trace') contains trace files from the LLM interaction(s), recorded with metadata {'stage': stage, 'summary': 'LLM ' + stage, **trace_meta}. 
(3) If v is None, a logging.error message containing stage is emitted. 

Exceptional termination (exception raised by _llm_json_call): the exception propagates; there is no return value, and no guarantees are made about the completeness or existence of the trace data.

---

## Code Evidence

Line 11: result = _llm_json_call(
        _llm_provider_client,
        LLM_MODEL,
        messages,
        validator,
        schema_description,
        trace_dir=os.path.join(work_dir, "trace"),
        trace_meta=meta,
    )

---

## Trigger Condition

The specification states that the function returns None whenever the LLM does not produce a valid, conforming JSON result; there is no provision for raising exceptions. The code propagates any exception raised by _llm_json_call (e.g., a network or client error) directly to the caller, violating the expected contract.

---

## How to trigger the bug

The bug is triggered whenever `_llm_json_call` raises an exception (e.g., due to a network error, authentication failure, or LLM client error). Instead of catching the exception and returning `None` as the specification requires, `_llm_select_json` lets the exception propagate directly to its caller.

### Inputs

| Parameter | Value |
|---|---|
| `work_dir` | `/tmp/probe__llm_select_json_XXXXXX` (temp dir) |
| `prompt_content` | `"test prompt"` |
| `stage` | `"test_stage"` |
| `validator` | `lambda x: (True, x)` |
| `schema_description` | `"test schema"` |
| `trace_meta` | `None` (default) |

### Expected (spec-correct) Output

`None` (the function should catch the exception and return `None`)

### Actual (buggy) Output

`RuntimeError` propagates to the caller — the function does not catch the exception from `_llm_json_call`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import patch
from src.incremental_reasoner import _llm_select_json

with patch("src.incremental_reasoner._llm_json_call") as mock_call:
    mock_call.side_effect = RuntimeError("Simulated LLM client error")
    _llm_select_json(
        work_dir="/tmp",
        prompt_content="test",
        stage="test_stage",
        validator=lambda x: (True, x),
        schema_description="test schema",
    )
# RuntimeError propagates — actual (buggy) output: exception raised
# expected (correct) output: None
```

---

## Probe Script

```python
"""Probe for bug: _llm_select_json propagates exceptions instead of returning None."""

import sys
import os
import tempfile
from unittest.mock import patch

# The probe is run from the repo root, so cwd is the project root directory.
# Python adds the script's own dir to sys.path, not the root. Add root explicitly.
sys.path.insert(0, os.getcwd())

# All fixtures and temp work stay in a fresh temp dir, not in fm_agent/
_workspace = tempfile.mkdtemp(prefix="probe__llm_select_json_")

passed = False
actual = None
expected = None

try:
    # Load _llm_select_json via the package entry point
    from src.incremental_reasoner import _llm_select_json

    # Patch _llm_json_call in the module where _llm_select_json looks it up.
    # In incremental_reasoner.py line 54: from .llm_client import _llm_json_call
    # So the name is bound in the incremental_reasoner module namespace.
    with patch("src.incremental_reasoner._llm_json_call") as mock_call:
        mock_call.side_effect = RuntimeError("Simulated LLM client error")

        # Per the specification, _llm_select_json must return None when the LLM
        # cannot produce valid output. A network/client exception falls under
        # "LLM produces no valid output", so the function should catch it and
        # return None — not let it propagate.
        result = _llm_select_json(
            work_dir=_workspace,
            prompt_content="test prompt",
            stage="test_stage",
            validator=lambda x: (True, x),
            schema_description="test schema",
        )

    # If we reach here without an exception, check the result.
    # The spec says a non-exceptional return should be None or valid JSON.
    # Since the mock raised, we should not be here — but we are.
    actual = result
    expected = None
    passed = False

except RuntimeError as e:
    # Bug confirmed: the exception from _llm_json_call propagated unchanged to
    # the caller. The specification requires returning None instead.
    actual = f"RuntimeError propagated: {e}"
    expected = None
    passed = True

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — exception propagated to caller (expected: None returned)")
else:
    print(f"NOT CONFIRMED — function returned {actual!r} (expected: {expected!r})")

# Cleanup temp workspace
try:
    os.rmdir(_workspace)
except OSError:
    pass
```

### Probe Output

```
CONFIRMED — exception propagated to caller (expected: None returned)
```
