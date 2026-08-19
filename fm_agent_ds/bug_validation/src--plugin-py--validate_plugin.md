# Bug Report: validate_plugin

**Source file:** `src/plugin-py/validate_plugin.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns None if plugin_dir does not contain a file named plugin.json, or if that file cannot be read as a JSON object whose parsed dict passes PluginConfig validation (non-empty name attribute, valid version string, and for every stage declared in the stages dict the stage configuration is valid: type field is one of 'pass', 'replace', or 'modify'; if type is 'replace' then replace_cmd is a non-empty string; if type is 'modify' then input_md is a non-empty string). When validation fails for any reason, a message describing the failure is printed to stdout and None is returned. Otherwise returns a PluginConfig object whose name attribute is the directory name of plugin_dir (non-empty) and whose root is plugin_dir.

---

### Actual Behavior

The function completes without raising any unhandled exception. The return value `r` is either `None` or an instance of `PluginConfig`. If `r` is a `PluginConfig`, its `name` attribute is a non-empty string and all validation rules checked by `_validate_plugin_json_content` hold. If `r` is `None`, an appropriate error message has been printed to stdout. The exact outcome is determined by the following logical relation between the pre-state and post-state:

Let `pj = plugin_dir / "plugin.json"`, `pc = plugin_dir / "plugin.config.json"`, `name = plugin_dir.name`.

Post-condition 
  (  pj.is_file()    Printed("Invalid plugin '" + name + "': ...")    r = None )
  
  ( pj.is_file()  
    ( ( exc  {OSError, json.JSONDecodeError}  on opening/parsing pj)
          Printed("Invalid plugin '" + name + "': failed to parse plugin.json  " + str(exc))    r = None )
    
    ( data = parse_success(pj)  
        (  isinstance(data, dict)    Printed("Invalid plugin '" + name + "': plugin.json must be a JSON object")    r = None )
        
        ( isinstance(data, dict)    r = _validate_plugin_json_content(plugin_dir, name, data) )
    )
  )

where `parse_success(pj)` denotes the dictionary obtained when `pj` is successfully opened and parsed without raising `OSError`/`JSONDecodeError`. The `Printed(...)` predicates indicate a one-to-one correspondence between a specific condition and an error message containing the quoted substring. If `r` is a `PluginConfig`, then `r.name` is nonempty and satisfies the `PluginConfig` schema (valid version, stages, etc.).

---

## Code Evidence

Line 31: return _validate_plugin_json_content(plugin_dir, name, data)

---

## Trigger Condition

The specification requires that the returned PluginConfig's name attribute equals the directory name of plugin_dir. However, the code's validation (via _validate_plugin_json_content) only ensures the name is non-empty but does not enforce that it matches the directory name. Consequently, a valid plugin.json with a non-empty name different from the directory's name passes validation and yields a PluginConfig with a name that violates the specification.

---

## How to trigger the bug

The trigger condition claims that `_validate_plugin_json_content` does not enforce the name matching the directory name, allowing a PluginConfig with a mismatched name to be returned. However, examination of the actual source code (`src/plugin.py`, lines 110-116) reveals that `_validate_plugin_json_content` explicitly checks `if plugin_name != name:` and returns `None` when they differ. The probe confirms this: creating a plugin directory named "my_plugin" with a `plugin.json` containing `"name": "different_name"` causes the code to print a mismatch error and return `None`, which is the correct spec-compliant behavior. The bug is a false positive in the logic verification step — the code enforces the name matching constraint that the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `plugin_dir` | `Path(tmpdir) / "my_plugin"` (a directory named "my_plugin") |
| `plugin.json` content | `{"name": "different_name", "version": "1.0.0", "stages": {}}` |

### Expected (spec-correct) Output

`None` (plugin name "different_name" does not match directory name "my_plugin")

### Actual (buggy) Output

`None` (code correctly rejects the name mismatch)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, json
from pathlib import Path
from src.plugin import validate_plugin

with tempfile.TemporaryDirectory() as tmpdir:
    plugin_dir = Path(tmpdir) / "my_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps({
        "name": "different_name",
        "version": "1.0.0",
        "stages": {}
    }))
    result = validate_plugin(plugin_dir)
    print(result)  # None — correct, name mismatch rejected
# actual (buggy) output: None
# expected (correct) output: None
```

---

## Probe Script

```python
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
```

### Probe Output

```
Invalid plugin 'my_plugin': plugin name mismatch (expected 'my_plugin', got 'different_name')
NOT CONFIRMED — validate_plugin returned None for plugin.json with name 'different_name' in directory 'my_plugin' (code correctly rejects the name mismatch)
```
