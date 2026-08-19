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
