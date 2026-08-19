import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.configure_llm import _preview_llm_settings_update

    with tempfile.TemporaryDirectory() as tmpdir:
        toml_path = Path(tmpdir) / "fm-agent.toml"
        toml_path.write_text('[llm]\nname = "original-model"\nprovider = "original-provider"\n')

        updates = {"name": "new-model", "provider": "new-provider"}
        actual = _preview_llm_settings_update(updates, toml_path)

        has_original_name = "original-model" in actual
        has_original_provider = "original-provider" in actual
        expected_has_current = True
        actual_has_current = has_original_name or has_original_provider
        passed = expected_has_current != actual_has_current

        if passed:
            print("CONFIRMED — output missing current TOML values.")
            print(f"  Expected to contain: original-model, original-provider")
            print(f"  Output:\n{actual}")
        else:
            print(f"NOT CONFIRMED — output contains current TOML values: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
