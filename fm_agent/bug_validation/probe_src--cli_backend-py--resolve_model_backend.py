import sys
import os
from unittest.mock import patch

# The probe is run from the repo root, so cwd is the import base.
sys.path.insert(0, os.getcwd())


def main():
    try:
        import config
        from src.cli_backend import resolve_model_backend

        canonical = {"opencode", "codex-cli", "claude-cli"}
        # Monkey-patch settings.llm.backend to a non-canonical value
        with patch.object(config.settings.llm, "backend", "foobar"):
            actual = resolve_model_backend()
            # The spec requires a canonical identifier. The buggy code
            # passes the unrecognized value straight through.
            passed = actual not in canonical  # True = bug reproduced

        if passed:
            expected_fmt = f"one of {sorted(canonical)}"
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected_fmt}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
