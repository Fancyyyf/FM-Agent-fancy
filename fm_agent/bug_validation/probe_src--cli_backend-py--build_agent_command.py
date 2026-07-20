import sys
import os

# Add repo root to path so the "src" package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from src.cli_backend import build_agent_command
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

actual = None
expected = None
passed = None

try:
    cwd = os.path.abspath(os.getcwd())
    files = ["test_file.txt"]

    actual = build_agent_command(
        model="test-model",
        prompt="test prompt",
        cwd=cwd,
        files=files,
        backend="codex-cli",
    )

    # Spec says: "each file path in files is attached as context to the
    # backend invocation." That means file paths SHOULD appear in argv.
    # Bug claim: the code only composes stdin, never adds file paths to argv.
    file_path_in_argv = any("test_file.txt" in arg for arg in actual.argv)
    expected_contains_files = True
    passed = not file_path_in_argv  # bug confirmed when files NOT in argv

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — file path 'test_file.txt' NOT found in argv: {actual.argv}")
else:
    print(f"NOT CONFIRMED — file path found in argv: {actual.argv}")
