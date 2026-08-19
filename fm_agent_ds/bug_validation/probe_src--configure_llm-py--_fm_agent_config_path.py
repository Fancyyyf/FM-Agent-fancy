import os
import sys
import tempfile
from pathlib import Path

# Ensure the repo root is on sys.path so src/ can be imported.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from src.configure_llm import default_paths

    _saved = os.environ.get("FM_AGENT_CONFIG")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            os.environ["FM_AGENT_CONFIG"] = ""
            result = default_paths(project_root)
            actual = result.toml_path
            # Spec says: if FM_AGENT_CONFIG is set in os.environ, use it
            # regardless of whether it's empty. Buggy code treats empty string
            # as falsy and falls back to project_root / "fm-agent.toml".
            expected = Path(os.environ["FM_AGENT_CONFIG"])
            passed = actual != expected
    finally:
        if _saved is None:
            os.environ.pop("FM_AGENT_CONFIG", None)
        else:
            os.environ["FM_AGENT_CONFIG"] = _saved
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
