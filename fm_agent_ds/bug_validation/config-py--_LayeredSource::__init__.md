# Bug Report: _LayeredSource::__init__

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/config.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

After construction, invoking __call__() on this instance returns a dict whose keys are exactly the model field names of settings_cls. For each field, the value is resolved by the following precedence (highest first): (1) the value of any process environment variable mapped to that field via the environment-to-field mapping, (2) the value from the TOML file at path when path references an existing regular file containing valid TOML syntax, (3) the field's Pydantic default. An environment variable value, when present, overrides a TOML value for the same field regardless of the TOML value's type. If path does not reference an existing regular file, a message identifying the missing file is written to stderr and the TOML source is treated as empty.

---

### Actual Behavior

If no exception occurs during file reading and TOML parsing: super().__init__ completed; if path.is_file() is True, data is the nested dict from tomllib.loads(path.read_text()); if False, a warning is printed to stderr and data is {}; then for each (env_name, (section, field)) in _ENV_MAP, if os.environ.get(env_name) is not None, data.setdefault(section, {})[field] = value; finally self._data = data. If an exception is raised at line 5: super().__init__ completed, no warning, self._data is not set by this method.

---

## Code Evidence

Line 5: data = tomllib.loads(path.read_text())

---

## Trigger Condition

The specification states that after construction, __call__() returns a dict with values resolved from environment, TOML (if the file is a valid TOML- containing regular file), or Pydantic defaults. When the file exists but is not valid TOML, step (2) does not apply, so the expected behavior is to use defaults. The code does not handle the TOMLDecodeError raised by tomllib.loads(), so self._data is never set, causing subsequent __call__() to fail with an AttributeError instead of returning the expected dict of defaults.

---

## How to trigger the bug

The `_LayeredSource.__init__` method reads a TOML file and attempts to parse it with `tomllib.loads()`. When the file exists on disk but contains invalid TOML syntax, `tomllib.loads()` raises a `TOMLDecodeError`. This exception is not caught within `__init__`, so the `self._data = data` line is never reached. As a result, `self._data` is never set on the instance. Any subsequent call to `__call__()` (which returns `self._data`) fails with an `AttributeError`.

The specification requires that when the TOML is invalid (i.e., step (2) does not apply), the source should be treated as empty and defaults should be used — the same behavior as when the file does not exist. Instead, the unhandled exception prevents the object from being usable at all.

### Inputs

| Parameter | Value |
|-----------|-------|
| `settings_cls` | A Pydantic `BaseModel` subclass with fields and defaults |
| `path` | A `Path` pointing to an existing regular file containing **invalid** TOML syntax (e.g., `"[[this is not valid toml [unclosed bracket"`) |

### Expected (spec-correct) Output

`__init__` completes successfully with `self._data = {}` (treating invalid TOML as empty), allowing subsequent `__call__()` to return a dict populated with Pydantic defaults and environment variable overrides.

### Actual (buggy) Output

`tomllib.TOMLDecodeError` is raised during `__init__`. If the caller catches the exception and attempts to call `__call__()`, an `AttributeError` is raised because `self._data` was never set.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from pathlib import Path
from pydantic import BaseModel
from config import _LayeredSource

class DummySettings(BaseModel):
    model_config = {"extra": "forbid"}
    foo: str = "default_value"

# Create a TOML file with invalid syntax
bad_toml = Path("/tmp/invalid.toml")
bad_toml.write_text("[[this is not valid toml [unclosed bracket")

# This raises tomllib.TOMLDecodeError
source = _LayeredSource(DummySettings, bad_toml)
# actual (buggy) output: TOMLDecodeError: Expected ']]' at the end of an array declaration
# expected (correct) output: construction succeeds, source() returns {"foo": "default_value"}
```

---

## Probe Script

```python
"""Probe for bug: _LayeredSource.__init__ does not catch tomllib.TOMLDecodeError
when the TOML file exists but contains invalid syntax.

Bug ID: config-py--_LayeredSource::__init__

Expected (spec): invalid TOML should be treated as empty (like a missing file),
and __call__() should return a dict of defaults.

Actual (bug): tomllib.TOMLDecodeError propagates from __init__, so self._data
is never set. If the caller catches the error and then calls __call__(),
it gets an AttributeError instead of a dict of defaults.
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure the repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# --- Save and sanitize environment to isolate the test ---
_saved_env = {k: os.environ.get(k) for k in (
    "FM_AGENT_CONFIG", "LLM_API_KEY", "LLM_API_BASE_URL", "FM_AGENT_MODEL_BACKEND",
    "LLM_MODEL", "LLM_EFFORT", "OPENCODE_MODEL_PROVIDER", "LLM_API_STYLE",
    "MAX_SPC_ITER", "GRANULARITY", "MAX_WORKERS", "OPENCODE_MAX_RETRIES",
    "BUG_VALIDATION_MAX_RETRIES", "OPENCODE_TIMEOUT_SECONDS",
    "FM_AGENT_DOMAIN_KNOWLEDGE",
)}
for k in _saved_env:
    if k in os.environ:
        del os.environ[k]

tmpdir = None

try:
    # --- Step 1: Create a temporary invalid TOML file ---
    tmpdir = tempfile.mkdtemp(prefix="probe_layered_init_")
    bad_toml = Path(tmpdir) / "invalid.toml"
    # Content that looks like a file but is not valid TOML syntax
    bad_toml.write_text("[[this is not valid toml [unclosed bracket = garbage")

    # --- Step 2: Import the target class ---
    from pydantic import BaseModel
    from config import _LayeredSource

    # --- Step 3: Create a minimal settings class ---
    class DummySettings(BaseModel):
        model_config = {"extra": "forbid"}
        foo: str = "default_value"

    # --- Step 4: Attempt construction with invalid TOML ---
    # Spec says: invalid TOML → treated as empty → defaults used.
    # Bug says:  TOMLDecodeError propagates, self._data never set.
    source = _LayeredSource(DummySettings, bad_toml)

    # If we reach here, __init__ did NOT raise. Check __call__():
    result = source()
    print(
        f"NOT CONFIRMED — construction succeeded unexpectedly; "
        f"__call__() returned: {result!r}"
    )

except Exception as e:
    import tomllib  # stdlib in Python 3.11+

    if isinstance(e, tomllib.TOMLDecodeError):
        print(
            f"CONFIRMED — TOMLDecodeError raised during __init__; "
            f"spec requires treating invalid TOML as empty/defaults "
            f"instead of propagating the error. "
            f"Exception: {e}"
        )
    elif isinstance(e, AttributeError) and "_data" in str(e):
        # This path occurs if __init__ succeeded but self._data was never set
        # (e.g. if TOMLDecodeError was caught by someone else earlier)
        print(
            f"CONFIRMED — AttributeError on __call__(): "
            f"self._data not set due to unhandled TOMLDecodeError in __init__. "
            f"Exception: {e}"
        )
    else:
        import traceback
        traceback.print_exc()
        print(f"ERROR: unexpected exception: {type(e).__name__}: {e}")

finally:
    # Restore environment
    for k, v in _saved_env.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]

    # Clean up temp directory
    if tmpdir:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — TOMLDecodeError raised during __init__; spec requires treating invalid TOML as empty/defaults instead of propagating the error. Exception: Expected ']]' at the end of an array declaration (at line 1, column 8)
```
