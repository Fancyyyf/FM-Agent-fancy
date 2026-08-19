"""Probe for bug src--cli_backend-py--run_agent_for_messages.

Bug: run_agent_for_messages always returns an empty dict {} for usage metadata,
but the specification requires a dict containing token usage metadata.
"""
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure repo root is on sys.path so the src package is importable.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

BUG_ID = "src--cli_backend-py--run_agent_for_messages"


def main():
    try:
        mock_result = MagicMock()
        mock_result.stdout = "Hello, this is the agent response.\n"
        mock_result.returncode = 0

        mock_cmd = MagicMock()
        mock_cmd.argv = ["echo", "mock"]
        mock_cmd.stdin = None
        mock_cmd.backend = "mock-backend"

        # Patch subprocess.run (to avoid real CLI execution) and
        # build_agent_command (to avoid config dependency) before calling.
        with patch("src.cli_backend.subprocess.run", return_value=mock_result), \
             patch("src.cli_backend.build_agent_command", return_value=mock_cmd):
            from src.cli_backend import run_agent_for_messages

            actual_text, actual_usage = run_agent_for_messages(
                "test-model",
                [{"role": "user", "content": "What is 2+2?"}],
            )

        expected_text = "Hello, this is the agent response."

        # The bug is confirmed if:
        # - the text output is a non-empty string matching stdout
        # - the usage dict is empty ({}), but the spec requires token metadata
        is_bug = (
            isinstance(actual_text, str)
            and len(actual_text) > 0
            and actual_text == expected_text
            and actual_usage == {}
        )

    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    if is_bug:
        print(
            f"CONFIRMED — actual: (response={actual_text!r}, usage={actual_usage!r}) | "
            f"spec requires usage dict with token metadata, but code returns empty dict"
        )
    else:
        print(
            f"NOT CONFIRMED — actual: (response={actual_text!r}, usage={actual_usage!r})"
        )


if __name__ == "__main__":
    main()
