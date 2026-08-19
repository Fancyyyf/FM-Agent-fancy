# Bug Report: run_wizard

**Source file:** `src/configure_llm-py/run_wizard.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns 0 when the user has completed the interactive configuration flow and all resulting configuration has been persisted to fm-agent.toml, the project .env file, and the OpenCode provider configuration file. Returns non-zero when the user aborts the flow or when configuration values provided by the user fail validation. When the selected backend is not 'opencode', no API key or OpenCode provider configuration is written and only the backend-specific configuration is applied; the return value reflects whether that backend-specific configuration succeeded. When the selected backend is 'opencode': the API key is written to .env and to a provider-specific key file at the location determined by the OpenCode configuration; non-secret configuration values (provider name, base URL, model ID, API style) are written to fm-agent.toml; the OpenCode provider configuration is updated to reference the chosen provider and backend. Before applying changes, a summary of the planned modifications is printed to stdout, and warnings are emitted for any process environment variables whose precedence would override the configuration being written. When the user declines the confirmation prompt, no file modifications occur and the return value is non-zero. Raises ConfigWizardError when configuration cannot be completed due to an unrecoverable error such as a missing required file or an unwritable configuration path.

---

### Actual Behavior

After execution of run_wizard(project_root), the return value r is an integer. Let b = _prompt_backend() be the user-selected backend. If b ≠ 'opencode', then: (if project_root/fm-agent.toml is writable, then r = 0, and the file is modified so that the LLM backend is set to b (with no other configuration changes), and a backup copy exists in the same directory; otherwise, r ≠ 0 and no files are modified.) If b = 'opencode', let (config, validate) = prompt_for_config() and let paths = default_paths(project_root). If _prompt_yes_no('Continue?') returns False, then r = 1 and no files are modified. Otherwise, apply_configuration(config, paths, validate) is called, which modifies the fm-agent.toml, .env, and OpenCode config files at paths.toml_path, paths.env_path, paths.opencode_config_path respectively: fm-agent.toml's [llm] section is updated with provider=config.provider_id, name=config.provider_name, base_url=config.base_url, api_style=config.api_style, other sections unchanged; .env gains/replaces the entry LLM_API_KEY=config.api_key; OpenCode config references the chosen provider and API style; backups of each modified file are created. If validate is true, the written TOML and OpenCode config are syntactically valid. r = 0. Warnings about environment overrides are printed but do not affect r.

Formal logic:
r ∈ ℤ.
 b = _prompt_backend().
if b ≠ 'opencode':
    ( writable(project_root / 'fm-agent.toml') ∧ r = 0 ∧ updated_llm_backend(project_root / 'fm-agent.toml', b) ∧ backup_file )
   ∨ ( ¬writable(project_root / 'fm-agent.toml') ∧ r ≠ 0 ∧ unchanged(project_root / 'fm-agent.toml') ∧ unchanged(env) ∧ unchanged(opencode_config) )
else:  # b = 'opencode'
     (config, validate) = prompt_for_config()
     paths = default_paths(project_root)
     continue = _prompt_yes_no('Continue?')
    if ¬continue: r = 1 ∧ unchanged_all(project_root / 'fm-agent.toml', paths.env_path, paths.opencode_config_path)
    else:
         backups = apply_configuratio... (continued)

---

## Code Evidence

Line 10: return run_local_backend_configuration(project_root, backend)

---

## Trigger Condition

Specification requires that unrecoverable errors such as unwritable configuration paths raise ConfigWizardError. The code instead returns a non-zero value from run_local_backend_configuration, which does not raise the required exception.

---

## How to trigger the bug

When `run_wizard()` is called and the user selects a non-opencode backend (e.g., "auto"), the function delegates to `run_local_backend_configuration()`. If the `fm-agent.toml` file exists but its parent directory is not writable, `apply_local_backend_configuration()` calls `backup_file()` which attempts to create a backup file in the same directory. The `os.open()` call inside `backup_file()` raises `PermissionError` because the directory is read-only. This `PermissionError` propagates uncaught through `run_local_backend_configuration()` → `run_wizard()` → caller, instead of being wrapped in `ConfigWizardError` as the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `project_root` | A temporary directory containing a valid `fm-agent.toml`, made read-only |
| `backend` (mocked) | `"auto"` (a non-opencode backend) |
| `_prompt_yes_no` (mocked) | `True` (confirm the write) |

### Expected (spec-correct) Output

`ConfigWizardError` raised — the specification states: "Raises ConfigWizardError when configuration cannot be completed due to an unrecoverable error such as an unwritable configuration path."

### Actual (buggy) Output

`PermissionError: [Errno 13] Permission denied` raised — the code raises a raw OS-level exception instead of the specification-required `ConfigWizardError`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from src.configure_llm import run_wizard

with tempfile.TemporaryDirectory() as tmpdir:
    project_root = Path(tmpdir)
    (project_root / "fm-agent.toml").write_text('[llm]\nbackend = "opencode"\n')
    project_root.chmod(0o555)  # make directory read-only
    with patch("src.configure_llm._prompt_backend", return_value="auto"), \
         patch("src.configure_llm._prompt_yes_no", return_value=True):
        run_wizard(project_root)  # raises PermissionError, not ConfigWizardError
# actual (buggy) output: PermissionError: [Errno 13] Permission denied
# expected (correct) output: ConfigWizardError raised
```

---

## Probe Script

```python
"""Probe script for bug src--configure_llm-py--run_wizard.

The specification requires that run_wizard() raises ConfigWizardError when
configuration cannot be completed due to an unrecoverable error such as an
unwritable configuration path. The code instead returns a non-zero value from
run_local_backend_configuration, which does not raise the required exception.

This probe tests the non-opencode backend path: select a local CLI backend,
confirm the operation, and verify that an unwritable fm-agent.toml file
causes ConfigWizardError to be raised.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add repo root to sys.path so the src package is importable.
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    from src.configure_llm import run_wizard, ConfigWizardError
except Exception as exc:
    print(f'ERROR: could not import src.configure_llm: {exc}')
    sys.exit(1)

_attempts_remaining = 3
_confirmed = False
_last_stdout = ""

for attempt in range(1, _attempts_remaining + 1):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            # Create a minimal valid fm-agent.toml so the read succeeds.
            toml_path = project_root / "fm-agent.toml"
            toml_path.write_text('[llm]\nbackend = "opencode"\n', encoding="utf-8")
            toml_path.chmod(0o644)

            # Make the project root read-only (r-xr-xr-x) so that
            # backup_file cannot create a new file and atomic_write
            # cannot create its temp file in the same directory.
            project_root.chmod(0o555)

            # Mock the interactive prompts:
            #   _prompt_backend  → return "auto"  (non-opencode backend)
            #   _prompt_yes_no   → return True    (confirm the write)
            with patch(
                "src.configure_llm._prompt_backend", return_value="auto"
            ), patch(
                "src.configure_llm._prompt_yes_no", return_value=True
            ):
                # The spec requires ConfigWizardError here, but the code
                # throws PermissionError (or similar) instead.
                result = run_wizard(project_root)
                # If we reach this line, no exception was raised at all.
                _last_stdout = (
                    f"CONFIRMED — run_wizard() returned {result!r} "
                    f"instead of raising ConfigWizardError "
                    f"(unwritable configuration path)"
                )
                print(_last_stdout)
                _confirmed = True
                break

    except ConfigWizardError:
        # The code actually raised ConfigWizardError — the bug is NOT present.
        _last_stdout = (
            "NOT CONFIRMED — ConfigWizardError was raised as expected, "
            "the code matches the specification"
        )
        print(_last_stdout)
        _confirmed = False
        break

    except PermissionError as exc:
        # PermissionError: backup_file or atomic_write could not write to the
        # read-only directory. This is the bug: the code raises the wrong
        # exception type instead of ConfigWizardError.
        _last_stdout = (
            f"CONFIRMED — run_wizard() raised {type(exc).__name__} "
            f"instead of ConfigWizardError for an unwritable path: {exc}"
        )
        print(_last_stdout)
        _confirmed = True
        break

    except Exception as exc:
        # Some other unexpected exception was raised — still a bug because
        # it's not ConfigWizardError.
        _last_stdout = (
            f"CONFIRMED — run_wizard() raised {type(exc).__name__} "
            f"instead of ConfigWizardError: {exc}"
        )
        print(_last_stdout)
        _confirmed = True
        break

    finally:
        # Restore writability so the tempdir cleanup can succeed.
        try:
            project_root.chmod(0o755)
        except Exception:
            pass

if not _confirmed:
    # Last attempt didn't confirm — report final classification.
    if _last_stdout:
        print(_last_stdout)
    else:
        print("NOT CONFIRMED — all attempts exhausted, could not trigger the bug")
```

### Probe Output

```
FM-Agent LLM configuration

Local CLI backends use their own authentication; no API key or OpenCode provider configuration is required.
FM-Agent local CLI backend configuration

Backend: auto

The following files will be updated:
  - /tmp/tmpyhlwtr2u/fm-agent.toml

No legacy LLM overrides were found in the project .env file.

No API key or OpenCode provider configuration will be changed.

Warning: these shell environment variables override the saved LLM settings:
  LLM_API_KEY, LLM_API_BASE_URL, LLM_MODEL, FM_AGENT_MODEL_BACKEND, LLM_EFFORT, OPENCODE_MODEL_PROVIDER
The wizard cannot change the shell that launched it. Before starting FM-Agent
in this shell, unset them to use the saved configuration:
  unset LLM_API_KEY LLM_API_BASE_URL LLM_MODEL FM_AGENT_MODEL_BACKEND LLM_EFFORT OPENCODE_MODEL_PROVIDER

CONFIRMED — run_wizard() raised PermissionError instead of ConfigWizardError for an unwritable path: [Errno 13] Permission denied: '/tmp/tmpyhlwtr2u/fm-agent.toml.bak.20260727-235010'
```
