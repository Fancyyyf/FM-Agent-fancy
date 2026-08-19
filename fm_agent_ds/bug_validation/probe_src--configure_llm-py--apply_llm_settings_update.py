import sys
import os
import tempfile
from pathlib import Path

# Add the src directory to the import path so we can load configure_llm
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))

try:
    from configure_llm import apply_llm_settings_update, ConfigWizardError

    with tempfile.TemporaryDirectory() as tmpdir:
        toml_path = Path(tmpdir) / "fm-agent.toml"
        # Create an empty file that exists but has no content
        toml_path.write_text("", encoding="utf-8")

        updates = {"backend": "opencode"}

        try:
            result = apply_llm_settings_update(updates, toml_path)
            # No error was raised -- the function proceeded normally.
            # This means the bug is NOT confirmed (function behaved correctly per spec).
            print(f'NOT CONFIRMED -- function returned {result!r} without raising ConfigWizardError')
        except ConfigWizardError as e:
            # Bug confirmed: function raised ConfigWizardError for an existing empty file.
            # The spec only allows ConfigWizardError when toml_path does not refer to an
            # existing file or when the updated TOML is unparseable.
            # An empty file exists and empty TOML is valid (tomllib.loads("") returns {}).
            expected = "function should have proceeded normally for an existing empty file"
            actual = f"ConfigWizardError raised: {e}"
            print(f'CONFIRMED -- actual: {actual} | expected: {expected}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
