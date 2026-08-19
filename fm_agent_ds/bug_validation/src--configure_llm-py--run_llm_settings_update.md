# Bug Report: run_llm_settings_update

**Source file:** `src/configure_llm.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns 0 when every key in updates has been written to the corresponding TOML field with the provided value and the pre-update TOML content has been backed up to a file adjacent to the original. Before the write, the planned field modifications are printed to stdout, and warnings are emitted for any .env entries or process environment variables whose precedence would override the TOML values being changed. When assume_yes is false and the user declines the confirmation prompt, no file modifications occur and the return value is non-zero. When the TOML file cannot be written or any key path in updates does not resolve to a writable field in the LLM section, the return value is non-zero and no partial updates are persisted.

---

### Actual Behavior

After execution of run_llm_settings_update, the program state satisfies one of the following exhaustive cases. (1) Early termination: assume_yes is False, the user responds negatively to the confirmation prompt; the function prints the preview string from _preview_llm_settings_update(updates, toml_path), any warnings from warn_dotenv_overrides_for_updates and warn_live_llm_environment_overrides, an extra blank line if either warning function flagged active overrides, then prints 'Aborted.' and returns 1. No changes are made to the TOML file. (2) Successful update: either assume_yes is True or the user responds affirmatively to the prompt; the same preview and warnings are printed, followed by 'Updated {toml_path}'. apply_llm_settings_update(updates, toml_path) is invoked, which writes the new LLM settings into the TOML file while preserving all other sections and fields, and may create a timestamped backup file adjacent to toml_path; if a backup was created, the line 'Backed up {toml_path} -> {backup_path}' is printed. The function returns 0. (3) Unhandled exception: if any step after printing the preview and warnings raises an exception (e.g., apply_llm_settings_update fails due to a non-writable file or TOML serialization error), the exception propagates without printing 'Updated ...' or 'Backed up ...'; the state of the TOML file may be unchanged or partially modified, and no return value is produced.

---

## Code Evidence

Line 18: backup = apply_llm_settings_update(updates, toml_path)  no validation of key paths or error handling; the function returns 0 on success (Line 22) instead of returning non-zero for invalid keys as required.

---

## Trigger Condition

Specification B states: 'When ... any key path in updates does not resolve to a writable field in the LLM section, the return value is non-zero and no partial updates are persisted.' The code unconditionally passes updates to apply_llm_settings_update without checking validity, and it returns 0 when that call succeeds (or raises an unhandled exception when it fails). Thus, for an invalid key the code either returns 0 (violating the nonzero requirement) or allows an exception to propagate (failing to return any integer).

---

## How to trigger the bug

The function `run_llm_settings_update` calls `_preview_llm_settings_update(updates, toml_path)` on line 1067, which iterates over `updates.items()` and accesses `labels[key]` (line 1024) without first validating that each key exists in the labels dictionary. When a key not in `_LLM_TOML_KEYS` is passed — e.g., `"invalid_key"` — a `KeyError` is raised before any validation or error handling can occur. The specification requires the function to return a non-zero integer in this case, but instead an unhandled exception propagates.

### Inputs

| Parameter | Value |
|-----------|-------|
| `project_root` | A temporary directory containing a minimal `fm-agent.toml` with `[llm]\nname = "test-model"\n` |
| `updates` | `{"invalid_key": "value"}` |
| `assume_yes` | `True` |

### Expected (spec-correct) Output

`non-zero integer (≠ 0)` — the function should detect that `"invalid_key"` is not a writable LLM setting field and return a non-zero exit code without modifying any files.

### Actual (buggy) Output

`KeyError: 'invalid_key'` — an unhandled exception propagates because `_preview_llm_settings_update` attempts to look up `labels["invalid_key"]` which does not exist.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from pathlib import Path
from src.configure_llm import run_llm_settings_update

tmpdir = Path(tempfile.mkdtemp())
(tmpdir / "fm-agent.toml").write_text('[llm]\nname = "test-model"\n')
(tmpdir / ".env").write_text("")

run_llm_settings_update(tmpdir, {"invalid_key": "value"}, assume_yes=True)
# actual (buggy) output: KeyError: 'invalid_key'
# expected (correct) output: non-zero integer (e.g., 2)
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — actual: Exception: KeyError: 'invalid_key' | expected: non-zero integer (≠ 0) — function should not raise
```
