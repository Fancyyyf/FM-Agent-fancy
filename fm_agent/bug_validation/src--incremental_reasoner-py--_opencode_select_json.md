# Bug Report: _opencode_select_json

**Source file:** `/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot/fm_agent/extracted_functions/src/incremental_reasoner-py/_opencode_select_json.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- The full prompt_content is present at proj_dir/prompt_relpath when the LLM agent is invoked
  - Any pre-existing file at proj_dir/result_relpath is removed before the first LLM invocation
  - An LLM agent is invoked to read the prompt and may write a JSON artifact to result_relpath
  - The invocation is retried up to a configurable maximum number of times when result_relpath is not produced
  - A fixed delay elapses between consecutive retry attempts
  - Each invocation attempt is traced as an observable event
  - Returns the parsed JSON value (dict or list) when result_relpath is produced and its content is valid JSON
  - Returns None when result_relpath is never produced within the retry limit, or when the file content is not valid JSON or cannot be read
  - A non-zero exit code from the LLM agent does not determine the return value  only the presence and parseability of result_relpath does

---

### Actual Behavior

After execution (no unhandled exceptions), the function returns either None or a Python object representing the JSON content of the file at `result_path`. The following holds:

1. **Prompt file**: `prompt_path = os.path.join(proj_dir, prompt_relpath)` exists and its content is exactly `prompt_content`. Any previous file at that path is overwritten atomically via a temporary file.
2. **Result file cleanup**: If `result_path = os.path.join(proj_dir, result_relpath)` existed before the call, it is removed before the first attempt.
3. **Retry loop**: For each attempt `i` from 1 to `OPENCODE_MAX_RETRIES` (inclusive), unless an earlier attempt already caused a break:
   - The LLM command `cmd` returned by `build_llm_cli_command(...)` is executed via `run_opencode_traced`. If the process exits with a non-zero code, `CalledProcessError` is caught and logged; the loop continues (unless it was the last attempt).
   - After the command (or after catching the error), the file system is inspected: if `result_path` now exists, the loop breaks immediately (`produced = True`) and no further attempts occur. Otherwise, if `i < OPENCODE_MAX_RETRIES`, the thread sleeps for 10 seconds before the next attempt.
4. **Return value**: Let `r` be the returned value.
   - If after the loop `result_path` does **not** exist, then `r = None`.
   - If `result_path` exists, the function attempts to open it and parse its content with `json.load`. If parsing succeeds (no `ValueError` or `OSError`), `r` is the parsed object; otherwise `r = None`.

---

## Code Evidence

Line 61: return json.load(f)

---

## Trigger Condition

The specification requires that the function returns a dict or list on success, but the code returns any JSON value that json.load produces (e.g., a number, string, bool, or null). There is no type check to ensure the parsed result is a dict or list, so a valid input where the LLM writes a nondict/list JSON value yields a return value that violates the specification.

---

## How to trigger the bug

Mock the LLM invocation (`run_opencode_traced`) to write a valid JSON string (not a dict or list) to the result file. The function calls `json.load(f)` at line 106 and returns the parsed value without checking whether it is a dict or list, violating the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | (temporary directory) |
| `work_dir` | (temporary directory) |
| `prompt_relpath` | `"test_prompt.md"` |
| `prompt_content` | `"test prompt content"` |
| `result_relpath` | `"test_result.json"` |
| `stage` | `"test_stage"` |
| `input_files` | `[]` |

### Expected (spec-correct) Output

`None` — The specification states the function returns `dict | list | None`. A string value is neither a dict nor a list, so `None` is the correct response (treat it as an invalid/unexpected JSON structure).

### Actual (buggy) Output

`'not_a_dict_or_list'` (type: `str`) — The function returns whatever `json.load(f)` produces without any type validation.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, os, tempfile
from unittest.mock import patch
import src.incremental_reasoner as ir

tmpdir = tempfile.mkdtemp()
proj_dir = tmpdir
work_dir = os.path.join(tmpdir, "work")
os.makedirs(work_dir)

# Mock the LLM agent to write a string (not dict/list) to the result file
def mock_run(proj_dir, work_dir, command, stage, input_files, output_files, summary, metadata):
    with open(os.path.join(proj_dir, output_files[0]), "w") as f:
        json.dump("not_a_dict_or_list", f)

with patch.object(ir, "run_opencode_traced", mock_run), \
     patch.object(ir, "build_llm_cli_command", return_value="echo mock"):
    actual = ir._opencode_select_json(
        proj_dir, work_dir, "prompt.md", "content",
        "result.json", "test", []
    )
    print(repr(actual))  # actual (buggy) output: 'not_a_dict_or_list' (str)
                         # expected (correct) output: None (not a dict/list)
```

---

## Probe Script

```python
"""Probe for _opencode_select_json: missing type check on json.load result at line 106.

The bug: `return json.load(f)` returns any JSON value (string, number, bool, null, list, dict),
but the spec requires returning only dict or list. There is no type check to reject
non-dict/list values.
"""
import sys
import os
import json
import tempfile
import shutil
from unittest.mock import patch

# Ensure the repo root is on sys.path so 'src' is importable as a package.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    import src.incremental_reasoner as ir
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)


def probe():
    tmpdir = tempfile.mkdtemp(prefix="probe_opencode_select_json_")

    try:
        proj_dir = tmpdir
        work_dir = os.path.join(tmpdir, "work")
        os.makedirs(work_dir, exist_ok=True)
        prompt_relpath = "test_prompt.md"
        result_relpath = "test_result.json"
        prompt_content = "test prompt content"
        stage = "test_stage"
        input_files = []

        # Simulate the LLM agent producing a valid JSON string (NOT a dict or list)
        # by mocking run_opencode_traced to write a string value to the result file.
        def mock_run_opencode_traced(proj_dir, work_dir, command, stage,
                                      input_files, output_files, summary, metadata):
            result_path = os.path.join(proj_dir, output_files[0])
            with open(result_path, "w") as f:
                json.dump("not_a_dict_or_list", f)

        # Mock build_llm_cli_command to avoid needing a real opencode setup
        def mock_build_llm_cli_command(model, prompt, cwd, files):
            return "echo mock"

        with patch.object(ir, "run_opencode_traced", mock_run_opencode_traced), \
             patch.object(ir, "build_llm_cli_command", mock_build_llm_cli_command):

            actual = ir._opencode_select_json(
                proj_dir, work_dir, prompt_relpath, prompt_content,
                result_relpath, stage, input_files,
            )

        # The spec requires: returns dict or list on success, None otherwise.
        # The code at line 106 has no type check — it returns whatever json.load produces.
        # If actual is a string (not dict/list), the bug is CONFIRMED.
        expected_types = (dict, list)

        if isinstance(actual, expected_types):
            print(f"NOT CONFIRMED — actual type {type(actual).__name__} IS a valid dict/list, but the missing type-check still exists at line 106")
        elif actual is None:
            print(f"NOT CONFIRMED — returned None, meaning result file was not produced or parsed")
        else:
            print(f"CONFIRMED — actual: {actual!r} (type: {type(actual).__name__}) | expected type: dict or list | missing type check at line 106")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    try:
        probe()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: 'not_a_dict_or_list' (type: str) | expected type: dict or list | missing type check at line 106
```
