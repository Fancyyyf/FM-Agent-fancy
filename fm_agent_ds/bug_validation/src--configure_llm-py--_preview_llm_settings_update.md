# Bug Report: _preview_llm_settings_update

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/configure_llm-py/_preview_llm_settings_update.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a human-readable multi-line string. For each key in updates, the string contains a human-readable label identifying the field and both the field's current value as read from the TOML file at toml_path and the new value from updates. The string also lists toml_path as the sole file that will be modified under a section header to that effect.

---

### Actual Behavior

The function returns a string formatted as follows:
- First line: 'FM-Agent LLM settings update'
- Second line: empty
- Then, for each (key, value) pair in updates (in the order of updates.items()), a line of the form '{label}: {quoted_value}' where label is derived from key using the fixed mapping: 'name'->'Model ID', 'provider'->'Provider ID', 'base_url'->'Base URL', 'backend'->'Backend', 'effort'->'Reasoning effort', 'api_style'->'API protocol', and quoted_value is the repr of value (enclosed in single quotes and escaped).
- Then an empty line
- Then the line 'Only the following file will be updated:'
- Then the line '  - {toml_path}' (with the path as a string)
- Then an empty line
- Then the line 'This command does not change .env or the standalone OpenCode config.'
The returned string contains no other characters. No exceptions are raised. The function has no side effects: the input arguments are not mutated, the filesystem is unchanged, and no global or external state is modified.

---

## Code Evidence

Line 10: settings = [f"{labels[key]}: {value!r}" for key, value in updates.items()] - this line only includes the new values from updates, not the current values from the TOML file. The function body (Lines 1-22) never reads the TOML file at toml_path.

---

## Trigger Condition

The specification requires the output to contain both the current value from the TOML file and the new value from updates for each updated field. The code implementation only outputs the new values and never reads the TOML file, so it cannot include current values. This violates the specification for any valid input where the TOML file exists and contains values.

---

## How to trigger the bug

The function `_preview_llm_settings_update` builds a preview string from `updates` dictionary values only, never consulting the TOML file at `toml_path`. When the TOML file contains existing values for the same keys being updated, those current values are absent from the output — the spec requires them to appear alongside the new values.

### Inputs

| Parameter | Value |
|-----------|-------|
| `updates` | `{"name": "new-model", "provider": "new-provider"}` |
| `toml_path` | Temp file containing `[llm]\nname = "original-model"\nprovider = "original-provider"\n` |

### Expected (spec-correct) Output

A string that includes both the current values from the TOML file (`original-model`, `original-provider`) and the new values from updates (`new-model`, `new-provider`).

### Actual (buggy) Output

```
FM-Agent LLM settings update

Model ID: 'new-model'
Provider ID: 'new-provider'

Only the following file will be updated:
  - /tmp/tmp_ocdqo6h/fm-agent.toml

This command does not change .env or the standalone OpenCode config.
```

The output only shows the new values. The current TOML values (`original-model`, `original-provider`) are completely absent.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from pathlib import Path
from src.configure_llm import _preview_llm_settings_update

with tempfile.TemporaryDirectory() as tmpdir:
    toml_path = Path(tmpdir) / "fm-agent.toml"
    toml_path.write_text('[llm]\nname = "original-model"\nprovider = "original-provider"\n')
    updates = {"name": "new-model", "provider": "new-provider"}
    print(_preview_llm_settings_update(updates, toml_path))
// actual (buggy) output: Only shows new values ('new-model', 'new-provider'); current TOML values ('original-model', 'original-provider') are missing
// expected (correct) output: Would also include the current TOML values alongside the new values
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — output missing current TOML values.
  Expected to contain: original-model, original-provider
  Output:
FM-Agent LLM settings update

Model ID: 'new-model'
Provider ID: 'new-provider'

Only the following file will be updated:
  - /tmp/tmp_ocdqo6h/fm-agent.toml

This command does not change .env or the standalone OpenCode config.
```
