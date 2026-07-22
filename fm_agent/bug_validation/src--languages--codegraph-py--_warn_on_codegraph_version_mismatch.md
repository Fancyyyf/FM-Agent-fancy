# Bug Report: _warn_on_codegraph_version_mismatch

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/languages/codegraph-py/_warn_on_codegraph_version_mismatch.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns None; never raises an exception.
  - The function has no externally observable side effect unless all of the
    following conditions are met:
      (a) the configured codegraph version, after stripping leading and trailing
          whitespace and removing any leading "v" prefix, is non-empty;
      (b) executing the command referred to by cmd with the argument "--version"
          succeeds as a subprocess and produces non-empty output after stripping
          leading and trailing whitespace from its captured stdout;
      (c) that output does not equal the configured version after each has been
          stripped of whitespace and any leading "v" prefix.
  - When all conditions (a), (b), and (c) are met: a log record at WARNING
    severity is emitted whose message identifies both the version string obtained
    from the command output and the configured version string from
    fm-agent.toml.

---

### Actual Behavior

The function completes without raising any exception. Let V = settings.codegraph.version.strip().removeprefix('v'). If V is empty, no warning is logged. Otherwise, the function attempts to run subprocess.run([cmd, '--version'], capture_output=True, text=True, timeout=10). If this raises OSError or subprocess.SubprocessError, no warning is logged. If it succeeds, let output = the stripped stdout of the completed process. If output is truthy and output != V, then a WARNING log record is emitted via logging.warning with the format string 'codegraph %r does not match the pinned %r (fm-agent.toml [codegraph].version); re-run install.sh to update.' and arguments (output, V). Otherwise, no warning is logged. No other side effects occur.

Formally: Let V = strip(removeprefix(settings.codegraph.version, 'v')). The post-condition is:
( (V='') ∨ (subprocess.run([cmd,'--version'],capture_output=True,text=True,timeout=10) raises OSError or SubprocessError) ∨ (let stdout = strip(result.stdout); (stdout ≠ '' ∨ stdout ≠ V)) ) → no WARNING log with the specified message is emitted;
(V ≠ '' ∧ subprocess succeeds ∧ let s = strip(result.stdout); s ≠ '' ∧ s ≠ V) → a WARNING log with the specified message and arguments (s, V) is emitted.

---

## Code Evidence

Line 6: want = settings.codegraph.version.strip().removeprefix("v"); Line 15: if got and got != want:

---

## Trigger Condition

The code removes the leading 'v' only from the configured version, not from the command output. The specification requires that both strings be stripped and have any leading 'v' removed before comparison. When both strings match after this normalization (e.g., configured 'v1.0' and output 'v1.0'), the code incorrectly emits a warning, violating condition (c) of the specification.

---

## How to trigger the bug

The bug is triggered when:
1. The configured codegraph version has a leading "v" (e.g., "v1.0" in fm-agent.toml)
2. The codegraph binary also reports its version with a leading "v" as stdout (e.g., "v1.0")

The code normalizes the configured version by removing the leading "v" (`want = "1.0"`), but only strips whitespace from the command output (`got = "v1.0"`). The comparison `got != want` evaluates to `"v1.0" != "1.0"` → `True`, causing a false WARNING to be emitted even though the versions are semantically identical after proper normalization.

### Inputs

| Parameter | Value |
|-----------|-------|
| `cmd` | `"codegraph"` |
| `settings.codegraph.version` | `"v1.0"` |
| Subprocess stdout (mocked) | `"v1.0\n"` |

### Expected (spec-correct) Output

No WARNING log emitted — both versions normalize to `"1.0"` after stripping and removing the leading "v".

### Actual (buggy) Output

WARNING log emitted: `codegraph 'v1.0' does not match the pinned '1.0' (fm-agent.toml [codegraph].version); re-run install.sh to update.`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, ".")

from unittest.mock import patch, MagicMock

# Set configured version to "v1.0"
class MockCodegraphCfg:
    version = "v1.0"
    bin_dir = "/tmp"
    repo = "fmagent-project/codegraph"

class MockSettings:
    codegraph = MockCodegraphCfg()

with patch("src.languages.codegraph.settings", MockSettings()):
    import src.languages.codegraph as cg
    with patch("src.languages.codegraph.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.stdout = "v1.0\n"
        mock_run.return_value = mock_result
        
        cg._warn_on_codegraph_version_mismatch("codegraph")
        # A WARNING log is emitted despite matching versions
        # actual (buggy) output: WARNING emitted
        # expected (correct) output: no WARNING emitted
```

---

## Probe Script

```python
"""Probe for bug src--languages--codegraph-py--_warn_on_codegraph_version_mismatch.

Bug: `_warn_on_codegraph_version_mismatch` removes the leading 'v' only from
`settings.codegraph.version` (the 'want' side) but NOT from the command output
(the 'got' side). When both strings differ only by a leading 'v' (e.g. configured
"v1.0" and command output "v1.0"), the code incorrectly emits a WARNING because
"v1.0" != "1.0". Per spec, both sides should be normalized before comparison,
so no warning should be emitted when the versions are semantically equal.

Workspace: all temp files under /tmp/bug_probe_warn_version_mismatch/
"""
import sys
import os

# ── workspace (fresh temp dir) ──────────────────────────────────────────
WORKSPACE = "/tmp/bug_probe_warn_version_mismatch"
os.makedirs(WORKSPACE, exist_ok=True)

# ── setup path to import from the project ───────────────────────────────
sys.path.insert(0, "/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot")

from unittest.mock import patch, MagicMock


def main():
    # ── Mock config.settings to set codegraph.version = "v1.0" ──────────
    class MockCodegraphCfg:
        version = "v1.0"
        bin_dir = WORKSPACE
        repo = "fmagent-project/codegraph"

    class MockSettings:
        codegraph = MockCodegraphCfg()

    # Replace the 'settings' reference that codegraph.py imports at the top
    with patch("src.languages.codegraph.settings", MockSettings()):
        # ── Import the target function AFTER patching settings ──────────
        import src.languages.codegraph as cg

        # ── Mock subprocess.run to return stdout "v1.0" ─────────────────
        # The command output has a leading "v" (e.g. "v1.0\n")
        warning_was_called = [False]
        warning_msg_holder = [None]

        def capture_warning(msg, *args):
            warning_was_called[0] = True
            warning_msg_holder[0] = msg % args if args else msg

        try:
            with patch("src.languages.codegraph.subprocess.run") as mock_run:
                with patch("src.languages.codegraph.logging.warning",
                           side_effect=capture_warning):
                    mock_result = MagicMock()
                    mock_result.stdout = "v1.0\n"
                    mock_run.return_value = mock_result

                    # Call the function under test
                    cg._warn_on_codegraph_version_mismatch("codegraph")
        except Exception as e:
            print(f"ERROR: {e!r}")
            sys.exit(1)

    # ── Oracle ──────────────────────────────────────────────────────────
    # Spec says: both strings must be stripped and have leading "v" removed
    # before comparison.  wanted = "v1.0" → "1.0", got = "v1.0" → should also
    # be "1.0" after normalization. Since they are equal, NO warning should be
    # emitted.
    #
    # Bug: got is only stripped ("v1.0"), not v-removed → "v1.0" != "1.0"
    # → warning IS emitted, violating the spec.

    # want after normalization: "v1.0".strip().removeprefix("v") = "1.0"
    # got after normalization (spec): "v1.0".strip().removeprefix("v") = "1.0"
    # got after normalization (code): "v1.0".strip() = "v1.0"
    # code compares "v1.0" != "1.0" → True → warning emitted (BUG!)

    if warning_was_called[0]:
        print(
            "CONFIRMED — WARNING emitted despite versions matching after "
            f"normalization: {warning_msg_holder[0]!r}"
        )
    else:
        print(
            "NOT CONFIRMED — no WARNING emitted; the code may have been fixed"
        )


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — WARNING emitted despite versions matching after normalization: "codegraph 'v1.0' does not match the pinned '1.0' (fm-agent.toml [codegraph].version); re-run install.sh to update."
```
