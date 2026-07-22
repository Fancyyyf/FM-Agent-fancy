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
