# Bug Report: _validate_single_bug

**Source file:** `src/verification.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Derives bug_id from result_json_rel deterministically: strips the prefix
    "fm_agent/logic_verification_results/" (accepting both OS-dependent and "/"
    separators), removes the file extension, then replaces every path separator
    ("/" or os.sep) with "--"
  - Reads md/bug_validator.md and assembles a per-bug prompt consisting of
    a header identifying the target result file and the derived bug_id,
    followed by an optional user-provided domain-knowledge section (when
    staged knowledge files exist under work_dir), followed by the bug_validator
    base content unmodified
  - Atomically writes the assembled prompt to
    fm_agent/bug_validation/bug_validator_{bug_id}.md under proj_dir
    (writes to a ".tmp" sibling then os.replace, so no reader observes a
    partial file)
  - When resume is True and fm_agent/bug_validation/{bug_id}.result.json
    already exists under proj_dir AND is valid JSON, returns immediately
    without launching the bug-validation agent
  - Otherwise, invokes the configured OpenCode bug-validation model (the model
    identified by OPENCODE_BUG_VALIDATION_MODEL) with the prompt file as
    context, recording trace events for the invocation
  - Retries the invocation up to BUG_VALIDATION_MAX_RETRIES total attempts;
    returns immediately once fm_agent/bug_validation/{bug_id}.result.json
    exists under proj_dir
  - Removes the generated prompt file (bug_validator_{bug_id}.md) from proj_dir
    on exit regardless of success or failure (best-effort cleanup)
  - Raises no uncaught exception to the caller; all subprocess failures are
    logged and retried internally

---

### Actual Behavior

After the code block executes, the following post-condition holds. Let prompt_filename = os.path.join("fm_agent", "bug_validation", f"bug_validator_{bug_id}.md"), prompt_path = os.path.join(proj_dir, prompt_filename), result_relpath = os.path.join("fm_agent", "bug_validation", f"{bug_id}.result.json"), result_path = os.path.join(proj_dir, result_relpath), output_md_path = os.path.join(proj_dir, "fm_agent", "bug_validation", f"{bug_id}.md"), tmp_path = prompt_path + ".tmp". (Invariance) result_json_rel is unchanged; base_md_path unchanged; all staged domain knowledge files listed in user_knowledge_paths are unchanged; tmp_path does not exist in the filesystem. (Early return before outer try) If resume is true, result_path existed and contained valid JSON, the function returns None: prompt_path exists and content(prompt_path) = prompt_content; result_path exists with unchanged content; output_md_path does not exist; no trace file created under proj_dir/fm_agent/trace/.

---

## Code Evidence

Line 63: return

---

## Trigger Condition

Specification requires that the generated prompt file be removed on exit regardless of success or failure (best-effort cleanup). However, when resuming with a valid existing result file, the code returns early at line 63 before the outer try block, and thus never executes the finally cleanup (lines 114-118). This leaves the prompt file behind, violating the specification.

---

## How to trigger the bug

When `_validate_single_bug` is called with `resume=True` and a valid `{bug_id}.result.json` already exists under `proj_dir/fm_agent/bug_validation/`, the function returns early at line 400 before entering the `try` block at line 403. The `finally` block at lines 454-458 that removes the prompt file is never executed, leaving `bug_validator_{bug_id}.md` on disk — violating the spec requirement that the prompt file be removed "on exit regardless of success or failure."

### Inputs

| Parameter | Value |
|-----------|-------|
| `result_json_rel` | `"fm_agent/logic_verification_results/src/verification-py/_validate_single_bug.json"` |
| `proj_dir` | (temporary directory with `fm_agent/bug_validation/src--verification-py--_validate_single_bug.result.json` pre-created) |
| `work_dir` | (defaults to `proj_dir`) |
| `resume` | `True` |

### Expected (spec-correct) Output

`fm_agent/bug_validation/bug_validator_src--verification-py--_validate_single_bug.md` should NOT exist after the function returns (cleaned up by the spec-mandated cleanup).

### Actual (buggy) Output

`fm_agent/bug_validation/bug_validator_src--verification-py--_validate_single_bug.md` still exists after the function returns — the early `return` at line 400 skipped the `finally` cleanup.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, os, tempfile
from src.verification import _validate_single_bug

proj_dir = tempfile.mkdtemp()
os.makedirs(os.path.join(proj_dir, "fm_agent", "bug_validation"))

# Pre-create result file to trigger early return
result_json = {"id": "src--verification-py--_validate_single_bug", "confirmation_status": "confirmed", "attempts": 1}
with open(os.path.join(proj_dir, "fm_agent", "bug_validation", "src--verification-py--_validate_single_bug.result.json"), "w") as f:
    json.dump(result_json, f)

_validate_single_bug(
    result_json_rel="fm_agent/logic_verification_results/src/verification-py/_validate_single_bug.json",
    proj_dir=proj_dir,
    resume=True,
)

# Bug: prompt file should be cleaned up but isn't
prompt_path = os.path.join(proj_dir, "fm_agent", "bug_validation", "bug_validator_src--verification-py--_validate_single_bug.md")
print("Prompt file exists?", os.path.exists(prompt_path))
# actual (buggy) output: True (file not cleaned up)
# expected (correct) output: False (file removed per spec)
```

---

## Probe Script

```python
import json
import os
import shutil
import sys
import tempfile

# Ensure the repo root is on sys.path so `import src.verification` works
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.verification import _validate_single_bug

    proj_dir = tempfile.mkdtemp(prefix="bug_probe_")

    # Set up the directory structure needed for the early-return path
    bug_validation_dir = os.path.join(proj_dir, "fm_agent", "bug_validation")
    os.makedirs(bug_validation_dir, exist_ok=True)

    # Create a valid result.json to trigger the early return
    result_json = {"id": "src--verification-py--_validate_single_bug", "confirmation_status": "confirmed", "attempts": 1}
    result_json_rel = "fm_agent/logic_verification_results/src/verification-py/_validate_single_bug.json"
    # bug_id derived from result_json_rel: src--verification-py--_validate_single_bug
    bug_id = "src--verification-py--_validate_single_bug"
    result_path = os.path.join(proj_dir, "fm_agent", "bug_validation", f"{bug_id}.result.json")
    with open(result_path, "w") as f:
        json.dump(result_json, f)

    # The prompt file that _validate_single_bug will create
    prompt_path = os.path.join(proj_dir, "fm_agent", "bug_validation", f"bug_validator_{bug_id}.md")

    # Call with resume=True — should return early from line 400
    _validate_single_bug(result_json_rel=result_json_rel, proj_dir=proj_dir, resume=True)

    # SPEC: prompt file must be removed on exit regardless of success/failure
    # BUG: early return at line 400 skips the finally cleanup at lines 454-458
    if os.path.exists(prompt_path):
        print(f"CONFIRMED — prompt file not cleaned up: {prompt_path}")
    else:
        print(f"NOT CONFIRMED — prompt file was cleaned up (spec-compliant)")

    # Cleanup
    shutil.rmtree(proj_dir, ignore_errors=True)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — prompt file not cleaned up: /tmp/bug_probe_8v9ugdd3/fm_agent/bug_validation/bug_validator_src--verification-py--_validate_single_bug.md
```
