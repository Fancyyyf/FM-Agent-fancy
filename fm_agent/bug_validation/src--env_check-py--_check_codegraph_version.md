# Bug Report: _check_codegraph_version

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/env_check-py/_check_codegraph_version.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns (True, None) when the configured codegraph version, after stripping whitespace and a leading "v" prefix, is the empty string  no version is pinned so verification is skipped
  - Otherwise, attempts to obtain the installed codegraph binary's version string by executing it with a --version flag and capturing its standard output
  - Returns (False, message) when the version string could not be obtained (binary missing, not executable, or times out), with a message identifying the configured binary directory and instructing the user to re-run ./install.sh
  - Returns (False, message) when the obtained version string does not equal the configured pinned version (after stripping whitespace and any leading "v" prefix), with a message stating the installed and pinned versions and instructing the user to re-run ./install.sh
  - Returns (True, None) when the obtained version string equals the configured pinned version
  - Never raises an exception: all error paths return (False, message) with a human-readable description

---

### Actual Behavior

After the execution of _check_codegraph_version(config), the function returns a tuple (status, msg) where status is True if the installed codegraph version matches the pinned version (or if no version is pinned), and False otherwise. The behavior is defined as follows:

- Let w = config.settings.codegraph.version.strip().removeprefix('v').
- If w is empty, return (True, None).
- Otherwise, let cmd = _codegraph_cmd(). By its specification, cmd is an absolute path to an executable file under config.settings.codegraph.bin_dir if that file exists and is executable, else the string 'codegraph' (to be resolved via PATH).
- Attempt to obtain the installed version by executing subprocess.run([cmd, '--version'], capture_output=True, text=True, timeout=10). On success, let got = strip(stdout). On any OSError or subprocess.SubprocessError, let got = ''.
- Let bin_dir = os.path.expanduser(config.settings.codegraph.bin_dir) (used only in messages).
- If got == '', return (False, 'codegraph (pinned v{want}) is not installed at {bin_dir}  run ./install.sh (C/C++ extraction falls back to the regex extractor otherwise).').
- Else if got != w, return (False, 'codegraph {got} is installed but v{w} is pinned in fm-agent.toml  re-run ./install.sh to install the pinned build.').
- Else (got == w), return (True, None).

---

## Code Evidence

Line 19: if not got:

---

## Trigger Condition

The code treats an empty version string (got='') the same as a failure to execute the binary, returning a 'not installed' error. The specification requires that if the binary executes successfully (even with empty output), the obtained version string (empty) should be compared against the pinned version. An empty string is not equal to a non-empty pinned version, so the correct behavior per spec is to return a version-mismatch error, not a missing-binary error.

---

## How to trigger the bug

The bug manifests when the codegraph binary exists and executes successfully but returns an empty version string on stdout. The `if not got:` check on line 77 of `src/env_check.py` treats the empty string as falsy, conflating "no output from a successful execution" with "binary failed to execute." Per the specification, a successful execution with empty output should be treated as an obtained version of `""`, which would mismatch any non-empty pinned version and produce a version-mismatch error.

### Inputs

| Parameter | Value |
|-----------|-------|
| `config.settings.codegraph.version` | `"1.2.3"` (non-empty pinned version) |
| `config.settings.codegraph.bin_dir` | any existing directory path |
| codegraph binary stdout | `""` (empty, simulating a binary that prints nothing on `--version`) |
| codegraph binary exit code | `0` (successful execution) |

### Expected (spec-correct) Output

`(False, "codegraph  is installed but v1.2.3 is pinned in fm-agent.toml — re-run ./install.sh to install the pinned build.")`

The specification requires distinguishing "binary executed successfully" from "binary could not be obtained." Since the binary ran and returned `""`, the obtained version is `""`, which does not equal the pinned version `"1.2.3"`. The correct error path is the version-mismatch branch.

### Actual (buggy) Output

`(False, "codegraph (pinned v1.2.3) is not installed at <bin_dir> — run ./install.sh (C/C++ extraction falls back to the regex extractor otherwise).")`

The code uses `if not got:` which evaluates to `True` when `got` is the empty string `""`. This incorrectly routes to the "not installed" error path instead of the version-mismatch path.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import patch, MagicMock
from src.env_check import _check_codegraph_version

class MockCodegraphSettings:
    version = "1.2.3"
    bin_dir = "/tmp"

class MockSettings:
    codegraph = MockCodegraphSettings()

class MockConfig:
    settings = MockSettings()

import src.languages.codegraph as cg
cg._codegraph_cmd = lambda: "codegraph"

with patch('subprocess.run') as mock_run:
    mock_result = MagicMock()
    mock_result.stdout = ""   # binary runs OK but returns empty output
    mock_run.return_value = mock_result
    status, msg = _check_codegraph_version(MockConfig())
    print(status, msg)
# actual (buggy) output: (False, 'codegraph (pinned v1.2.3) is not installed at ...')
# expected (correct) output: (False, 'codegraph  is installed but v1.2.3 is pinned ...')
```

---

## Probe Script

```python
"""Probe for bug src--env_check-py--_check_codegraph_version.

Bug: When codegraph binary executes successfully but returns empty stdout,
`if not got:` on line 77 treats empty string as "binary not installed" instead
of as a version-mismatch ('' != pinned_version).

Spec requires: if binary ran OK but output is empty, compare '' vs pinned version
and return version-mismatch error, not "not installed" error.

Workspace: all temp files under /tmp/bug_probe_env_check_codegraph/
"""
import sys
import os

# ── workspace (fresh temp dir) ──────────────────────────────────────────
WORKSPACE = "/tmp/bug_probe_env_check_codegraph"
os.makedirs(WORKSPACE, exist_ok=True)

# ── setup path to import from the project's package entry point ─────────
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot")

# Standard-library mocking utility (not a test framework)
from unittest.mock import patch, MagicMock

def main():
    # ── Build mock config: non-empty pinned version ─────────────────────
    class MockCodegraphSettings:
        version = "1.2.3"
        bin_dir = WORKSPACE  # arbitrary existing dir for message formatting

    class MockSettings:
        codegraph = MockCodegraphSettings()

    class MockConfig:
        settings = MockSettings()

    config = MockConfig()

    # ── Mock _codegraph_cmd so the import inside the function works ─────
    import src.languages.codegraph as cg
    cg._codegraph_cmd = lambda: "codegraph"

    # ── Mock subprocess.run: succeed but return empty stdout ────────────
    actual_status = None
    actual_msg = None

    try:
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = ""   # <-- empty output from successful binary
            mock_run.return_value = mock_result

            actual_status, actual_msg = _check_codegraph_version(config)
    except Exception as e:
        print(f"ERROR: {e!r}")
        sys.exit(1)

    # ── Assert: spec-correct vs buggy behavior ──────────────────────────
    # Spec says: got='' != want='1.2.3' → version-mismatch error, not "not installed"
    # Buggy code: got='' is falsy → "not installed" error

    # A version-mismatch message would contain "is installed but"
    # A "not installed" message would contain "not installed"
    if actual_status is False and "not installed" in (actual_msg or "").lower():
        print(
            f"CONFIRMED — actual: (False, {actual_msg!r}) "
            f"| expected: version-mismatch error, not 'not installed' error"
        )
    elif actual_status is False and "is installed but" in (actual_msg or "").lower():
        print(
            f"NOT CONFIRMED — actual: (False, {actual_msg!r}) "
            f"| already returns version-mismatch error per spec"
        )
    else:
        print(
            f"NOT CONFIRMED — unexpected result: ({actual_status!r}, {actual_msg!r})"
        )

# Import the target function from the package entry point
from src.env_check import _check_codegraph_version

if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — actual: (False, 'codegraph (pinned v1.2.3) is not installed at /tmp/bug_probe_env_check_codegraph — run ./install.sh (C/C++ extraction falls back to the regex extractor otherwise).') | expected: version-mismatch error, not 'not installed' error
```
