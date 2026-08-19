# Bug Report: _warn_on_codegraph_version_mismatch

**Source file:** `fm_agent/extracted_functions/src/languages/codegraph-py/_warn_on_codegraph_version_mismatch.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If the configured codegraph.version (after stripping whitespace and removing any leading 'v') is empty, returns immediately with no side effects. If the executable at cmd cannot be reached or fails to report its version, returns silently with no side effects. If the version reported by the executable differs from the configured version, a warning is logged containing both version strings. The function never raises an exception and never blocks or terminates the calling process.

---

### Actual Behavior

The function returns None. No exception is propagated. The global state (including `settings.codegraph.version`) is unchanged. If `want` (computed as `settings.codegraph.version.strip().removeprefix('v')`) is empty, the function returns immediately with no side effects. If `want` is nonempty, the subprocess `cmd --version` is run with `capture_output=True`, `text=True`, `timeout=10`. If an `OSError` or `subprocess.SubprocessError` is raised, it is caught and the function returns without logging. If the subprocess completes successfully, its stdout is stripped into `got`. If `got` is nonempty and `got != want`, then `logging.warning` is called with the specific message containing `got` and `want`; otherwise, no warning is logged. No other output or state change occurs.

Formally:
Let `want = settings.codegraph.version.strip().removeprefix('v')`.
Post-condition:
  return = None
   (want = ''    no warning logged  subprocess not executed)
   (want  ''  
      ( (subprocess.run raises OSError  subprocess.SubprocessError)
           no warning logged )
       ( no such exception occurs 
            let `got = subprocess_result.stdout.strip()` in
            ( (got  ''  got  want)    warning_logged_with(got, want) )
        )
    )

---

## Code Evidence

Line 15: if got and got != want:

---

## Trigger Condition

The code's condition requires `got` to be truthy before checking inequality, so it skips the warning when the executable reports an empty version string. The specification demands a warning whenever the reported version differs, even if it is empty.

---

## How to trigger the bug

When a codegraph executable produces an empty or whitespace-only stdout for `--version`, the value `got` becomes `""` after `.strip()`. The condition `if got and got != want` evaluates `got` first — since `""` is falsy, Python short-circuits and never evaluates `got != want`. The spec requires a warning whenever `got != want`, regardless of whether `got` is empty.

### Inputs

| Parameter | Value |
|-----------|-------|
| `cmd` | `/usr/bin/true` (arbitrary — subprocess is mocked) |
| `settings.codegraph.version` (via env) | `"v1.0.0"` |
| Subprocess `--version` stdout | `"\n"` (whitespace only — strips to `""`) |

### Expected (spec-correct) Output

`logging.warning` is called because `got="" != want="1.0.0"` — the versions differ.

### Actual (buggy) Output

No warning is logged. `got=""` is falsy, so `if got and got != want` short-circuits to `False` before evaluating the inequality.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import os, logging, subprocess
from unittest.mock import patch

os.environ["CODEGRAPH_VERSION"] = "v1.0.0"
from src.languages.codegraph import _warn_on_codegraph_version_mismatch

logging.basicConfig(level=logging.WARNING)

with patch("subprocess.run") as mock_run:
    mock_run.return_value.stdout = "\n"   # empty after strip()
    mock_run.return_value.returncode = 0
    _warn_on_codegraph_version_mismatch("/usr/bin/true")

# No warning printed despite got != want — BUG
// actual (buggy) output: (no warning logged)
// expected (correct) output: WARNING:root:codegraph '' does not match the pinned '1.0.0' ...
```

---

## Probe Script

```py
#!/usr/bin/env python3
"""Probe script: _warn_on_codegraph_version_mismatch short-circuits on
empty version string from the executable.

Bug ID: src--languages--codegraph-py--_warn_on_codegraph_version_mismatch

The code at line 15 uses: if got and got != want:
When the executable reports an empty version (got=''), the condition
short-circuits on `got` (falsy) and never evaluates `got != want`.
The spec requires a warning whenever versions differ, even if empty.
"""

import sys
import os

# Ensure the repo root is on sys.path so `import config` and `import src`
# resolve correctly (Python adds the script's directory, not the cwd).
sys.path.insert(0, os.getcwd())

# Must set env BEFORE importing anything that reads fm-agent config.
# This forces want = "1.0.0" after strip()+removeprefix("v").
os.environ["CODEGRAPH_VERSION"] = "v1.0.0"

import logging
from unittest.mock import patch


def main():
    # Import the private helper directly — FM-Agent self-validation guard
    # says "test only the smallest relevant unit with mocks or fixtures."
    from src.languages.codegraph import _warn_on_codegraph_version_mismatch

    warning_logged = False
    warning_message = ""

    original_warning = logging.warning

    def _capture(msg, *args, **kwargs):
        nonlocal warning_logged, warning_message
        warning_logged = True
        warning_message = msg % args if args else msg

    logging.warning = _capture

    try:
        # Mock subprocess.run to simulate a codegraph binary that prints
        # only whitespace/newlines for --version (got = "" after strip).
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "\n"
            mock_run.return_value.returncode = 0

            _warn_on_codegraph_version_mismatch("/usr/bin/true")

        # --- Verdict ---
        # want = "v1.0.0".strip().removeprefix("v") = "1.0.0"
        # got  = "\n".strip() = ""
        #
        # Spec claim: if got != want -> log warning with both strings.
        # "" != "1.0.0" is True, so the spec requires a warning here.
        #
        # Code:     if got and got != want:
        #           if ""  and ...       -> False (short-circuit on falsy got)
        #           Warning is NEVER logged.
        #
        # Therefore: spec requires warning, code skips it → BUG CONFIRMED.

        if warning_logged:
            print(
                "NOT CONFIRMED — warning was unexpectedly logged"
            )
            print(f"  Warning message: {warning_message!r}")
        else:
            print(
                "CONFIRMED — bug reproduced: no warning logged when executable "
                "reports empty version string, but spec requires warning when "
                "versions differ"
            )
            print(
                "  want: '1.0.0' (from CODEGRAPH_VERSION=v1.0.0)"
            )
            print(
                "  got:  '' (empty, from mocked subprocess.run stdout='\\n')"
            )
            print(
                "  Root cause: 'if got and got != want' short-circuits on "
                "falsy got before checking inequality"
            )

    except Exception as exc:
        print(f"ERROR: {exc!r}")
        sys.exit(1)

    finally:
        logging.warning = original_warning


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — bug reproduced: no warning logged when executable reports empty version string, but spec requires warning when versions differ
  want: '1.0.0' (from CODEGRAPH_VERSION=v1.0.0)
  got:  '' (empty, from mocked subprocess.run stdout='\n')
  Root cause: 'if got and got != want' short-circuits on falsy got before checking inequality
```
