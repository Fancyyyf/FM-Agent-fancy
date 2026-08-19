import sys
import tempfile
import json
from pathlib import Path

# Add repo root to path for public entry-point import
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root))

try:
    from src.plugin import validate_plugin

    # Create a temp directory for fixtures (not in fm_agent/)
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = Path(tmpdir) / "my_plugin"
        plugin_dir.mkdir()

        # plugin.json has a name DIFFERENT from the directory name.
        # Spec requires PluginConfig.name == plugin_dir.name ("my_plugin").
        # Bug claim: code only checks non-empty, not that name matches dir name.
        plugin_json = plugin_dir / "plugin.json"
        plugin_json.write_text(json.dumps({
            "name": "different_name",
            "version": "1.0.0",
            "stages": {}
        }))

        actual = validate_plugin(plugin_dir)

        if actual is not None:
            # Code returned a PluginConfig — check if name matches dir name
            passed = actual.name != "my_plugin"
            if passed:
                print(
                    f"CONFIRMED — actual name: {actual.name!r} | "
                    f"expected directory name: 'my_plugin'"
                )
            else:
                print(
                    f"NOT CONFIRMED — name matches directory name: "
                    f"{actual.name!r}"
                )
        else:
            # Code correctly returned None for mismatched name
            print(
                "NOT CONFIRMED — validate_plugin returned None for "
                "plugin.json with name 'different_name' in directory 'my_plugin' "
                "(code correctly rejects the name mismatch)"
            )

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
