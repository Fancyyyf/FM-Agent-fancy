# Bug Report: apply_local_backend_configuration

**Source file:** `fm_agent/extracted_functions/src/configure_llm-py/apply_local_backend_configuration.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Raises ConfigWizardError when paths.toml_path does not identify a readable fm-agent.toml file. Raises ConfigWizardError when the post-update TOML content is not parseable as valid TOML; when this occurs no file has been modified. Returns a tuple (backups, removed_overrides) where: removed_overrides is a tuple of zero or more environment variable names; for every name in removed_overrides, the corresponding legacy LLM override entry that existed in the project .env file before the call is absent from paths.env_path after the call, while all other .env entries are preserved; paths.env_path is modified if and only if removed_overrides is non-empty. backups is a list of (modified_path, backup_path) pairs. Its first element maps paths.toml_path to the path of a pre-modification backup of that file. When removed_overrides is non-empty, an additional element maps paths.env_path to the path of a pre-modification backup of that file. After return, paths.toml_path contains a valid TOML document in which the LLM-section backend field equals backend and every other LLM-section field has the same value it held before the call. No API key or OpenCode provider configuration is written.

---

### Actual Behavior

Post-condition: If `_read_text_if_exists(paths.toml_path)` returns a falsy value (None or empty string), the function raises `ConfigWizardError` with a message indicating that fm-agent.toml was not found, and no files are created or modified. If `toml_text` is truthy but `tomllib.loads(updated_toml)` raises a `tomllib.TOMLDecodeError`, the function raises `ConfigWizardError` with the message 'Generated fm-agent.toml is invalid TOML.' and no files are written; both `paths.toml_path` and `paths.env_path` remain unchanged. Otherwise, the function completes normally and returns `(backups, removed_overrides)`. In this success case:
- `updated_toml` (valid TOML incorporating backend and preserved settings) has been atomically written to `paths.toml_path`.
- If `removed_overrides` is non-empty, `paths.env_path` has been atomically overwritten with `updated_env` (the environment content with those overrides removed); if `removed_overrides` is empty, `paths.env_path` is left in its original state (unchanged or absent if it did not exist before).
- A backup copy of the original content of `paths.toml_path` exists at the path returned by `backup_file(paths.toml_path)`. If `removed_overrides` is non-empty, a private backup of the original `paths.env_path` also exists at `backup_file(paths.env_path, private=True)`.
- The returned list `backups` contains `(paths.toml_path, backup_toml_path)` and, if an env backup was made, `(paths.env_path, backup_env_path)`. The second element `removed_overrides` is the tuple of environment variable names whose legacy overrides were removed.

Formally:
(toml_text → raise ConfigWizardError → toml_path unchanged → env_path unchanged)
(toml_text → ¬valid_TOML(updated_toml) → raise ConfigWizardError → toml_path unchanged → env_path unchanged)
(toml_text → valid_TOML(updated_toml) →
  ( backup_toml = backup_file(paths.toml_path) →
   atomic_write(paths.toml_path, updated_toml) →
   (removed_overrides = () → env_path unchanged) ∨
   (removed_overrides ≠ () → backup_env = backup_file(paths.env_path, private=True) → atomic_write(paths.env_path, updated_env)) →
   return (backups, removed_overrides) ))

---

## Code Evidence

Line 5: toml_text = _read_text_if_exists(paths.toml_path)

---

## Trigger Condition

When the file is not readable, _read_text_if_exists may raise an exception (such as PermissionError) that is not caught. The code does not raise ConfigWizardError, violating the specification's requirement that ConfigWizardError be raised when the toml file is not readable.

---

## How to trigger the bug

When `paths.toml_path` points to an `fm-agent.toml` file that exists on disk but has no read permissions (e.g., mode `000`), `_read_text_if_exists` calls `path.read_text()` which raises a raw `PermissionError`. The calling function `apply_local_backend_configuration` does not catch this exception, so it propagates up as `PermissionError` instead of the `ConfigWizardError` required by the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `backend` | `"opencode"` |
| `paths.toml_path` | Path to an `fm-agent.toml` file that exists but has no read permission (`chmod 000`) |
| `paths.env_path` | Path to a writable `.env` file (can be empty) |
| `paths.project_root` | Any valid directory path |
| `paths.opencode_config_path` | Any valid path (not accessed for local backend configuration) |

### Expected (spec-correct) Output

`ConfigWizardError` is raised, indicating that `fm-agent.toml` is not readable.

### Actual (buggy) Output

`PermissionError: [Errno 13] Permission denied` is raised — an uncaught exception, not `ConfigWizardError`.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from pathlib import Path
from src.configure_llm import apply_local_backend_configuration, WizardPaths

tmp = Path(tempfile.mkdtemp())
project_root = tmp / "project"
project_root.mkdir()
toml_path = project_root / "fm-agent.toml"
toml_path.write_text('[llm]\nbackend = "opencode"\nname = "test-model"\n')
toml_path.chmod(0o000)

env_path = project_root / ".env"
env_path.write_text("")

paths = WizardPaths(
    project_root=project_root,
    env_path=env_path,
    toml_path=toml_path,
    opencode_config_path=tmp / "opencode.json",
)

apply_local_backend_configuration("opencode", paths)
# actual (buggy) output: PermissionError: [Errno 13] Permission denied
# expected (correct) output: ConfigWizardError is raised
```

---

## Probe Script

```python
"""Probe script for bug src--configure_llm-py--apply_local_backend_configuration.

The specification requires that apply_local_backend_configuration raises
ConfigWizardError when paths.toml_path does not identify a readable
fm-agent.toml file. When the file exists but lacks read permissions,
_read_text_if_exists raises PermissionError, which is not caught by
the calling code — violating the specification.
"""
import sys
import os
import stat
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os.chdir(str(_REPO_ROOT))

try:
    from src.configure_llm import (
        apply_local_backend_configuration,
        WizardPaths,
        ConfigWizardError,
    )
except Exception as exc:
    print(f"ERROR: could not import src.configure_llm: {exc}")
    sys.exit(1)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project_root = tmp / "project"
        project_root.mkdir()

        # Create fm-agent.toml with valid TOML but remove read permission
        toml_path = project_root / "fm-agent.toml"
        toml_path.write_text("[llm]\nbackend = \"opencode\"\nname = \"test-model\"\n", encoding="utf-8")
        # Make unreadable (even by owner)
        toml_path.chmod(0o000)

        # Create minimal .env file
        env_path = project_root / ".env"
        env_path.write_text("", encoding="utf-8")

        # Arbitrary opencode config path (should not be accessed for local backend)
        opencode_config_path = tmp / "opencode.json"

        paths = WizardPaths(
            project_root=project_root,
            env_path=env_path,
            toml_path=toml_path,
            opencode_config_path=opencode_config_path,
        )

        actual_str = ""
        raises_config_wizard_error = False
        raises_permission_error = False
        exc_type_name = ""

        try:
            result = apply_local_backend_configuration("opencode", paths)
            actual_str = "returned normally (did not raise)"
        except ConfigWizardError as exc:
            raises_config_wizard_error = True
            actual_str = f"ConfigWizardError: {exc}"
        except PermissionError as exc:
            raises_permission_error = True
            exc_type_name = type(exc).__name__
            actual_str = f"PermissionError: {exc}"
        except Exception as exc:
            exc_type_name = type(exc).__name__
            actual_str = f"{type(exc).__name__}: {exc}"
        finally:
            # Restore permissions so the tmpdir cleanup can succeed
            try:
                toml_path.chmod(0o644)
            except Exception:
                pass

        if raises_config_wizard_error:
            print(
                f"NOT CONFIRMED — function raised ConfigWizardError as spec requires: "
                f"{actual_str}"
            )
        elif raises_permission_error:
            print(
                f"CONFIRMED — spec requires ConfigWizardError for an unreadable toml file, "
                f"but code raised PermissionError (uncaught): {actual_str}"
            )
        else:
            print(
                f"CONFIRMED — spec requires ConfigWizardError for an unreadable toml file, "
                f"but actual: {actual_str}"
            )


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — spec requires ConfigWizardError for an unreadable toml file, but code raised PermissionError (uncaught): PermissionError: [Errno 13] Permission denied: '/tmp/tmpbiyujys_/project/fm-agent.toml'
```
