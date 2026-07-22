# Bug Report: _generate_block_post_condition

**Source file:** `src/prompts.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a string describing the strongest post-condition that must hold after executing block from the given pre-condition, covering all execution paths through the block including normal flow-through, early returns, and exceptional exits
  - Returns None when the post-condition could not be determined from the given inputs
  - The returned post-condition is expressed in natural language suitable for subsequent logical implication checks against specification post-conditions

---

### Actual Behavior

After normal execution (no exception), the function returns the value produced by calling `_llm_json_call` with the following arguments: client = `_llm_provider_client`, model = `REASONER_POST_CONDITION_MODEL`, messages = a list containing two dictionaries (a system message with content combining the expert role description and language-specific semantics, and a user message with the programming language, pre-condition, code block, and optional knowledge context), parse_fn = `_parse_post_condition_json`, default = `'{"post_condition": "non-empty string"}'`, trace_dir = the input `trace_dir`, and trace_meta = a dictionary with `'purpose'`, `'summary'`, and any input `trace_meta` merged. The return value is either a non-empty string (the extracted post-condition) or `None` if the LLM response could not be parsed. If `_llm_json_call` raises an exception, that exception propagates upward and the function terminates abnormally. No input arguments are mutated, and the only possible side effect is the trace persistence in `trace_dir` if provided.

Formally:

let info_str = if (knowledge is truthy) then "\nAdditional context:\n" + knowledge else "" in
let messages = [
  {role: "system", content: "You are an expert in formal verification of " + language + " programs. Given a " + language + " code block and its pre-condition, generate the post-condition that describes the program state after the code block finishes execution. Cover all execution paths including early returns, exceptions, and normal flow-through. Apply " + language + "-specific semantics (ownership, lifetimes, error handling, etc.) as appropriate. Be precise and unambiguous. Express the post-condition in natural language and formal logic."},
  {role: "user", content: "Programming language: " + language + "\n\nPre-condition:\n" + pre_condition + "\n\nCode block:\n```" + language_lower + "\n" + block + "\n```\n" + info_str + "\nGenerate th... (line truncated to 2000 chars)

---

## Code Evidence

Line 28: return _llm_json_call(...)

---

## Trigger Condition

The specification requires that the function returns None when the post-condition cannot be determined, implying all failure modes should be handled gracefully. The code does not catch exceptions from _llm_json_call, so any runtime error (e.g., network failure) results in an unhandled exception, violating the specification.

---

## How to trigger the bug

The function `_generate_block_post_condition` delegates to `_llm_json_call` via a bare `return _llm_json_call(...)` statement without any try/except wrapper. When `_llm_json_call` encounters an unrecoverable runtime error (e.g., network failure, rate limit exhaustion, invalid API response), it re-raises the exception. Since `_generate_block_post_condition` does not catch this exception, it propagates to the caller instead of returning `None` as the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| block | `"x = 1"` |
| pre_condition | `"x is undefined"` |
| knowledge | `None` |
| language | `"python"` |
| trace_dir | `None` (default) |
| trace_meta | `None` (default) |

### Expected (spec-correct) Output

`None` — the function should return `None` when the post-condition cannot be determined, which includes all failure modes (network errors, API failures, etc.)

### Actual (buggy) Output

A `RuntimeError` exception propagates from `_llm_json_call` through `_generate_block_post_condition` without being caught:
```
RuntimeError: Simulated LLM API failure — network error
```

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot')
import config
import src.prompts

# Monkey-patch _llm_json_call to simulate an LLM failure
original = src.prompts._llm_json_call
def mock_llm_json_call(*args, **kwargs):
    raise RuntimeError("Simulated LLM API failure")
src.prompts._llm_json_call = mock_llm_json_call

try:
    result = src.prompts._generate_block_post_condition("x = 1", "x is undefined", None, "python")
    # actual (buggy) output: RuntimeError propagates
except RuntimeError as e:
    # expected (correct) output: None
    pass
finally:
    src.prompts._llm_json_call = original
```

---

## Probe Script

```python
"""Probe for bug: _generate_block_post_condition does not catch exceptions from _llm_json_call.

Spec says: "Returns None when the post-condition could not be determined from the given inputs"
which implies all failure modes (including runtime errors) should be handled gracefully.
The code does `return _llm_json_call(...)` without try/except, so exceptions propagate.
"""
import sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot')

import config  # noqa: E402, F401
import src.prompts  # noqa: E402

# Save the original function
_original_llm_json_call = src.prompts._llm_json_call


def _mock_llm_json_call(*args, **kwargs):
    """Simulate an unrecoverable LLM runtime error (e.g. network failure)."""
    raise RuntimeError("Simulated LLM API failure — network error")


try:
    # Monkey-patch _llm_json_call so _generate_block_post_condition calls our mock
    src.prompts._llm_json_call = _mock_llm_json_call

    result = src.prompts._generate_block_post_condition(
        block="x = 1",
        pre_condition="x is undefined",
        knowledge=None,
        language="python",
    )

    # If we reach here, the function returned a value instead of propagating the exception.
    # But our mock raises, so this path means the exception was caught somehow.
    print(f"NOT CONFIRMED — function returned {result!r} instead of raising | "
          f"spec requires None for undetermined post-conditions")

except Exception as exc:
    # The exception from _mock_llm_json_call propagated through _generate_block_post_condition
    # without being caught. Per spec, it should have returned None.
    print(f"CONFIRMED — exception propagated instead of returning None | "
          f"exception type: {type(exc).__name__} | message: {exc}")

finally:
    # Always restore the original function
    src.prompts._llm_json_call = _original_llm_json_call
```

### Probe Output

```
CONFIRMED — exception propagated instead of returning None | exception type: RuntimeError | message: Simulated LLM API failure — network error
```
