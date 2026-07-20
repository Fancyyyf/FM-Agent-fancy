# Bug Report: _llm_rerank

**Source file:** `src/scope.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If the LLM produces a valid response, returns a list of function names
    (non‑empty strings), each drawn exclusively from the set of names in
    funcs_info, in descending order of relevance to the issue as judged by
    the LLM, with no duplicate names and length at most top_k.
  - If the LLM does not produce a valid response after the allowed number of
    attempts, returns None.
  - The function is idempotent with respect to funcs_info, source_lines,
    filepath, and issue: repeated calls with the same arguments may produce
    different rankings (LLM non‑determinism) but each valid ranking obeys
    the same contract.

---

### Actual Behavior

The function terminates normally (does not raise an exception under the given pre-conditions). Let R be the returned value. Then (R is None) XOR (R is a list of strings such that ∀ s ∈ R, s.strip() != ''). R is None if and only if all three retry attempts failed: each attempt's try block raised an exception (caught, logged with a warning, and, for the first two, followed by an extended messages list and a sleep). R is a non-empty list if and only if some attempt succeeded: the LLM returned a valid JSON array, every element was a string that after stripping was non-empty, and R is exactly [s.strip() for s in that parsed list]. No further validation against funcs_info names is performed. Formally, let S = {x ∈ str : x.strip() ≠ ''}; then post-condition ⊢ (R = None) ∨ (R ∈ list(S)).

---

## Code Evidence

Line 29: names = _parse_json_response(text)
Line 30: if not isinstance(names, list) or not all(
Line 31:     isinstance(name, str) and name.strip() for name in names
Line 32: ):
Line 33:     raise ValueError("LLM rerank response must be a JSON array of non-empty function names")
Line 34: return [name.strip() for name in names]

---

## Trigger Condition

The code only validates that the response is a JSON array of non-empty strings, but the specification requires that all returned names belong to funcs_info, have no duplicates, and the list length is at most top_k. A response like ['baz'] for funcs_info containing only 'foo' would be accepted by the code, violating the spec.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| funcs_info | `[{"name": "foo", "start": 1, "end": 3, ...}]` |
| source_lines | `["def foo():", "    pass", ""]` |
| filepath | `"test.py"` |
| issue | `"test issue for bug reproduction"` |
| top_k | `3` |
| Mock LLM response | `["baz"]` (a name NOT in funcs_info) |

### Expected (spec-correct) Output

The spec requires returned names to be drawn exclusively from `funcs_info`. Since `"baz"` is not in `funcs_info` (which only contains `"foo"`), the spec-compliant implementation should either reject the LLM response and retry (eventually returning `None`), or filter to only valid names (returning an empty list `[]` or `None`).

### Actual (buggy) Output

`["baz"]` — the function accepts the foreign name because its validation only checks that each element is a non-empty string, without verifying membership in `funcs_info`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, json
sys.path.insert(0, ".")  # repo root on path
from src.scope import _llm_rerank

# funcs_info with only "foo" — "baz" is not a valid function
funcs_info = [{"name": "foo", "start": 1, "end": 3, "docstring": ""}]
source_lines = ["def foo():", "    pass", ""]

class MockClient:
    class chat:
        class completions:
            @staticmethod
            def create(**kw):
                class R:
                    choices = [type("c", (), {"message": type("m", (), {"content": '["baz"]'})()})()]
                return R()

result = _llm_rerank(funcs_info, source_lines, "test.py", "test", 3, MockClient(), "m")
print(result)
# actual (buggy) output: ['baz']
# expected (correct) output: None  (baz is not in funcs_info)
```

---

## Probe Script

```python
"""Probe: _llm_rerank accepts LLM-returned names not in funcs_info.

Spec claim: returned names must be drawn exclusively from funcs_info.
Bug: only validates "JSON array of non-empty strings", not membership in funcs_info.
"""
import sys
import json
from pathlib import Path

# Ensure the repo root is on sys.path so `from src.xxx` imports work
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    # Import via the package module (not internal file path)
    from src.scope import _llm_rerank

    # --- Setup: funcs_info with only "foo" ---
    funcs_info = [
        {
            "name": "foo",
            "start": 1,
            "end": 3,
            "calls": set(),
            "idents": set(),
            "body_words": set(),
            "exc_types": set(),
            "docstring": "",
        }
    ]
    source_lines = ["def foo():", "    pass", ""]
    filepath = "test.py"
    issue = "test issue for bug reproduction"
    top_k = 3

    # --- Mock LLM client: returns ["baz"], a name NOT in funcs_info ---
    class MockMessage:
        content = json.dumps(["baz"])

    class MockChoice:
        message = MockMessage()

    class MockResponse:
        choices = [MockChoice()]

    class MockCompletions:
        @staticmethod
        def create(model, messages, max_tokens, temperature):
            return MockResponse()

    class MockChat:
        completions = MockCompletions()

    class MockLLMClient:
        chat = MockChat()

    mock_client = MockLLMClient()

    # --- Call _llm_rerank ---
    result = _llm_rerank(
        funcs_info=funcs_info,
        source_lines=source_lines,
        filepath=filepath,
        issue=issue,
        top_k=top_k,
        llm_client=mock_client,
        model="test-model",
    )

    # --- Verify against spec ---
    spec_names = {f["name"] for f in funcs_info}  # {"foo"}

    if result is None:
        # No valid result — this would be spec-compliant if LLM returned invalid names
        print(f"NOT CONFIRMED — _llm_rerank returned None (spec-compliant, no foreign names leaked)")
    else:
        foreign = [n for n in result if n not in spec_names]
        if foreign:
            # Bug reproduced: foreign name accepted
            print(f"CONFIRMED — _llm_rerank returned foreign names: {foreign}")
            print(f"  spec names in funcs_info: {list(spec_names)}")
            print(f"  actual returned names: {result}")
        else:
            # All names are valid — spec-compliant
            print(f"NOT CONFIRMED — all returned names in funcs_info: {result}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — _llm_rerank returned foreign names: ['baz']
  spec names in funcs_info: ['foo']
  actual returned names: ['baz']
```
