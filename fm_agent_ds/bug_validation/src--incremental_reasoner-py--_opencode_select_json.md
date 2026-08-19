# Bug Report: _opencode_select_json

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_opencode_select_json.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Atomically writes prompt_content to proj_dir/prompt_relpath via a temp-file rename, ensuring the previous content of that path (if any) is fully replaced. If a file exists at proj_dir/result_relpath before invocation, it is removed. Invokes the configured LLM CLI with the prompt file as the sole file argument, retrying up to OPENCODE_MAX_RETRIES times with a fixed 10-second delay between attempts. Each invocation is traced  producing a structured trace event with the stage identifier, attempt number, and any input/output file references. On the earliest attempt where the LLM invocation completes and the file at proj_dir/result_relpath exists afterward, reads and returns its content parsed as JSON. Returns None when: the LLM process exits with a non-zero code on every attempt, result_relpath does not exist after the last attempt, or result_relpath exists but contains content that is not valid JSON or is unreadable. The returned value is either a dict, a list, or None  depending on the JSON type produced by the LLM and whether generation succeeded. The original prompt_content, result_relpath, stage, and input_files arguments are not modified. No .spec.json or .info.json sidecar files are written by this function.

---

### Actual Behavior

After normal termination of _opencode_select_json (i.e., the function returns without raising an exception), the following holds:

- The file at `os.path.join(proj_dir, prompt_relpath)` exists and its content exactly equals `prompt_content`.
- Let `result_path = os.path.join(proj_dir, result_relpath)`.
- If the return value is not `None`, then `result_path` exists, its content is valid JSON, and the parsed JSON value equals the return value.
- If the return value is `None`, then either `result_path` does not exist (the agent never wrote the file after `OPENCODE_MAX_RETRIES` attempts) OR `result_path` exists but either its content could not be read due to an `OSError` or its content is not valid JSON.
- The function may have invoked `run_opencode_traced` multiple times (between 1 and `OPENCODE_MAX_RETRIES` inclusive), but the loop ensures that if a successful attempt produced `result_relpath`, the file remains on disk and is not removed by subsequent attempts.

Formal logic (in state after normal return):
```
Let result_path  join(proj_dir, result_relpath)
Let prompt_path  join(proj_dir, prompt_relpath)
Returned_value  (JSON_value  {None})
(
  (exists(prompt_path)  file_content(prompt_path) = prompt_content)
  
  (Returned_value  None 
    (exists(result_path)  is_valid_json(file_content(result_path))  json_parse(file_content(result_path)) = Returned_value)
  )
  
  (Returned_value = None 
    (exists(result_path) 
      (exists(result_path)  (read_error_occurred(result_path)  is_valid_json(file_content(result_path)))) )
  )
)
```
Here `read_error_occurred(result_path)` is true if an `OSError` prevented reading the file; `is_valid_json` and `json_parse` are standard JSON operations.

---

## Code Evidence

Line 61: return json.load(f)

---

## Trigger Condition

The code returns the raw parsed JSON value from the file, which can be a string, number, or boolean, violating the specification's requirement that the return value be only a dict, a list, or None.

---

## How to trigger the bug

When the LLM produces a JSON result file whose top-level value is a string, number, or boolean (all valid JSON), `_opencode_select_json` will return that scalar value instead of returning `None` or validating the type against the specification. The specification explicitly claims the return value is "either a dict, a list, or None".

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `<temporary directory>` |
| `work_dir` | `<temporary directory>` |
| `prompt_relpath` | `"prompt.txt"` |
| `prompt_content` | `"test prompt"` |
| `result_relpath` | `"result.json"` |
| `stage` | `"test_stage"` |
| `input_files` | `[]` |

### Expected (spec-correct) Output

`None` — the result file contains valid JSON but the top-level value is a string (not a dict or list). Per the spec, only dict, list, or None are valid return values.

### Actual (buggy) Output

`'hello world'` (a Python `str`) — the raw return value of `json.load()` is returned unvalidated.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, json, tempfile
from unittest.mock import patch

sys.path.insert(0, '.')

import src.incremental_reasoner as ir

with tempfile.TemporaryDirectory() as tmpdir:
    result_path = os.path.join(tmpdir, "result.json")
    
    def mock_run_opencode_traced(*a, **kw):
        with open(result_path, "w") as f:
            json.dump("hello world", f)
    
    with (
        patch.object(ir, "build_llm_cli_command", return_value=["echo", "mock"]),
        patch.object(ir, "run_opencode_traced", side_effect=mock_run_opencode_traced),
        patch.object(ir, "OPENCODE_MAX_RETRIES", 1),
    ):
        result = ir._opencode_select_json(
            proj_dir=tmpdir, work_dir=tmpdir,
            prompt_relpath="p.txt", prompt_content="x",
            result_relpath="result.json", stage="test",
            input_files=[],
        )
        print(result, type(result))
# actual (buggy) output: 'hello world' (str)
# expected (correct) output: None (scalar JSON is not dict or list)
```

---

## Probe Script

```python
"""Probe: _opencode_select_json returns raw json.load() including non-dict/non-list types."""

import sys
import os
import json
import tempfile
from unittest.mock import patch

# Resolve repo root from script location (script is at fm_agent/bug_validation/probe_*.py)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))
sys.path.insert(0, _repo_root)


def attempt(test_value, json_serialized, label):
    """Run _opencode_select_json with a mocked result file containing test_value."""
    with tempfile.TemporaryDirectory() as tmpdir:
        proj_dir = tmpdir
        work_dir = tmpdir
        prompt_relpath = "prompt.txt"
        prompt_content = f"test prompt for {label}"
        result_relpath = "result.json"
        stage = "test_stage"
        input_files = []

        result_path = os.path.join(proj_dir, result_relpath)

        def mock_run_opencode_traced(*args, **kwargs):
            with open(result_path, "w") as f:
                f.write(json_serialized)

        import src.incremental_reasoner as ir

        with (
            patch.object(ir, "build_llm_cli_command", return_value=["echo", "mock"]),
            patch.object(ir, "run_opencode_traced", side_effect=mock_run_opencode_traced),
            patch.object(ir, "OPENCODE_MAX_RETRIES", 1),
        ):
            return ir._opencode_select_json(
                proj_dir=proj_dir,
                work_dir=work_dir,
                prompt_relpath=prompt_relpath,
                prompt_content=prompt_content,
                result_relpath=result_relpath,
                stage=stage,
                input_files=input_files,
            )


if __name__ == "__main__":
    try:
        test_cases = [
            ("hello world", '"hello world"', "string"),
            (42, "42", "integer"),
            (True, "true", "boolean"),
        ]

        results = []
        for expected_val, json_str, label in test_cases:
            actual = attempt(expected_val, json_str, label)
            is_violation = actual is not None and not isinstance(actual, (dict, list))
            results.append((label, actual, is_violation))

        # The bug is confirmed if ANY test case shows a non-dict/non-list/non-None return
        confirmed = any(r[2] for r in results)

        if confirmed:
            details = "; ".join(
                f"{label}: {actual!r} (type={type(actual).__name__})"
                for label, actual, is_v in results if is_v
            )
            print(f"CONFIRMED — {details} | expected: must be dict, list, or None")
        else:
            details = "; ".join(
                f"{label}: {actual!r} (type={type(actual).__name__})"
                for label, actual, _ in results
            )
            print(f"NOT CONFIRMED — all results: {details}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

### Probe Output

```
CONFIRMED — string: 'hello world' (type=str); integer: 42 (type=int); boolean: True (type=bool) | expected: must be dict, list, or None
```
