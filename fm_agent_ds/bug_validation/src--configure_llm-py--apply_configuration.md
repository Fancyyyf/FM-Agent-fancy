# Bug Report: apply_configuration

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/configure_llm-py/apply_configuration.py`
**Actual source file:** `src/configure_llm.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of (modified_file_path, backup_path_or_None) tuples, one entry for each file that was written or would have been written, ordered by the sequence in which the files were written.

---

### Actual Behavior

After the function executes, one of the following holds:

1. **Normal return (no exception):**
   - The return value is a list of 4 tuples of the form (path, backup_path), where:
     - Tuple 0: (paths.toml_path, backup_file(paths.toml_path) )
     - Tuple 1: (paths.env_path, backup_file(paths.env_path, private=True) )
     - Tuple 2: (paths.opencode_config_path, backup_file(paths.opencode_config_path, private=True) )
     - Tuple 3: (opencode_secret_path, backup_file(opencode_secret_path, private=True) )
     where opencode_secret_path = secret_path_for_provider(config).
     For each tuple, the second element is either None (if the file did not exist before the backups were made) or a Path to a timestampsuffixed backup copy. Backups with private=True have permissions 0600 (disallow group/other read).
   - The file at paths.toml_path now contains the result of update_fm_agent_toml_text applied to the original TOML content. All TOML sections, fields, and comments outside the [llm] section are identical to the original. The [llm] sections provider, name, base_url, and api_style match config.provider_id, config.provider_name, config.base_url, and config.api_style respectively.
   - The file at paths.env_path now contains the result of update_env_text applied to the original .env content (which was empty if the file did not exist). The LLM_API_KEY line is set to config.api_key; all other lines are unchanged in order and content.
   - The file at paths.opencode_config_path contains the JSON representation (indented 2, ensure_ascii=False, followed by newline) of a dictionary that represents the merged OpenCode configuration. That dictionary includes a provider entry for config.provider_id with provider: config.api_style and api_key_secret: the absolute string representation of opencode_secret_path. Existing provider entries for other provider IDs are preserved exactly as they were in the original opencode configuration (or empty if none existed).
   - The file at opencode_secret_path contains config.api_key followed by a newline.

---

## Code Evidence

Line 30-38: `backups = [ ... ]` (the order of the list differs from the write order)

---

## Trigger Condition

The specification requires the returned list to be ordered by the sequence in which the files were written (toml, env, secret, opencode config). The code returns the list in the order toml, env, opencode config, secret, which is the order of backup creation, not the write order.

---

## How to trigger the bug

The function `apply_configuration` builds a `backups` list in backup creation order (toml, env, opencode_config, secret) but the specification requires it to be returned in file write order (toml, env, secret, opencode_config). The actual write sequence is toml → env → secret → opencode_config, but the returned list has the last two entries swapped.

### Inputs

| Parameter | Value |
|-----------|-------|
| config.provider_id | "test-provider" |
| config.provider_name | "TestProvider" |
| config.api_style | "openai" |
| config.base_url | "https://test.example.com/v1" |
| config.model_id | "test-model" |
| config.api_key | "sk-fake-key-123" |
| config.backend | "opencode" |
| paths.toml_path | <tmp>/project/fm-agent.toml |
| paths.env_path | <tmp>/project/.env |
| paths.opencode_config_path | <tmp>/opencode.json |

### Expected (spec-correct) Output

```
(toml_path, backup_or_None)
(env_path, backup_or_None)
(secret_path, backup_or_None)
(opencode_config_path, backup_or_None)
```
— ordered by write sequence

### Actual (buggy) Output

```
(toml_path, backup_or_None)
(env_path, backup_or_None)
(opencode_config_path, backup_or_None)
(secret_path, backup_or_None)
```
— ordered by backup creation sequence (indices 2 and 3 swapped)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from pathlib import Path
from src.configure_llm import (
    LLMConfigInput, WizardPaths, apply_configuration, secret_path_for_provider,
)

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    project = tmp / "project"
    project.mkdir()
    toml = project / "fm-agent.toml"
    toml.write_text('[llm]\nname = "test-model"\n')
    env = project / ".env"
    env.write_text("")
    oc = tmp / "opencode.json"

    config = LLMConfigInput(
        provider_id="test-provider", provider_name="TP", api_style="openai",
        base_url="https://x.com/v1", model_id="test-model", api_key="sk-fake",
    )
    paths = WizardPaths(project, env, toml, oc)
    result = apply_configuration(config, paths, validate=False)

    # actual (buggy) output: (toml, env, opencode_config, secret)
    # expected (correct) output: (toml, env, secret, opencode_config)
    print([p.name for p, _ in result])
```

---

## Probe Script

```python
import sys
import os
import tempfile
from pathlib import Path

# Ensure the project root (parent of src/) is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os.chdir(str(_REPO_ROOT))

try:
    from src.configure_llm import (
        LLMConfigInput,
        WizardPaths,
        apply_configuration,
        secret_path_for_provider,
    )
except Exception as e:
    print(f"ERROR: Import failed: {e}")
    sys.exit(1)


def main() -> None:
    # Create a temporary workspace with the minimal fixtures needed to call
    # apply_configuration without touching the real project files.
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project_root = tmp / "project"
        project_root.mkdir()

        # Minimal valid fm-agent.toml so the function does not raise
        toml_path = project_root / "fm-agent.toml"
        toml_path.write_text("[llm]\nname = \"test-model\"\n", encoding="utf-8")

        # Empty .env (new file)
        env_path = project_root / ".env"
        env_path.write_text("", encoding="utf-8")

        # Empty opencode config (new file)
        opencode_config_path = tmp / "opencode.json"

        config = LLMConfigInput(
            provider_id="test-provider",
            provider_name="TestProvider",
            api_style="openai",  # type: ignore[arg-type]
            base_url="https://test.example.com/v1",
            model_id="test-model",
            api_key="sk-fake-key-123",
            backend="opencode",
        )

        paths = WizardPaths(
            project_root=project_root,
            env_path=env_path,
            toml_path=toml_path,
            opencode_config_path=opencode_config_path,
        )

        try:
            result = apply_configuration(config, paths, validate=False)
        except Exception as e:
            print(f"ERROR: apply_configuration raised: {e}")
            sys.exit(1)

        # The write order in apply_configuration is:
        #   1. toml   (line 779: atomic_write(paths.toml_path, ...))
        #   2. env    (line 780: atomic_write(paths.env_path, ...))
        #   3. secret (line 783: atomic_write(opencode_secret_path, ...))
        #   4. opencode_config (line 785: atomic_write(paths.opencode_config_path, ...))
        #
        # The spec says return order must be the write order:
        #   (toml, env, secret, opencode_config)
        #
        # The actual return order is the backups list order:
        #   (toml, env, opencode_config, secret)  — WRONG

        expected_secret_path = secret_path_for_provider(config)

        # The spec-expected order (match write order):
        # index 0: toml_path, index 1: env_path, index 2: secret_path, index 3: opencode_config_path
        spec_order = [toml_path, env_path, expected_secret_path, opencode_config_path]

        # Extract the actual order from the returned list
        actual_order = [entry[0] for entry in result]

        # Check if the spec says index 2 should be the secret path
        # but the code returns it at index 3 (and opencode_config at index 2)
        if actual_order[2] == opencode_config_path and actual_order[3] == expected_secret_path:
            # Bug confirmed: spec wants secret at position 2, but code has opencode_config at position 2
            print(
                f"CONFIRMED — Return order does not match write order.\n"
                f"  Spec (write order) : [{spec_order[0].name}, {spec_order[1].name}, {spec_order[2].name}, {spec_order[3].name}]\n"
                f"  Actual (backup order): [{actual_order[0].name}, {actual_order[1].name}, {actual_order[2].name}, {actual_order[3].name}]\n"
                f"  Mismatch at positions 2 and 3: spec expects secret before opencode_config"
            )
        elif actual_order == spec_order:
            print(
                f"NOT CONFIRMED — Return order matches write order: {[p.name for p in actual_order]}"
            )
        else:
            print(
                f"NOT CONFIRMED — Unexpected order. "
                f"Spec: {[p.name for p in spec_order]}, "
                f"Actual: {[p.name for p in actual_order]}"
            )


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — Return order does not match write order.
  Spec (write order) : [fm-agent.toml, .env, fm-agent-opencode-api-key.test-provider.793b2b6e7c, opencode.json]
  Actual (backup order): [fm-agent.toml, .env, opencode.json, fm-agent-opencode-api-key.test-provider.793b2b6e7c]
  Mismatch at positions 2 and 3: spec expects secret before opencode_config
```
