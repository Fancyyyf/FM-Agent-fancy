# Bug Report: _llm_rerank

**Source file:** `src/scope.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

On success: returns a list of function name strings ordered by LLM-assessed relevance to issue, with length at most top_k and no duplicate names. Every returned name appears in funcs_info. On failure (the LLM response after 3 attempts is not a valid JSON array of non-empty function name strings): returns None. The initial LLM call includes the formatted function list, filepath, issue, and top_k; when the response is not a valid JSON array of non-empty strings, up to two additional retries are made with corrective instructions appended to the conversation, each spaced with increasing backoff delay. The function does not raise exceptions; all errors within attempts are caught and result in either a retry or None.

---

### Actual Behavior

The function returns either a list of non-empty strings (function names) parsed from a valid JSON array in the LLM response, or None if all three attempts fail. Input arguments remain unchanged. All exceptions are caught internally and do not propagate. Side effects (logging, sleep, local messages list modifications) do not affect the caller. Formal post-condition: (return value = None)  (return value is a list of strings   s  return value, isinstance(s, str)  s.strip() != ''). The list may be empty. If returned, the list originates from the first successful LLM call within three attempts where the response contained a parseable JSON array of strings, each non-empty. Otherwise, after three failed attempts, None is returned.

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

The code only ensures the response is a JSON array of non-empty strings. It fails to check that the returned list has length  top_k, contains no duplicates, or includes only names present in funcs_info, any of which would violate the specification.

---

## How to trigger the bug

The function accepts a mock LLM client that returns a JSON array with 4 function names (`["foo", "bar", "baz", "qux"]`) when `top_k=2` and `funcs_info` only contains `["foo", "bar", "baz"]`. The function returns all 4 names without validating the length constraint, the presence of "qux" (not in `funcs_info`), or the `top_k` limit.

### Inputs

| Parameter | Value |
|-----------|-------|
| `funcs_info` | `[{"name": "foo", ...}, {"name": "bar", ...}, {"name": "baz", ...}]` |
| `source_lines` | `["def foo(): pass", "def bar(): pass", "def baz(): pass"]` |
| `filepath` | `"/tmp/test.py"` |
| `issue` | `"test issue"` |
| `top_k` | `2` |
| `llm_client` | Mock returning `["foo", "bar", "baz", "qux"]` |
| `model` | `"test-model"` |

### Expected (spec-correct) Output

`None` or a list with at most 2 names, all drawn from `{"foo", "bar", "baz"}`, with no duplicates.

### Actual (buggy) Output

`['foo', 'bar', 'baz', 'qux']` — 4 names exceeding `top_k=2`, including `"qux"` which is not in `funcs_info`.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json
from unittest.mock import MagicMock
import src.scope as scope

funcs_info = [
    {"name": "foo", "start": 1, "end": 1, "calls": [], "idents": [],
     "body_words": [], "exc_types": [], "docstring": "Function foo"},
    {"name": "bar", "start": 2, "end": 2, "calls": [], "idents": [],
     "body_words": [], "exc_types": [], "docstring": "Function bar"},
    {"name": "baz", "start": 3, "end": 3, "calls": [], "idents": [],
     "body_words": [], "exc_types": [], "docstring": "Function baz"},
]
source_lines = ["def foo(): pass", "def bar(): pass", "def baz(): pass"]

mock = MagicMock()
mock.chat.completions.create.return_value = MagicMock(
    choices=[MagicMock(message=MagicMock(content=json.dumps(["foo", "bar", "baz", "qux"])))]
)

result = scope._llm_rerank(funcs_info, source_lines, "/t.py", "test", 2, mock, "m")
print(result)
# actual (buggy) output: ['foo', 'bar', 'baz', 'qux']
# expected (correct) output: at most 2 names from {foo, bar, baz}, no duplicates
```

---

## Probe Script

```python
"""Probe for bug: _llm_rerank does not validate len <= top_k, uniqueness, or funcs_info membership."""
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock

# Ensure repo root is on sys.path so `from src.scope import ...` resolves.
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))


def main() -> str:
    import src.scope as scope
    _llm_rerank = scope._llm_rerank

    # Create minimal funcs_info with 3 functions: foo, bar, baz
    # start/end must be within source_lines range (1-indexed)
    funcs_info = [
        {
            "name": "foo",
            "start": 1,
            "end": 1,
            "calls": [],
            "idents": [],
            "body_words": [],
            "exc_types": [],
            "docstring": "Function foo",
        },
        {
            "name": "bar",
            "start": 2,
            "end": 2,
            "calls": [],
            "idents": [],
            "body_words": [],
            "exc_types": [],
            "docstring": "Function bar",
        },
        {
            "name": "baz",
            "start": 3,
            "end": 3,
            "calls": [],
            "idents": [],
            "body_words": [],
            "exc_types": [],
            "docstring": "Function baz",
        },
    ]
    source_lines = [
        "def foo(): pass",
        "def bar(): pass",
        "def baz(): pass",
    ]
    filepath = "/tmp/test.py"
    issue = "test issue"
    top_k = 2  # spec requires at most 2 names returned

    # Bug 1: LLM returns more names than top_k (4 names > top_k=2)
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps(["foo", "bar", "baz", "qux"])))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    result = _llm_rerank(
        funcs_info=funcs_info,
        source_lines=source_lines,
        filepath=filepath,
        issue=issue,
        top_k=top_k,
        llm_client=mock_client,
        model="test-model",
    )

    # The spec requires len(result) <= top_k when not None.
    # Since top_k=2 but result has 4 names, this is a confirmed bug.
    if result is None:
        return "NOT CONFIRMED — function returned None (unexpected)"
    if len(result) > top_k:
        return (
            f"CONFIRMED — spec requires len <= {top_k}, "
            f"but got {len(result)} names: {result}"
        )
    return f"NOT CONFIRMED — result length {len(result)} <= top_k {top_k}: {result}"


if __name__ == "__main__":
    try:
        output = main()
        print(output)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        import traceback; traceback.print_exc()
        sys.exit(1)
```

### Probe Output

```
CONFIRMED — spec requires len <= 2, but got 4 names: ['foo', 'bar', 'baz', 'qux']
```
