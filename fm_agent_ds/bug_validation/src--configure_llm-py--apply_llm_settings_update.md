# Bug Report: apply_llm_settings_update

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/configure_llm-py/apply_llm_settings_update.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

The file at toml_path is overwritten such that every key in updates has its value written to the corresponding field path in the [llm] section, while all other sections, fields, and the overall TOML structure outside the updated fields are preserved unchanged. Before the write, the original file content is copied to a timestamp-suffixed backup file adjacent to toml_path. Returns the backup file Path when a backup was created; returns None when no backup was created. Raises ConfigWizardError when toml_path does not refer to an existing file or when the updated TOML content is not parseable as valid TOML by the standard library parser.

---

### Actual Behavior

After the function execution, one of the following holds: (1) The function raised a `ConfigWizardError` (with message `"fm-agent.toml not found at {toml_path}; refusing to guess a new project config."` or `"Generated fm-agent.toml is invalid TOML."`). In this case, the file at `toml_path` remains unchanged and no backup file is created. (2) The function returned a value `r` normally. Then the file at `toml_path` has been atomically replaced with the TOML text obtained by applying the given `updates` to the original file's `[llm]` section, preserving all other parts of the document. If `r` is a `Path` object, a backup copy of the original file content exists at the path `r` (adjacent to `toml_path` with a timestamp-suffixed name); the content at `r` equals the original file content before the call. If `r` is `None`, no backup copy was created.

Formally, let `orig` be the content of `toml_path` at function entry, and `updated = update_llm_settings_toml_text(orig, updates)`. Let `F_before` and `F_after` be the filesystem state mapping paths to contents immediately before and after the call.

- If the function raises a `ConfigWizardError`:
  `F_after = F_before` (no files changed or created).

- If the function returns `r` normally:
  `F_after(toml_path) = updated` 
  `(r = None  p adjacent to toml_path, F_after(p) = F_before(p)  no new timestamp-suffixed backup file exists)` 
  `(isinstance(r, Path)  r is a path adjacent to toml_path  r did not exist in F_before  F_after(r) = orig  all other files unchanged)`.

---

## Code Evidence

Line 6: if not toml_text:

---

## Trigger Condition

The code raises a ConfigWizardError for an existing empty file, claiming the file is not found, which violates the specification. The specification only allows raising ConfigWizardError when toml_path does not refer to an existing file or when the updated TOML content is unparseable. An empty file exists, so the code should not raise a 'file not found' error; it should instead proceed to generate updated TOML.

---

## How to trigger the bug

`apply_llm_settings_update` calls `_read_text_if_exists(toml_path)` which returns `""` for an existing but empty file. The guard `if not toml_text:` treats the empty string as falsy, raising `ConfigWizardError` with a misleading "file not found" message — even though the file does exist and empty TOML is valid (`tomllib.loads("")` returns `{}`).

### Inputs

| Parameter | Value |
|-----------|-------|
| `updates` | `{"backend": "opencode"}` |
| `toml_path` | Path to an existing empty `fm-agent.toml` file |

### Expected (spec-correct) Output

`Path` — the function should process the empty TOML, generate a `[llm]` section with `backend = "opencode"`, create a backup, atomically write the new content, and return the backup path.

### Actual (buggy) Output

`ConfigWizardError` raised with message: `fm-agent.toml not found at {toml_path}; refusing to guess a new project config.`

### How to Reproduce

1. Navigate to the repo root.
2. Create an empty `fm-agent.toml` in a temporary directory.
3. Run the following snippet:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from src.configure_llm import apply_llm_settings_update, ConfigWizardError

with TemporaryDirectory() as tmpdir:
    toml_path = Path(tmpdir) / "fm-agent.toml"
    toml_path.write_text("")  # exists but empty
    apply_llm_settings_update({"backend": "opencode"}, toml_path)
    # actual (buggy) output: ConfigWizardError raised
    # expected (correct) output: proceeds normally, returns backup Path
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED -- actual: ConfigWizardError raised: fm-agent.toml not found at /tmp/tmp5zk0ey_k/fm-agent.toml; refusing to guess a new project config. | expected: function should have proceeded normally for an existing empty file
```
