# Bug Report: warn_dotenv_overrides_for_updates

**Source file:** `src/configure_llm.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Prints a warning to stdout when one or more keys in updates correspond to environment variables whose values are present in the .env file at env_path, indicating that those .env values would override the TOML updates. Returns True when at least one warning was printed; returns False when no overrides were found, or the .env file is absent or unreadable.

---

### Actual Behavior

After normal execution (i.e., no exceptions), the function returns a boolean indicating whether any legacy environment variable overrides in the .env file shadow the supplied TOML updates. Let `content = _read_text_if_exists(env_path)` and `(_, overrides) = remove_legacy_llm_env_overrides(content)`. Define `shadowing = { name in overrides | _TOML_KEY_BY_ENV_KEY[name] in updates }`. If `shadowing` is empty, the function returns `False` and produces no output. Otherwise, it prints exactly the warning text: 'Warning: these project .env variables still override this TOML update:' followed by a line with the comma-separated list of `shadowing` names, then 'The set command does not modify .env. Remove those lines, or run the', 'interactive wizard to migrate legacy LLM overrides.', and returns `True`. The `env_path` file, the `updates` dictionary, and any global state are unchanged except for the standard output stream.

---

## Code Evidence

Line 6:     _updated_env, legacy_overrides = remove_legacy_llm_env_overrides(
Line 7:         _read_text_if_exists(env_path)
Line 8:     )

---

## Trigger Condition

The specification explicitly states that the function should return False when the .env file is absent or unreadable. The code provides no error handling for these scenarios; an unreadable file will cause an exception to be raised, violating the required behavior.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| `env_path` | Path to an unreadable `.env` file (permission `0o000`) |
| `updates` | `{}` (empty dict) |

### Expected (spec-correct) Output

`False` — the spec states the function returns `False` when the `.env` file is unreadable.

### Actual (buggy) Output

`PermissionError` is raised — the function propagates the unhandled exception from `_read_text_if_exists(path)` → `path.read_text(encoding="utf-8")` when the file exists but has no read permission.

### Root Cause

`_read_text_if_exists()` (line 710) only checks `path.exists()` but does not guard against `PermissionError` from `path.read_text()`. When the file exists but is unreadable, the exception propagates up through `warn_dotenv_overrides_for_updates()` uncaught, contrary to the spec requiring a `False` return.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Create an unreadable `.env` file in a temporary directory.
3. Call `warn_dotenv_overrides_for_updates()` with that path.

```python
import os
import tempfile
from pathlib import Path

# Add src/ to Python path
import sys
sys.path.insert(0, "src")
import configure_llm

with tempfile.TemporaryDirectory() as tmpdir:
    env_file = Path(tmpdir) / ".env"
    env_file.write_text("LLM_MODEL=test\nLLM_EFFORT=high\n")
    os.chmod(env_file, 0o000)
    # Bug: PermissionError raised; spec says should return False
    configure_llm.warn_dotenv_overrides_for_updates(env_file, {})
    # actual (buggy) output: PermissionError: [Errno 13] Permission denied
    # expected (correct) output: False
```

---

## Probe Script

```python
"""Probe script: verify that warn_dotenv_overrides_for_updates raises
an exception for an unreadable .env file, contrary to the spec which
requires it to return False."""
import sys
import os
import stat
import tempfile
from pathlib import Path

# Probe is at: <project>/fm_agent/bug_validation/probe_<id>.py — 3 levels deep
_PROJECT_ROOT = Path(__file__).absolute().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

try:
    import configure_llm as _configure_llm
    warn_dotenv_overrides_for_updates = _configure_llm.warn_dotenv_overrides_for_updates
except ImportError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

confirmed = False

try:
    with tempfile.TemporaryDirectory(prefix="fm_agent_probe_") as tmpdir:
        env_file = Path(tmpdir) / ".env"

        # Create a dotenv-style file
        env_file.write_text("LLM_MODEL=test-model-override\nLLM_EFFORT=high\n")
        # Make it unreadable (removes read permission for all)
        os.chmod(env_file, 0o000)

        # Verify the probe process itself cannot read it
        try:
            env_file.read_text()
            print(
                "WARN: chmod 000 did not prevent reads — "
                "filesystem may not support Unix perms; "
                "bug cannot be reproduced in this environment"
            )
        except PermissionError:
            pass  # expected — true unreadable file

        updates: dict[str, str] = {}
        try:
            result = warn_dotenv_overrides_for_updates(env_file, updates)
            # If we reach here without exception, the bug is NOT confirmed
            print(
                f"NOT CONFIRMED — function returned {result} "
                f"instead of raising for unreadable .env file"
            )
        except PermissionError:
            confirmed = True
            print(
                "CONFIRMED — PermissionError raised for "
                "unreadable .env file; spec requires returning False"
            )
        except OSError as exc:
            confirmed = True
            print(
                f"CONFIRMED — OSError ({type(exc).__name__}: {exc}) "
                f"raised for unreadable .env file; spec requires returning False"
            )
        except Exception as exc:
            confirmed = True
            print(
                f"CONFIRMED — Exception ({type(exc).__name__}: {exc}) "
                f"raised for unreadable .env file; spec requires returning False"
            )
        finally:
            # Restore permissions so tempdir cleanup doesn't fail
            os.chmod(env_file, stat.S_IRUSR | stat.S_IWUSR)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — PermissionError raised for unreadable .env file; spec requires returning False
```
