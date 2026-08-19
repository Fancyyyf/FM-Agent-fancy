# Bug Report: _validate_single_bug

**Source file:** `src/verification.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When a result marker for the discrepancy corresponding to result_json_rel does not already exist at <work_dir>/bug_validation/<bug_id>.result.json, or when resume is False, a bug-validation agent is dispatched to evaluate whether the spec-code discrepancy recorded in result_json_rel constitutes a real, exploitable bug. A validated bug report is produced at <work_dir>/bug_validation/<bug_id>.md if and only if the discrepancy is confirmed to be an exploitable bug. The bug report contains: the behavioral assertion claimed by the specification that the code violates, the actual behavior observed from the code, concrete code evidence with line references, the condition under which the violation is triggered, step-by-step reproduction instructions, a probe script exercising the violation, and the raw output from executing the probe script. A result marker file is written to <work_dir>/bug_validation/<bug_id>.result.json upon completion of validation. When resume is True and the result marker already exists with valid, parseable JSON content, no re-validation occurs and no side effects are produced. The bug_id is uniquely derived from result_json_rel by stripping the standard verification-results path prefix and canonicalizing directory separators.

---

### Actual Behavior

After the code block, one of three scenarios holds: (1) An unhandled exception was raised (e.g., from os.makedirs, file writing, os.replace, or build_llm_cli_command). In this case the program may have aborted with only partial side effects; no further guarantees are made about variables after the exception point. (2) No exception occurred and the function returned early at line 73 because resume was truthy, result_path existed, and the file could be successfully read and parsed as JSON. Then the following are true: the directory os.path.join(work_dir, 'bug_validation') exists; the file at prompt_path exists and its entire content equals prompt_content; the temporary file tmp_path no longer exists; the following variables are defined with values as given in the code: prompt_content = '# Bug Validator\\n\\n**Target result file:** `{result_json_rel}`\\n**Bug ID:** `{bug_id}`\\n\\n---\\n\\n' + user_knowledge_section + base_content, prompt_filename = 'fm_agent/bug_validation/bug_validator_{bug_id}.md', prompt_path = os.path.join(proj_dir, prompt_filename), tmp_path = prompt_path + '.tmp', prompt = 'Follow the instructions in the attached file', command = build_llm_cli_command(OPENCODE_BUG_VALIDATION_MODEL, prompt, cwd=proj_dir, files=[prompt_path]), result_relpath = 'fm_agent/bug_validation/{bug_id}.result.json', result_path = os.path.join(proj_dir, result_relpath); the function returns normally. (3) No exception occurred and no early return (either resume is falsy, result_path does not exist, or JSON parsing raised an exception). Then the same directory and file side effects hold as in scenario (2), the same variable assignments hold as in scenario (2), and additionally: max_attempts = config.BUG_VALIDATION_MAX_RETRIES; the for loop for attempt in range(1, max_attempts + 1) has been entered and the first iteration began with attempt = 1 and run_failed = False; the try block at line 80 has been entered but no inner statements have executed yet.

**Note:** The verification analysis stops at line 80 of the extracted function and does not account for the `run_opencode_traced()` call on lines 84–106 (lines 434–451 in the original `src/verification.py`), which is the actual bug-validation agent dispatch. The verification is a false positive caused by incomplete control-flow analysis that stopped before reaching the dispatch logic.

---

## Code Evidence

Line 41: through Line 80: The code block only performs prompt setup and a skip check; it never dispatches the bug-validation agent, never writes the validated bug report to <work_dir>/bug_validation/<bug_id>.md, and never writes the result marker file <work_dir>/bug_validation/<bug_id>.result.json upon completion of validation as required by the specification.

**Rebuttal:** Lines 84–106 of the extracted function (lines 430–451 of the original `src/verification.py`) contain the `run_opencode_traced()` call, which IS the bug-validation agent dispatch. The `output_files` parameter explicitly declares both `bug_validation/<bug_id>.md` and `bug_validation/<bug_id>.result.json` as expected outputs. The verification was truncated before reaching this code.

---

## Trigger Condition

The specification requires that when resume is False or the result marker does not exist, a bug-validation agent is dispatched, leading to production of a bug report and a result marker. Condition A describes poststates where either an exception occurs (no dispatch) or the function returns early (skip) or enters a retry loop without executing any dispatch. In none of these scenarios does the code perform the mandated side effects.

**Rebuttal:** Scenario (3) in the actual behavior describes poststate at line 80 — BEFORE the dispatch. The code at lines 84–106 (lines 430–451 original) DOES execute the dispatch via `run_opencode_traced()`. The function DOES perform the mandated side effects by delegating to an OpenCode agent.

---

## How to trigger the bug

The claimed bug does not exist. The function correctly dispatches the bug-validation agent.

### Inputs

| Parameter | Value |
|-----------|-------|
| result_json_rel | `fm_agent/logic_verification_results/src/verification-py/_validate_single_bug.json` |
| proj_dir | `<temp_directory>` |
| work_dir | `<temp_directory>` |
| resume | False |
| bug_validator_path | `<repo_root>/md/bug_validator.md` |

### Expected (spec-correct) Output

The function dispatches a bug-validation agent that produces output files including `fm_agent/bug_validation/<bug_id>.md` and `fm_agent/bug_validation/<bug_id>.result.json`.

### Actual (buggy) Output

The function DOES dispatch the bug-validation agent. `run_opencode_traced()` was called with `stage=bug_validation`, `output_files=['fm_agent/bug_validation/src--verification-py--_validate_single_bug.md', 'fm_agent/bug_validation/src--verification-py--_validate_single_bug.result.json']`, and `summary='OpenCode bug validation for src--verification-py--_validate_single_bug'`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.verification import _validate_single_bug
from unittest.mock import patch

call_tracker = []
def tracker(*args, **kwargs):
    call_tracker.append(True)

with patch("src.verification.run_opencode_traced", side_effect=tracker):
    _validate_single_bug(
        result_json_rel="fm_agent/logic_verification_results/test.json",
        proj_dir="/tmp/test",
        work_dir="/tmp/test",
        resume=False,
    )
    assert call_tracker, "Expected run_opencode_traced to be called — it was not!"
    # actual (buggy?) output: No assertion error — dispatch WAS called as expected
    # expected (correct) output: dispatch called
```

---

## Probe Script

```python
"""Probe script for _validate_single_bug bug validation.

Tests whether _validate_single_bug dispatches the bug-validation agent
(via run_opencode_traced) when resume=False and no result marker exists.

Spec claim: the function dispatches a bug-validation agent.
Code reality: the function calls run_opencode_traced at line 434 of src/verification.py
(lines 84-106 in extracted form).

If dispatch is called -> NOT CONFIRMED (code matches spec -> false positive).  
If dispatch is NOT called -> CONFIRMED (code violates spec).
"""

import sys
import os

# Ensure repo root is on sys.path so 'src' can be imported
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import tempfile
import json
from unittest.mock import patch, MagicMock

# ── Mock setup ──────────────────────────────────────────────────────────

probe_tmp = tempfile.TemporaryDirectory(prefix="bug_validator_probe_")
tmp_dir = probe_tmp.name
os.makedirs(os.path.join(tmp_dir, "fm_agent", "bug_validation"), exist_ok=True)

dispatch_called = []
dispatch_kwargs = []


def fake_run_opencode_traced(proj_dir, work_dir, command, stage, function_ids,
                             input_files, output_files, summary, metadata):
    dispatch_called.append(True)
    dispatch_kwargs.append({
        "proj_dir": proj_dir,
        "work_dir": work_dir,
        "stage": stage,
        "output_files": output_files,
        "summary": summary,
        "metadata": metadata,
    })
    # Simulate agent producing the result.json marker so function returns normally
    bug_id = metadata.get("bug_id", "unknown")
    result_path = os.path.join(proj_dir, "fm_agent", "bug_validation", f"{bug_id}.result.json")
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    with open(result_path, "w") as f:
        json.dump({"confirmation_status": "confirmed"}, f)


BUG_VALIDATOR_MD_PATH = os.path.join(REPO_ROOT, "md", "bug_validator.md")

actual = None
expected = "dispatch called"
passed = False
error_msg = None

try:
    with patch("src.opencode_trace.run_opencode_traced", side_effect=fake_run_opencode_traced), \
         patch("src.verification.run_opencode_traced", side_effect=fake_run_opencode_traced), \
         patch("src.llm_client.build_llm_cli_command", return_value=["opencode", "run"]), \
         patch("src.verification.build_llm_cli_command", return_value=["opencode", "run"]), \
         patch("src.opencode_trace.function_id_from_result_path", return_value="test_func_123"), \
         patch("src.verification.function_id_from_result_path", return_value="test_func_123"), \
         patch("src.domain_knowledge.list_staged_domain_knowledge_relpaths", return_value=[]), \
         patch("src.verification.list_staged_domain_knowledge_relpaths", return_value=[]), \
         patch("src.verification.format_domain_knowledge_bullets", return_value=""), \
         patch("src.verification.config") as mock_config, \
         patch("src.verification.OPENCODE_BUG_VALIDATION_MODEL", "fake-model"), \
         patch("src.verification.logging") as mock_logging:

        mock_config.BUG_VALIDATION_MAX_RETRIES = 3

        # Import after patching
        from src.verification import _validate_single_bug

        # Test: resume=False, no existing result -> dispatch should be called
        dispatch_called.clear()
        dispatch_kwargs.clear()
        result_json_rel = "fm_agent/logic_verification_results/src/verification-py/_validate_single_bug.json"

        _validate_single_bug(
            result_json_rel=result_json_rel,
            proj_dir=tmp_dir,
            work_dir=tmp_dir,
            resume=False,
            bug_validator_path=BUG_VALIDATOR_MD_PATH,
        )

        if dispatch_called:
            actual = "dispatch called"
        else:
            actual = "dispatch NOT called"

        passed = actual != expected  # True only if dispatch missing (bug real)

except Exception as e:
    error_msg = str(e)
    import traceback
    traceback.print_exc()

# ── Output verdict ───────────────────────────────────────────────────────

if error_msg:
    print(f"ERROR: {error_msg}")
    sys.exit(1)
elif passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    detail = ""
    if dispatch_kwargs:
        dk = dispatch_kwargs[0]
        detail = (
            f" | output_files={dk['output_files']} | "
            f"stage={dk['stage']} | summary={dk['summary']}"
        )
    print(f"NOT CONFIRMED — actual: {actual!r} | expected: {expected!r}{detail}")

probe_tmp.cleanup()
```

### Probe Output

```
NOT CONFIRMED — actual: 'dispatch called' | expected: 'dispatch called' | output_files=['fm_agent/bug_validation/src--verification-py--_validate_single_bug.md', 'fm_agent/bug_validation/src--verification-py--_validate_single_bug.result.json'] | stage=bug_validation | summary=OpenCode bug validation for src--verification-py--_validate_single_bug
```
