import sys
import tempfile
import io
from pathlib import Path

# Ensure the repo root is on sys.path so src.plugin is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.plugin import load_plugins


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        plugins_dir = Path(tmpdir)

        # Create an invalid plugin subdirectory — no plugin.json present
        invalid_plugin = plugins_dir / "invalid_plugin"
        invalid_plugin.mkdir()

        # Create a hidden directory — should be silently skipped
        (plugins_dir / ".hidden").mkdir()

        # Create __pycache__ — should be silently skipped
        (plugins_dir / "__pycache__").mkdir()

        # Create a file (not a directory) — should be skipped
        (plugins_dir / "not_a_dir.txt").write_text("hello")

        # Create a valid plugin with a real plugin.json
        valid_plugin = plugins_dir / "valid_plugin"
        valid_plugin.mkdir()
        (valid_plugin / "plugin.json").write_text(
            '{"name": "valid_plugin", "version": "1.0.0"}'
        )

        # Capture stdout during load_plugins
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            result = load_plugins(plugins_dir)
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()

        # Spec claim: invalid plugins are skipped after printing their error reason
        # The actual code: validate_plugin (called by load_plugins) prints the error
        #
        # If the spec is satisfied, we expect:
        # 1. result has only valid_plugin (invalid_plugin is skipped)
        # 2. The error reason for invalid_plugin ("plugin.json not found") is in stdout

        expected_empty_for_valid = "valid_plugin" in result
        expected_no_invalid = "invalid_plugin" not in result
        error_printed = "plugin.json not found" in output

        actual_satisfies_spec = (
            expected_empty_for_valid
            and expected_no_invalid
            and error_printed
        )

        if actual_satisfies_spec:
            print(
                "NOT CONFIRMED — error reason 'plugin.json not found' was printed "
                f"for invalid plugin; spec satisfied. result={list(result.keys())}"
            )
        else:
            print(
                f"CONFIRMED — spec claims invalid plugins are skipped "
                f"after printing error reason, but "
                f"stdout={output!r}, result_keys={list(result.keys())}, "
                f"error_printed={error_printed}"
            )


if __name__ == "__main__":
    main()
