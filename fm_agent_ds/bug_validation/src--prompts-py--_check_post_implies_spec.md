# Bug Report: _check_post_implies_spec

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/src/prompts.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a 4-tuple. When the actual post-condition of block satisfies the specification post-condition for all valid inputs, returns (True, None, None, None). When a concrete input exists where the actual post-condition violates the specification, returns (False, offending_statements, post_condition, reason) where offending_statements and reason are both non-empty strings. Raises ValueError if every LLM attempt produces an unparseable response. Raises the original exception (re-raised without retry) when an LLM API call itself fails, after recording a failure trace event. Produces structured trace event records when trace_dir is truthy; produces no side effects when trace_dir is falsy.

---

### Actual Behavior

After the code block finishes execution, the program state is described by one of the following four mutually exclusive outcomes.

Natural language:
1. The function returns a tuple (False, stmts, post_condition, reason) where stmts and reason are strings (if the parsed JSON had null or missing values, they have been replaced with the literal '(unable to extract)'). An event with status 'mismatch' has been recorded to the trace directory if trace_dir is truthy.
2. The function returns (True, None, None, None). An event with status 'success' has been recorded to the trace directory if trace_dir is truthy.
3. A ValueError is raised with the exact message 'Could not parse a valid structured JSON verdict from spec-check response.'. Before the raise, an event with status 'format_error' has been recorded (if trace_dir truthy), and the local variable messages has been extended by two new entries: an assistant message containing the raw LLM response and a user message re-prompting to output valid JSON.
4. An exception (any subclass of Exception) raised by the call to _retry_create is re-raised. Before the re-raise, an event with status 'error' and details of the exception has been recorded (if trace_dir truthy); the local messages list is unchanged.

In outcomes 1 and 2, no exception is raised; in outcomes 3 and 4, the function does not return a value. No other side effects on global state occur beyond the possible trace file writes.

---

## Code Evidence

Line 66: has_violation, stmts, reason, parsed_result = _parse_spec_check_json(response)
Line 92: if has_violation is not None:
Line 93:     if has_violation:
Line 94:         stmts = stmts or "(unable to extract)"
Line 95:         reason = reason or "(unable to extract)"
Line 96:         return False, stmts, post_condition, reason

---

## Trigger Condition

The code unconditionally trusts the LLM's verdict. When the LLM returns MISMATCH despite the actual post-condition satisfying the specification, the function incorrectly reports a violation, violating the specification's requirement to return (True, None, None, None) when no violation exists.

---

## How to trigger the bug

The function `_check_post_implies_spec` delegates the determination of whether a post-condition violates the specification entirely to an LLM via `_retry_create`. Once the LLM response is parsed by `_parse_spec_check_json`, the code at lines 92-96 unconditionally returns the LLM's verdict without any validation or sanity check. If the LLM hallucinates a violation (returns "MISMATCH" with fabricated evidence), the function returns `(False, ...)` even when the actual post-condition clearly satisfies the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `block` | `"def add(x, y):\\n    return x + y"` |
| `post_condition` | `"The function returns the sum of two integers. It always succeeds and does not raise any exceptions."` |
| `spec_post_condition` | `"The function returns the sum of two integers. It always succeeds and does not raise any exceptions."` |
| `knowledge` | `""` |
| `language` | `"python"` |
| `trace_dir` | `None` |

### Expected (spec-correct) Output

`(True, None, None, None)` — since `post_condition` is identical to `spec_post_condition`, the code's behavior trivially satisfies the specification for all inputs.

### Actual (buggy) Output

`(False, "Line 3: return x // y", "The function returns the sum of two integers...", "Hallucinated: code may divide by zero...")` — the function returns a false violation report because it blindly trusts the LLM's "MISMATCH" verdict.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json
import unittest.mock as mock
from src.prompts import _check_post_implies_spec
import src.prompts as prompts_module

fake_llm_response = json.dumps({
    "verdict": "MISMATCH",
    "counterexample": "x=42, y=0",
    "offending_statements": "Line 3: return x // y",
    "reason": "Hallucinated: code may divide by zero when y is 0.",
})

with mock.patch.object(prompts_module, "_retry_create",
                       return_value=(fake_llm_response, {})):
    result = _check_post_implies_spec(
        block="def add(x, y):\n    return x + y",
        post_condition="The function returns the sum of two integers.",
        spec_post_condition="The function returns the sum of two integers.",
        knowledge="",
        language="python",
        trace_dir=None,
    )
    print(result)
# actual (buggy) output: (False, 'Line 3: return x // y', ..., ...)
# expected (correct) output: (True, None, None, None)
```

---

## Probe Script

```python
"""Probe for bug: _check_post_implies_spec unconditionally trusts the LLM verdict.

Bug ID: src--prompts-py--_check_post_implies_spec

Expected (spec): When the actual post-condition satisfies the specification
post-condition, returns (True, None, None, None).

Actual (bug): The function delegates the verdict entirely to an LLM and
unconditionally returns whatever the LLM says. When the LLM returns "MISMATCH"
despite identical post_condition and spec_post_condition (where the former
clearly satisfies the latter), the function incorrectly reports a violation
as (False, stmts, post_condition, reason).
"""

import json
import os
import sys
import unittest.mock as mock
from pathlib import Path

# Ensure the repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# --- Save and sanitize environment to isolate the test ---
_saved_env = {k: os.environ.get(k) for k in (
    "FM_AGENT_CONFIG", "LLM_API_KEY", "LLM_API_BASE_URL", "FM_AGENT_MODEL_BACKEND",
    "LLM_MODEL", "LLM_EFFORT", "OPENCODE_MODEL_PROVIDER", "LLM_API_STYLE",
    "MAX_SPC_ITER", "GRANULARITY", "MAX_WORKERS", "OPENCODE_MAX_RETRIES",
    "BUG_VALIDATION_MAX_RETRIES", "OPENCODE_TIMEOUT_SECONDS",
    "FM_AGENT_DOMAIN_KNOWLEDGE",
)}
for k in _saved_env:
    if k in os.environ:
        del os.environ[k]

try:
    # --- Step 1: Import the target function ---
    from src.prompts import _check_post_implies_spec

    # --- Step 2: Craft a fake LLM response that says MISMATCH ---
    fake_llm_response = json.dumps({
        "verdict": "MISMATCH",
        "counterexample": "x=42, y=0",
        "offending_statements": "Line 3: return x // y",
        "reason": "Hallucinated: code may divide by zero when y is 0.",
    })

    fake_usage = {"prompt_tokens": 100, "completion_tokens": 50}

    # --- Step 3: Mock _retry_create to return the fake response ---
    import src.prompts as prompts_module

    with mock.patch.object(prompts_module, "_retry_create",
                           return_value=(fake_llm_response, fake_usage)):
        has_violation, stmts, post_cond, reason = _check_post_implies_spec(
            block="def add(x, y):\n    return x + y",
            post_condition=(
                "The function returns the sum of two integers. "
                "It always succeeds and does not raise any exceptions."
            ),
            spec_post_condition=(
                "The function returns the sum of two integers. "
                "It always succeeds and does not raise any exceptions."
            ),
            knowledge="",
            language="python",
            trace_dir=None,
        )

    if has_violation is False:
        # Bug confirmed: LLM said MISMATCH but conditions are identical
        print(
            f"CONFIRMED — Function returned ({has_violation}, {stmts!r}, "
            f"{post_cond!r}, {reason!r}) instead of "
            f"(True, None, None, None). "
            f"The code unconditionally trusts an LLM MISMATCH verdict even when "
            f"post_condition and spec_post_condition are identical. "
            f"stmts={stmts!r} reason={reason!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — Function correctly returned "
            f"({has_violation}, {stmts!r}, {post_cond!r}, {reason!r})"
        )

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {type(e).__name__}: {e}")

finally:
    # Restore environment
    for k, v in _saved_env.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]
```

### Probe Output

```
CONFIRMED — Function returned (False, 'Line 3: return x // y', 'The function returns the sum of two integers. It always succeeds and does not raise any exceptions.', 'Hallucinated: code may divide by zero when y is 0.') instead of (True, None, None, None). The code unconditionally trusts an LLM MISMATCH verdict even when post_condition and spec_post_condition are identical. stmts='Line 3: return x // y' reason='Hallucinated: code may divide by zero when y is 0.'
```
