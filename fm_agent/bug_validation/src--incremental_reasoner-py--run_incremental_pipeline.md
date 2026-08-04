# Bug Report: run_incremental_pipeline

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/run_incremental_pipeline.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If no previous full run is detected (phases.json missing or incomplete extracted_functions), falls back to a complete full pipeline run via run_pipeline and returns None. If intent_file_path does not resolve to an existing, non-empty file, logs an error and returns None. Otherwise, executes the 10-stage incremental pipeline and returns a sorted list of relative paths to extracted function files that have confirmed bugs  i.e. where the reasoner produced a MISMATCH verdict and bug validation independently confirmed the violation. Side effects: (a) re-extracts function sources into extracted_functions/ without overwriting existing .spec.json and .info.json sidecars; (b) regenerates phases.json and topdown dependency layers; (c) updates behavioral specs (.spec.json and .info.json) for every function that is either changed relative to old_commit_id or judged relevant to the developer intent; (d) records the set of updated spec paths in fm_agent/incremental_updated_specs.json; (e) writes verification verdicts to logic_verification_results/; (f) writes confirmed bug reports to bug_validation/<bug_id>.md; (g) removes stale verification-result directories and scope-selection artifacts from the workspace before writing any new outputs.

---

### Actual Behavior

In natural language: After executing Lines 41-80, exactly one of the following has occurred:

1. If no previous full run existed (has_last_run is False), the warning was logged, run_pipeline(proj_dir, domain_knowledge_files, submodules, one_phase, extra_call_edges_path, bug_validator_path, plugin_config) was executed (completing a full 6-stage analysis and producing all outputs), and the function returned. No further statements in the function are reached.

2. If a previous full run existed (has_last_run is True), the success log was emitted and the intent file was examined:
   a) If the intent file does not exist, an error is logged and the function returns.
   b) If the intent file exists but is empty or whitespace-only, an error is logged and the function returns.
   c) If the intent file exists and is nonempty, developer_intent is set to the stripped content, an info message with its length is logged, and execution continues to the next line (the artifact-wiping comment block). In this path the function does not return; all other variables (work_dir, script_dir, input_dir, output_dir, extra_call_edges, etc.) retain the values they had in the precondition.

Logging for Stage 1 and, when reached, Stage 2 has been performed in all paths.

In formal logic: Let pre be the state immediately before Line 41. The post-state post is described by the disjunction of return-on-no-prior-run, return-on-missing-intent, return-on-empty-intent, or continue-to-stage-3 when the intent file is valid and nonempty.

---

## Code Evidence

Line 69:         with open(intent_file_path, "r") as f:
Line 70:             developer_intent = f.read().strip()

These lines (corresponding to lines 767-768 in the actual source file `src/incremental_reasoner.py`) open and read the intent file inside an `else` branch that only checks `os.path.isfile(intent_file_path)`. There is no `try/except` block wrapping the `open()` call, so any I/O error (e.g., `PermissionError`) propagates as an unhandled exception.

---

## Trigger Condition

The specification demands that if the intent file does not resolve to an existing, nonempty file (including when it cannot be read), the function logs an error and returns None. The code only checks file existence and emptiness, but does not wrap the open() call in a try/except to handle permission or I/O errors, leading to an unhandled exception that violates the specification.

---

## How to trigger the bug

Pass an `intent_file_path` that points to a file that exists (so `os.path.isfile()` returns `True`) but is not readable by the current process (e.g., file permissions set to `000`). The function will raise `PermissionError` at the `open()` call instead of logging an error and returning `None`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A temporary directory (must exist) |
| `intent_file_path` | Path to an existing file with permissions `000` (unreadable) |
| `old_commit_id` | `"HEAD"` (any valid commit-ish) |
| `domain_knowledge_files` | `None` (default) |
| `submodules` | `None` (default) |
| `check_last_run_existence` | Mocked to return `True` (so the code reaches Stage 2) |

### Expected (spec-correct) Output

The function should log an error message and return `None`.

### Actual (buggy) Output

The function raises `PermissionError: [Errno 13] Permission denied: '<path>'` — an unhandled exception.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the probe script:

```python
import os
import tempfile
from unittest.mock import MagicMock
import sys

sys.path.insert(0, "/path/to/FM-Agent")
sys.modules['main'] = MagicMock()

from src.incremental_reasoner import run_incremental_pipeline
import src.incremental_reasoner as incr

tmp = tempfile.mkdtemp()
proj_dir = os.path.join(tmp, "proj")
os.makedirs(proj_dir)
intent_file = os.path.join(tmp, "intent.txt")
with open(intent_file, "w") as f:
    f.write("test")
os.chmod(intent_file, 0o000)

incr.check_last_run_existence = lambda *a, **kw: True
incr._setup_incremental_logging = lambda wd: "/dev/null"

run_incremental_pipeline(proj_dir, intent_file, "HEAD")
# Raises: PermissionError: [Errno 13] Permission denied: '.../intent.txt'
```

---

## Probe Script

```python
import sys
import os
import tempfile
import shutil
from unittest.mock import MagicMock

# The probe runs from the repo root; ensure src/ is importable.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

# All fixtures and temp data live under a fresh temporary directory owned by the probe.
PROBE_TMP = tempfile.mkdtemp(prefix="fm_agent_probe_")
proj_dir = os.path.join(PROBE_TMP, "project")
os.makedirs(proj_dir, exist_ok=True)

# Create an intent file that exists but is unreadable (mode 0000)
intent_file = os.path.join(PROBE_TMP, "unreadable_intent.txt")
with open(intent_file, "w") as f:
    f.write("test developer intent content")
os.chmod(intent_file, 0o000)

old_commit_id = "HEAD"

actual = None

try:
    # Mock the 'main' module before it gets imported by the function body.
    # This prevents any FM-Agent workflow from starting.
    mock_main = MagicMock()
    mock_main.run_pipeline = MagicMock(return_value=None)
    mock_main._run_setup_extract = MagicMock(return_value=None)
    mock_main.main = MagicMock(return_value=None)
    sys.modules['main'] = mock_main

    from src.incremental_reasoner import run_incremental_pipeline
    import src.incremental_reasoner as incr_mod

    # Mock check_last_run_existence to return True so we reach the
    # intent-file-reading code path (Stage 2) without falling back to
    # a full pipeline run (which would start FM-Agent).
    original_check = incr_mod.check_last_run_existence
    incr_mod.check_last_run_existence = lambda *a, **kw: True

    # Mock _setup_incremental_logging so it doesn't set up real file handlers
    original_setup_logging = incr_mod._setup_incremental_logging
    incr_mod._setup_incremental_logging = lambda wd: os.path.join(wd, "incremental_dummy.log")

    # Also mock stage_domain_knowledge_files to avoid side effects
    if hasattr(incr_mod, 'stage_domain_knowledge_files'):
        original_stage = incr_mod.stage_domain_knowledge_files
        incr_mod.stage_domain_knowledge_files = lambda *a, **kw: []

    result = run_incremental_pipeline(
        proj_dir,
        intent_file,
        old_commit_id,
    )
    # If we get here, no exception was raised — the bug was NOT triggered.
    actual = result
    print(f"NOT CONFIRMED — function returned {result!r} without raising an exception")

except PermissionError as e:
    actual = f"PermissionError: {e}"
    print(f"CONFIRMED — PermissionError raised: {e}")
except OSError as e:
    actual = f"OSError: {e}"
    print(f"CONFIRMED — OSError raised: {e}")
except ImportError as e:
    actual = f"ImportError: {e}"
    print(f"ERROR: ImportError — {e}")
    sys.exit(1)
except Exception as e:
    actual = f"{type(e).__name__}: {e}"
    print(f"CONFIRMED — unexpected exception {type(e).__name__}: {e}")
finally:
    # Cleanup: restore mocked modules and functions
    if 'incr_mod' in dir():
        if 'original_check' in dir():
            incr_mod.check_last_run_existence = original_check
        if 'original_setup_logging' in dir():
            incr_mod._setup_incremental_logging = original_setup_logging
        if 'original_stage' in dir():
            incr_mod.stage_domain_knowledge_files = original_stage

    # Restore the real main module
    sys.modules.pop('main', None)

    # Clean up temp files and directories
    try:
        if os.path.exists(intent_file):
            os.chmod(intent_file, 0o644)
    except Exception:
        pass
    if os.path.isdir(PROBE_TMP):
        shutil.rmtree(PROBE_TMP, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — PermissionError raised: [Errno 13] Permission denied: '/tmp/fm_agent_probe_8tm61xz6/unreadable_intent.txt'
```
