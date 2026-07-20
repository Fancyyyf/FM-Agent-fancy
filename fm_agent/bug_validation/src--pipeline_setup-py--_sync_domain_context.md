# Bug Report: _sync_domain_context

**Source file:** `src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The specification claims the function should retry agent invocation up to `OPENCODE_MAX_RETRIES` times with a delay, and after exhaustion log a warning and return without raising. The bug report claims the code "does not implement any retry logic; upon nonzero exit it raises subprocess.CalledProcessError instead of retrying and finally logging a warning."

Reading the actual source code at `src/pipeline_setup.py` lines 211-244 reveals that the function **does** implement the retry logic described in the specification. The code contains a `for attempt in range(1, OPENCODE_MAX_RETRIES + 1)` loop with a `try/except subprocess.CalledProcessError` handler that logs a warning, sleeps for 10 seconds, and continues to the next attempt. After the loop exhausts all retries, it logs a final warning and returns without raising.

The probe script confirms this by mocking `run_opencode_traced` to always raise `CalledProcessError`, then verifying that `_sync_domain_context` retries exactly `OPENCODE_MAX_RETRIES` (5) times and returns without propagating the exception.

### Specification Claim

- Returns without effect when changed_phases is empty and no phase removal or
    renumbering has occurred.
  - Returns without invoking the LLM agent when the domain_context subdirectory
    (spec_prompts/domain_context/) is absent under work_dir.
  - Returns without invoking the LLM agent when every changed phase owns zero
    source files per phases.json and no cleanup renumbering/removal is pending.
  - When invoked, the LLM agent receives phases.json and all staged domain-knowledge
    Markdown files as input and is instructed to regenerate phase_NN_types.txt
    files only for phases whose source-file composition changed.
  - The agent invocation is retried up to a configured maximum (OPENCODE_MAX_RETRIES),
    with a delay between attempts. On success the function returns; after all
    retries are exhausted, a warning is logged and the function returns without
    raising — this is a best-effort operation.
  - Every agent invocation is traced as an opencode_call event recorded in
    fm_agent/trace/events.jsonl.
  - The agent is constrained to write only under fm_agent/ and must not modify
    any existing project source files.

---

### Actual Behavior

The actual code at lines 211-244 implements a retry loop:

```python
for attempt in range(1, OPENCODE_MAX_RETRIES + 1):
    try:
        run_opencode_traced(...)
        return
    except subprocess.CalledProcessError as e:
        logging.warning(
            "Domain-context sync attempt %d/%d failed: opencode exited %s",
            attempt, OPENCODE_MAX_RETRIES, e.returncode,
        )
        if attempt < OPENCODE_MAX_RETRIES:
            time.sleep(10)

logging.warning(
    "Domain-context sync did not complete after %d attempts; "
    "phase_NN_types.txt files may be out of sync with phases.json.",
    OPENCODE_MAX_RETRIES,
)
```

This matches the specification exactly: retries up to `OPENCODE_MAX_RETRIES` (5), sleeps between attempts, logs warnings on each failure, and returns without raising after exhaustion.

---

## Code Evidence

The code after the earlyreturn checks invokes the agent via a subprocess but does not implement any retry logic; upon nonzero exit it raises subprocess.CalledProcessError instead of retrying and finally logging a warning.

**Note:** The above code evidence from the bug report is **incorrect**. The actual source code at `src/pipeline_setup.py` lines 211-244 does implement retry logic. The code contains a `for attempt in range(1, OPENCODE_MAX_RETRIES + 1)` loop wrapping `run_opencode_traced()` in a try/except block that catches `subprocess.CalledProcessError`, logs a warning, sleeps, and retries. After the loop exhausts, a final warning is logged and the function returns normally (no exception propagates).

---

## Trigger Condition

Specification requires that the agent invocation be retried up to OPENCODE_MAX_RETRIES with a delay, and after exhaustion a warning is logged and the function returns without raising. The actual implementation raises on the first failure, violating the besteffort behaviour specified.

**Note:** The trigger condition is **not valid** because the actual implementation does NOT raise on the first failure. Our probe confirms the function retries 5 times and returns cleanly after exhaustion.

---

## How to trigger the bug

The claimed bug cannot be triggered — the code already implements retry logic.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | any existing directory |
| `work_dir` | a directory containing `phases.json` and `spec_prompts/domain_context/` |
| `changed_phases` | `{1}` (a set containing a phase that has source files in phases.json) |
| `phase_cleanup` | `None` |

### Expected (spec-correct) Output

Function retries up to `OPENCODE_MAX_RETRIES` (5) times when `run_opencode_traced` fails, then logs a warning and returns without raising.

### Actual (buggy) Output

Function retries 5 times and returns without raising — matching the spec. No bug present.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import src.pipeline_setup as pkg
import subprocess, tempfile, os, json, unittest.mock

work_dir = tempfile.mkdtemp()
os.makedirs(os.path.join(work_dir, "spec_prompts", "domain_context"))
with open(os.path.join(work_dir, "phases.json"), "w") as f:
    json.dump({"phases": [{"phase": 1, "modules": [{"source_files": ["src/x.py"]}]}]}, f)

call_count = [0]
def fail(**kw):
    call_count[0] += 1
    raise subprocess.CalledProcessError(1, "mock")

with unittest.mock.patch.object(pkg, "run_opencode_traced", fail), \
     unittest.mock.patch("time.sleep"):
    pkg._sync_domain_context(proj_dir=tempfile.mkdtemp(), work_dir=work_dir, changed_phases={1})
# actual (buggy) output: returns normally after 5 retries, no exception raised
# expected (correct) output: returns normally after retries, no exception raised
```

---

## Probe Script

```python
"""Probe: verify _sync_domain_context retries on subprocess failure.

Bug claim: _sync_domain_context does not implement retry logic and raises
subprocess.CalledProcessError on first failure, violating the best-effort spec.

Actual spec requirement: Retry up to OPENCODE_MAX_RETRIES with delay; after
exhaustion, log a warning and return without raising.
"""

import sys
import os
import json
import tempfile
import subprocess
import unittest.mock

# ── setup: import the package via its public entry point ──────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import src.pipeline_setup as pkg
except Exception as e:
    print(f'ERROR: could not import src.pipeline_setup: {e}')
    sys.exit(1)

CONFIRMED_MSG = "CONFIRMED"
NOT_CONFIRMED_MSG = "NOT CONFIRMED"


def _create_minimal_phases(work_dir, phase_num, source_files):
    """Create a minimal phases.json with one phase owning some source files."""
    phases_path = os.path.join(work_dir, "phases.json")
    data = {
        "phases": [
            {
                "phase": phase_num,
                "modules": [{"source_files": list(source_files)}],
            }
        ]
    }
    with open(phases_path, "w") as f:
        json.dump(data, f)


def main():
    proj_dir = tempfile.mkdtemp(prefix="fm_probe_proj_")
    work_dir = tempfile.mkdtemp(prefix="fm_probe_work_")

    try:
        # Create domain_context directory (required to pass early-return guard)
        domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
        os.makedirs(domain_dir, exist_ok=True)

        # Create a minimal phases.json so _phase_source_files finds phase 1
        _create_minimal_phases(work_dir, 1, ["src/example.py"])

        # Patch run_opencode_traced to always fail with CalledProcessError
        call_count = [0]

        def failing_traced(**kwargs):
            call_count[0] += 1
            raise subprocess.CalledProcessError(returncode=1, cmd="mock-cmd")

        # Patch time.sleep to avoid waiting 10s per retry
        with unittest.mock.patch.object(pkg, "run_opencode_traced", failing_traced), \
             unittest.mock.patch("time.sleep", return_value=None):

            # Call the function — spec says it should retry and return without raising
            try:
                pkg._sync_domain_context(
                    proj_dir=proj_dir,
                    work_dir=work_dir,
                    changed_phases={1},
                    phase_cleanup=None,
                )
            except subprocess.CalledProcessError:
                # Bug CONFIRMED: function raised instead of retrying
                expected_retries = pkg.OPENCODE_MAX_RETRIES
                print(
                    f"{CONFIRMED_MSG} — _sync_domain_context raised CalledProcessError "
                    f"after {call_count[0]} call(s); expected {expected_retries} retries "
                    f"per spec (OPENCODE_MAX_RETRIES={expected_retries})"
                )
                return

        # Check that retries happened
        expected_retries = pkg.OPENCODE_MAX_RETRIES
        if call_count[0] == expected_retries:
            print(
                f"{NOT_CONFIRMED_MSG} — _sync_domain_context retried {call_count[0]} "
                f"times and returned without raising, matching the spec "
                f"(OPENCODE_MAX_RETRIES={expected_retries})"
            )
        elif call_count[0] > 0:
            print(
                f"{NOT_CONFIRMED_MSG} — _sync_domain_context retried {call_count[0]} "
                f"times before returning; spec requires up to {expected_retries} retries "
                f"(OPENCODE_MAX_RETRIES={expected_retries}). Retry logic exists, "
                f"just with a different count than expected."
            )
        else:
            print(
                f"{CONFIRMED_MSG} — _sync_domain_context called run_opencode_traced "
                f"0 times (unexpected)"
            )

    finally:
        import shutil
        shutil.rmtree(proj_dir, ignore_errors=True)
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
WARNING:root:Domain-context sync attempt 1/5 failed: opencode exited 1
WARNING:root:Domain-context sync attempt 2/5 failed: opencode exited 1
WARNING:root:Domain-context sync attempt 3/5 failed: opencode exited 1
WARNING:root:Domain-context sync attempt 4/5 failed: opencode exited 1
WARNING:root:Domain-context sync attempt 5/5 failed: opencode exited 1
WARNING:root:Domain-context sync did not complete after 5 attempts; phase_NN_types.txt files may be out of sync with phases.json.
NOT CONFIRMED — _sync_domain_context retried 5 times and returned without raising, matching the spec (OPENCODE_MAX_RETRIES=5)
```
