# Bug Report: _validate_plugin_json_content

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/plugin-py/_validate_plugin_json_content.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns None if any of the following validation conditions fail, after printing a diagnostic message to stdout identifying the plugin name and the specific failure condition: (1) the value of the key 'name' in data does not equal name, (2) the key 'version' in data is missing or its value is empty/falsy, (3) the key 'stages' in data is not a dict, (4) any value in stages is not a dict, (5) for any stage name in stages, a PluginStageConfig constructed from the stage's data produces a non-empty error list when validated, (6) any stage whose type field equals 'modify' references an input_md path that does not exist as a regular file within plugin_dir. Returns a PluginConfig when none of the failure conditions apply, where: the name attribute equals name (non-empty), the version attribute equals data['version'], the root attribute equals plugin_dir, and the stages attribute is a dict mapping each validated stage name (string) to its corresponding PluginStageConfig.

---

### Actual Behavior

The function returns either None or a PluginConfig object. If it returns a PluginConfig c, then all of the following hold: c.name equals the input argument name (c.name == name); c.version equals data.get('version') (and data.get('version') is truthy); c.root equals plugin_dir; and c.stages is a dictionary where for each key k in c.stages, data.get('stages', {}).get(k) is a dict, the PluginStageConfig object for k passes validation (stage.validated() returns an empty list), and if stage.type == 'modify' and stage.input_md is truthy, then (plugin_dir / stage.input_md).is_file() is True. If it returns None, then at least one of the following is true: 1) data.get('name', '') != name; 2) not data.get('version'); 3) not isinstance(data.get('stages', {}), dict); 4) there exists a key s in data.get('stages', {}) such that not isinstance(data.get('stages', {})[s], dict); 5) there exists a key s and corresponding PluginStageConfig object constructed from its data such that stage.validated() is non-empty; 6) there exists a key s with stage.type == 'modify' and stage.input_md truthy for which (plugin_dir / stage.input_md).is_file() is False. The inputs plugin_dir, name, and data are not modified.

---

## Code Evidence

Line 35: if stage.type == "modify" and stage.input_md:

---

## Trigger Condition

The code only checks the existence of input_md when stage.input_md is truthy. The specification requires rejecting any modify stage whose input_md does not exist as a regular file, regardless of whether input_md is truthy. An empty input_md produces a path that is not a regular file, so the function should return None, but the code returns a PluginConfig.

---

## How to trigger the bug

The code at line 143 in `src/plugin.py` (line 38 in the extracted function file) guards the `input_md` file-existence check with `stage.type == "modify" and stage.input_md`. When `input_md` is an empty string (`""`), the second operand is falsy, so the check is skipped. However, `plugin_dir / ""` resolves to `plugin_dir` itself, which is a directory — not a regular file. Per specification condition (6), the function should return `None`, but instead it returns a `PluginConfig`.

The `validated()` method allows modify stages with an empty `input_md` as long as `output_process` is provided, so the stage passes validation and reaches the guarded file check.

### Inputs

| Parameter | Value |
|-----------|-------|
| `plugin_dir` | A temporary directory (e.g. `/tmp/probe_plugin_xxx`) |
| `name` | The directory's basename (e.g. `probe_plugin_xxx`) |
| `data["name"]` | Same as `name` |
| `data["version"]` | `"1.0.0"` |
| `data["stages"]["mystage"]["type"]` | `"modify"` |
| `data["stages"]["mystage"]["input_md"]` | `""` (empty string — falsy) |
| `data["stages"]["mystage"]["output_process"]` | `"echo hello"` (truthy, so `validated()` passes) |

### Expected (spec-correct) Output

`None` — because `plugin_dir / ""` (the plugin directory itself) is not a regular file, violating specification condition (6).

### Actual (buggy) Output

`PluginConfig(name='probe_plugin_xxx', version='1.0.0', root=PosixPath('/tmp/probe_plugin_xxx'), stages={'mystage': PluginStageConfig(type='modify', replace_cmd=None, input_md='', output_process='echo hello')})`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json
import tempfile
from pathlib import Path
from src.plugin import validate_plugin

with tempfile.TemporaryDirectory() as tmpdir:
    plugin_dir = Path(tmpdir)
    (plugin_dir / "plugin.json").write_text(json.dumps({
        "name": plugin_dir.name,
        "version": "1.0.0",
        "stages": {
            "mystage": {
                "type": "modify",
                "input_md": "",
                "output_process": "echo hello",
            }
        },
    }))
    result = validate_plugin(plugin_dir)
    # actual (buggy) output: PluginConfig(...)
    # expected (correct) output: None
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — actual: PluginConfig(name='probe_plugin_71kf98tp', version='1.0.0', root=PosixPath('/tmp/probe_plugin_71kf98tp'), stages={'mystage': PluginStageConfig(type='modify', replace_cmd=None, input_md='', output_process='echo hello')}) | expected: None
  Bug: empty input_md resolved to /tmp/probe_plugin_71kf98tp (a directory), which is not a regular file, but the function returned a PluginConfig.
```
