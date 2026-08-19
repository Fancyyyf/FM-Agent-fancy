"""Probe for bug src--plugin-py--_validate_plugin_json_content.

The function _validate_plugin_json_content only checks file existence of input_md
when stage.input_md is truthy (line 143 in plugin.py). The specification requires
rejecting ANY modify stage whose input_md does not exist as a regular file,
regardless of whether input_md is truthy. An empty input_md resolves to the
plugin directory itself (not a regular file), so the function should return None,
but the code returns a PluginConfig.
"""

import json
import sys
import tempfile
from pathlib import Path

# Probe lives at fm_agent/bug_validation/; repo root is two levels up
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

try:
    from src.plugin import validate_plugin

    # Create a temporary plugin directory with a crafted plugin.json.
    # input_md="" is empty/falsy so the code skips the file-existence check,
    # but plugin_dir / "" == plugin_dir is a directory (not a regular file).
    # Per the spec, this should cause validate_plugin to return None.
    with tempfile.TemporaryDirectory(prefix="probe_plugin_") as tmpdir:
        plugin_dir = Path(tmpdir)
        plugin_json_path = plugin_dir / "plugin.json"
        plugin_json_path.write_text(
            json.dumps(
                {
                    "name": plugin_dir.name,
                    "version": "1.0.0",
                    "stages": {
                        "mystage": {
                            "type": "modify",
                            "input_md": "",
                            "output_process": "echo hello",
                        }
                    },
                }
            )
        )

        actual = validate_plugin(plugin_dir)

    # Specification says: None (input_md path is not a regular file)
    expected = None
    passed = actual is not expected  # True → bug reproduced (code did NOT return None)

except Exception as exc:
    print(f"ERROR: {exc}")
    sys.exit(1)

if passed:
    print(
        f"CONFIRMED — actual: {actual!r} | expected: {expected!r}"
        f"\n  Bug: empty input_md resolved to {plugin_dir} (a directory),"
        f" which is not a regular file, but the function returned a PluginConfig."
    )
else:
    print(
        f"NOT CONFIRMED — actual matched expected: {actual!r}"
    )
