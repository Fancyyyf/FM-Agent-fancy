# Bug Report: run_local_backend_configuration

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/src/configure_llm.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns 0 when the fm-agent.toml file has been updated to set the LLM backend to the provided backend value, with a backup of the original file created. Returns non-zero when the fm-agent.toml file has not been modified. No API key, .env modification, or OpenCode provider configuration is performed.

---

### Actual Behavior

Natural language: After the execution of `run_local_backend_configuration`, exactly one of the following outcomes occurs, depending on runtime events:

1. Normal return with 0: The user confirmed the prompt. The standard output contains the preview of the local backend configuration (generated from `_preview_local_backend_configuration`), any warnings about live LLM environment overrides, the prompt `Continue?` followed by the user's affirmative response, and then the messages: `Updated {paths.toml_path}`; if legacy LLM overrides were present, `Removed legacy LLM overrides from {paths.env_path}`; and for every pair `(path, backup)` returned by `apply_local_backend_configuration` where `backup is not None`, `Backed up {path} -> {backup}`. The file system has been modified: `paths.toml_path` now contains the local backend configuration for `backend` (as produced by `local_backend_toml_updates`); `paths.env_path` (if it existed and contained legacy LLM overrides) no longer contains those overrides; and for each changed file, a backup file exists at the reported backup path with the original contents. The function returns 0.

2. Normal return with 1: The user declined the prompt. The standard output contains the same preview, warnings, and the prompt, followed by `Aborted.`. No files were modified on disk. The function returns 1.

3. Exceptional termination: An exception (e.g., IOError, OSError, or any exception from the called functions) is raised. The standard output includes all output generated before the exception (which may include the preview, warnings, and possibly partial apply messages). The file system may be in an inconsistent state: some backups may have been created and some file updates written, but not all intended changes are guaranteed. The function does not return to the caller; the exception propagates up the stack.

---

## Code Evidence

Line 22: backups, removed_overrides = apply_local_backend_configuration(backend, paths)

---

## Trigger Condition

The specification explicitly requires that no .env modification is performed. The code, however, modifies the .env file by removing legacy LLM overrides when they are present, as performed by apply_local_backend_configuration called on line 22.

---

## How to trigger the bug

When `run_local_backend_configuration` is called with a local CLI backend (e.g., "codex-cli", "claude-cli", "auto") and the project's `.env` file contains legacy LLM override keys (`LLM_MODEL`, `LLM_EFFORT`, `LLM_API_BASE_URL`, etc.), the function modifies `.env` by stripping those overrides — contrary to the specification which states no .env modification is performed.

### Inputs

| Parameter | Value |
|-----------|-------|
| `project_root` | Path to project directory with `fm-agent.toml` and `.env` containing legacy LLM overrides |
| `backend` | `"codex-cli"` (or any non-openode backend) |

### Expected (spec-correct) Output

`.env` file unchanged. Only `fm-agent.toml` is updated.

### Actual (buggy) Output

`.env` file is modified — legacy LLM override keys (`LLM_MODEL`, `LLM_EFFORT`, `LLM_API_BASE_URL`) are removed. The standard output contains: `"Removed legacy LLM overrides from {paths.env_path}"`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from pathlib import Path
from unittest.mock import patch
from src.configure_llm import run_local_backend_configuration

# Ensure .env has legacy LLM overrides (e.g. LLM_MODEL=foo)
with patch('src.configure_llm._prompt_yes_no', return_value=True):
    run_local_backend_configuration(Path('.'), 'codex-cli')

# .env has been modified — legacy LLM overrides are now removed
# actual (buggy) output: "Removed legacy LLM overrides from .env"
# expected (correct) output: .env should not be modified at all
```

---

## Probe Script

```python
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch


def main() -> int:
    try:
        from src.configure_llm import run_local_backend_configuration
    except Exception as e:
        print(f'ERROR: {e}')
        return 1

    tmp_root = Path(tempfile.mkdtemp(prefix='bug_probe_'))
    env_path = tmp_root / '.env'
    toml_path = tmp_root / 'fm-agent.toml'

    try:
        # Minimal valid fm-agent.toml with an [llm] section
        toml_path.write_text('[llm]\nbackend = "opencode"\n')

        # .env with legacy LLM overrides to trigger the bug
        env_content = (
            'LLM_MODEL=old-model\n'
            'LLM_EFFORT=high\n'
            '# keep this comment\n'
            'LLM_API_BASE_URL=https://example.com/api\n'
        )
        env_path.write_text(env_content)

        # Ensure _fm_agent_config_path picks up the temp toml
        os.environ['FM_AGENT_CONFIG'] = str(toml_path)

        # Mock interactive prompt to auto-confirm
        with patch('src.configure_llm._prompt_yes_no', return_value=True):
            result = run_local_backend_configuration(tmp_root, 'codex-cli')

        # Check whether .env was modified
        env_after = env_path.read_text()

        legacy_keys = (
            'LLM_MODEL',
            'LLM_EFFORT',
            'LLM_API_BASE_URL',
            'FM_AGENT_MODEL_BACKEND',
            'OPENCODE_MODEL_PROVIDER',
            'LLM_API_STYLE',
        )
        has_legacy = any(key + '=' in env_after for key in legacy_keys)
        env_changed = env_after != env_content

        if env_changed and not has_legacy:
            print(
                'CONFIRMED — .env was modified (legacy LLM overrides removed) '
                f'result={result!r} after={env_after!r}'
            )
        elif env_changed:
            print(
                f'CONFIRMED — .env was modified (changed in some way) '
                f'result={result!r} after={env_after!r}'
            )
        else:
            print(
                f'NOT CONFIRMED — .env was not modified '
                f'result={result!r} after={env_after!r}'
            )

        return 0

    except Exception as e:
        print(f'ERROR: {e}')
        return 1

    finally:
        # Cleanup temp directory
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
```

### Probe Output

```
FM-Agent local CLI backend configuration

Backend: codex-cli

The following files will be updated:
  - /tmp/bug_probe_ubnz7ezp/fm-agent.toml
  - /tmp/bug_probe_ubnz7ezp/.env

The following legacy dotenv overrides will be removed so they do not
shadow the selected backend: LLM_MODEL, LLM_EFFORT, LLM_API_BASE_URL

The local CLI model settings retained from .env will be written to TOML:
  - name: 'old-model'
  - effort: 'high'

No API key or OpenCode provider configuration will be changed.

Warning: these shell environment variables override the saved LLM settings:
  LLM_API_KEY, LLM_API_BASE_URL, LLM_MODEL, FM_AGENT_MODEL_BACKEND, LLM_EFFORT, OPENCODE_MODEL_PROVIDER
The wizard cannot change the shell that launched it. Before starting FM-Agent
in this shell, unset them to use the saved configuration:
  unset LLM_API_KEY LLM_API_BASE_URL LLM_MODEL FM_AGENT_MODEL_BACKEND LLM_EFFORT OPENCODE_MODEL_PROVIDER

Updated /tmp/bug_probe_ubnz7ezp/fm-agent.toml
Removed legacy LLM overrides from /tmp/bug_probe_ubnz7ezp/.env
Backed up /tmp/bug_probe_ubnz7ezp/fm-agent.toml -> /tmp/bug_probe_ubnz7ezp/fm-agent.toml.bak.20260727-235535
Backed up /tmp/bug_probe_ubnz7ezp/.env -> /tmp/fm-agent-config-backups-uid-1000/tmp_bug_probe_ubnz7ezp__.env.bak.20260727-235535
CONFIRMED — .env was modified (legacy LLM overrides removed) result=0 after='# keep this comment\n'
```
