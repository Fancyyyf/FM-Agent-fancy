import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add repo root to path for imports
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

tmpdir = Path(tempfile.mkdtemp(prefix="bug_probe_"))

try:
    # Create minimal fm-agent.toml so apply_llm_settings_update doesn't bail
    toml_path = tmpdir / "fm-agent.toml"
    toml_path.write_text("[llm]\nname = \"test-model\"\n")
    # Create empty .env to avoid side effects
    env_path = tmpdir / ".env"
    env_path.write_text("")

    from src.configure_llm import run_llm_settings_update

    # Pass a key NOT in _LLM_TOML_KEYS — spec mandates non-zero return
    actual = run_llm_settings_update(
        tmpdir,
        {"invalid_key": "value"},
        assume_yes=True,
    )
    # The spec says it should return non-zero (≠ 0) for invalid keys
    # If it returned 0, the bug is confirmed (wrong return value)
    expected = "non-zero integer (≠ 0)"
    passed = actual == 0
    actual_repr = repr(actual)
except Exception as e:
    # Unhandled exception — also a bug per spec
    # Spec requires returning non-zero, not crashing with an exception
    actual_repr = f"Exception: {type(e).__name__}: {e}"
    expected = "non-zero integer (≠ 0) — function should not raise"
    passed = True  # Bug confirmed
finally:
    shutil.rmtree(str(tmpdir), ignore_errors=True)

if passed:
    print(f"CONFIRMED — actual: {actual_repr} | expected: {expected}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual_repr}")
