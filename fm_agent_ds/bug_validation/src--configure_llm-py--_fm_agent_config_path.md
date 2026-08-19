# Bug Report: _fm_agent_config_path

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/configure_llm-py/_fm_agent_config_path.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a Path whose string representation equals the value obtained by resolving the FM_AGENT_CONFIG configuration key through the following precedence: (1) the process environment variable FM_AGENT_CONFIG, if set; (2) the value of the FM_AGENT_CONFIG key in the dotenv environment file at project_root/.env, if the file exists and contains the key; (3) the literal filename "fm-agent.toml", resolved relative to project_root.

---

### Actual Behavior

The function returns a Path object. If the environment variable 'FM_AGENT_CONFIG' is set and its value is a non-empty string, the returned path is Path(os.environ['FM_AGENT_CONFIG']). Otherwise, if the environment variable is completely absent (None) and the .env file at project_root / '.env' contains a non-empty value for 'FM_AGENT_CONFIG', the returned path is Path(dotenv_values(project_root / '.env').get('FM_AGENT_CONFIG')). In all remaining cases (environment variable present but empty, or absent and .env entry missing or empty), the returned path is project_root / 'fm-agent.toml'. Formally: let env = os.environ.get('FM_AGENT_CONFIG'). If env is not None and env != '': result = Path(env). Else if env is None: let dotenv = dotenv_values(project_root / '.env').get('FM_AGENT_CONFIG'); if dotenv is not None and dotenv != '': result = Path(dotenv); else: result = project_root / 'fm-agent.toml'. Else (env == ''): result = project_root / 'fm-agent.toml'.

---

## Code Evidence

Line 7: return Path(explicit_config) if explicit_config else project_root / "fm-agent.toml"

---

## Trigger Condition

The specification states that if the environment variable FM_AGENT_CONFIG is set (i.e., present in os.environ), its value is used as the path, regardless of whether it is empty. The code incorrectly falls back to the default 'fm-agent.toml' when the variable is set but empty, because the ternary treats an empty string as falsy.

---

## How to trigger the bug

The bug is triggered when the environment variable `FM_AGENT_CONFIG` is set to an empty string. The specification requires that any value present in `os.environ` for `FM_AGENT_CONFIG` be used as the config path without further filtering. The code, however, uses a ternary expression that treats empty strings (and `None`) as falsy, causing it to incorrectly fall back to the default `fm-agent.toml` path.

### Inputs

| Parameter | Value |
|-----------|-------|
| `project_root` | A `Path` pointing to a temporary directory |
| `os.environ["FM_AGENT_CONFIG"]` | `""` (empty string) |

### Expected (spec-correct) Output

`Path("")` (resolves to `PosixPath('.')`)

### Actual (buggy) Output

`project_root / "fm-agent.toml"` (e.g., `PosixPath('/tmp/tmpXXXXXX/fm-agent.toml')`)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
from pathlib import Path
from src.configure_llm import default_paths

with tempfile.TemporaryDirectory() as tmpdir:
    project_root = Path(tmpdir)
    os.environ["FM_AGENT_CONFIG"] = ""
    result = default_paths(project_root)
    # actual (buggy) output: project_root / "fm-agent.toml"
    # expected (correct) output: Path("") (resolves to PosixPath('.'))
    print(result.toml_path)
```

---

## Probe Script

```python
import os
import sys
import tempfile
from pathlib import Path

# Ensure the repo root is on sys.path so src/ can be imported.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from src.configure_llm import default_paths

    _saved = os.environ.get("FM_AGENT_CONFIG")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            os.environ["FM_AGENT_CONFIG"] = ""
            result = default_paths(project_root)
            actual = result.toml_path
            # Spec says: if FM_AGENT_CONFIG is set in os.environ, use it
            # regardless of whether it's empty. Buggy code treats empty string
            # as falsy and falls back to project_root / "fm-agent.toml".
            expected = Path(os.environ["FM_AGENT_CONFIG"])
            passed = actual != expected
    finally:
        if _saved is None:
            os.environ.pop("FM_AGENT_CONFIG", None)
        else:
            os.environ["FM_AGENT_CONFIG"] = _saved
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: PosixPath('/tmp/tmpp7xzcd6p/fm-agent.toml') | expected: PosixPath('.')
```
