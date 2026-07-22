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
