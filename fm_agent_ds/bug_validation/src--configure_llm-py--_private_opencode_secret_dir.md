# Bug Report: _private_opencode_secret_dir

**Source file:** `src/configure_llm.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a Path representing the platform-specific directory for storing OpenCode private secret key files. On Windows: the base directory is resolved from the APPDATA environment variable when set, otherwise from the AppData/Roaming directory under the user's home. On other platforms: the base directory is resolved from the XDG_STATE_HOME environment variable when set to an absolute path, otherwise from .local/state under the user's home. The returned path always terminates with the relative path components "fm-agent/opencode". The directory corresponding to the returned path exists on the filesystem after the call returns.

---

### Actual Behavior

The function returns a `Path` object representing the directory path for a secret agent configuration. The return value is constructed as follows:

If the operating system is Windows (`os.name == "nt"`):
  - If the environment variable `APPDATA` is set and non-empty, the base directory is `Path(appdata)`; otherwise it is `Path.home() / "AppData" / "Roaming"`.
  - The return value is `base_dir / "fm-agent" / "opencode"`.

If the operating system is not Windows (Unix-like):
  - Let `xdg_state = os.environ.get("XDG_STATE_HOME")`.
  - If `xdg_state` is set, let `xdg_state_path = Path(xdg_state).expanduser()`, else `xdg_state_path = None`.
  - If `xdg_state_path` is not None and `xdg_state_path.is_absolute()` evaluates to True, then `base_dir = xdg_state_path`; otherwise `base_dir = Path.home() / ".local" / "state"`.
  - The return value is `base_dir / "fm-agent" / "opencode"`.

No side effects occur; only reading environment variables and constructing a `Path` object. The returned path is purely computed and does not guarantee that the directory exists.

Formally: Let R be the returned Path. Then:
  R = (if os.name = "nt" then
         (if  v = os.environ["APPDATA"] then Path(v) else Path.home() / "AppData" / "Roaming")
       else
         (let x = os.environ.get("XDG_STATE_HOME") in
          if x  None  Path(x).expanduser().is_absolute() then Path(x).expanduser()
          else Path.home() / ".local" / "state")
      ) / "fm-agent" / "opencode"

---

## Code Evidence

Line 13: The return statement does not create the directory; the function as defined lacks any logic to ensure the directory exists.

---

## Trigger Condition

Condition B requires that the directory corresponding to the returned path exists on the filesystem after the call returns. The code in condition A merely computes a Path without creating it, and there is no side effect, so it fails to meet this requirement. The code is missing a call to e.g., path.mkdir(parents=True, exist_ok=True) before returning.

---

## How to trigger the bug

The function `_private_opencode_secret_dir` returns a `Path` but never creates the directory it points to. The specification requires the directory to exist on the filesystem after the call returns. The code evidence at line 13 shows the function ends with a bare `return base_dir / "fm-agent" / "opencode"` — no `mkdir` call.

The probe confirms this by overriding `XDG_STATE_HOME` with a controlled empty temporary directory, calling through the public API `secret_path_for_provider`, and verifying that the returned directory does not exist after the call.

### Inputs

| Parameter | Value |
|-----------|-------|
| `config.provider_id` | `test-provider-42` |
| `config.provider_name` | `TestProvider` |
| `config.api_style` | `openai` |
| `config.base_url` | `https://test.example.com/v1` |
| `config.model_id` | `test-model` |
| `config.api_key` | `sk-fake-key-123` |
| `XDG_STATE_HOME` (env) | `/tmp/probe_secret_dir_*/fake-state-home` (empty dir) |

### Expected (spec-correct) Output

The directory `<XDG_STATE_HOME>/fm-agent/opencode` should exist on the filesystem after the call returns.

### Actual (buggy) Output

The directory `<XDG_STATE_HOME>/fm-agent/opencode` does not exist after the call returns. The function computed and returned the path but never created the directory.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
from pathlib import Path
from src.configure_llm import LLMConfigInput, secret_path_for_provider

os.environ["XDG_STATE_HOME"] = "/tmp/test-empty-dir"

config = LLMConfigInput(
    provider_id="test", provider_name="Test",
    api_style="openai", base_url="https://example.com/v1",
    model_id="test-model", api_key="test-key",
)

secret_path = secret_path_for_provider(config)
returned_dir = secret_path.parent   # /tmp/test-empty-dir/fm-agent/opencode
print(returned_dir.exists())        # False — bug: directory was not created
# actual (buggy) output: False
# expected (correct) output: True
```

---

## Probe Script

```python
"""Probe for bug: _private_opencode_secret_dir does not create the directory.

Bug ID: src--configure_llm-py--_private_opencode_secret_dir

The specification requires the directory corresponding to the returned path to
exist on the filesystem after the call returns.  The code_evidence shows the
function merely constructs a Path and returns it — no mkdir call.  To prove
this reliably we set XDG_STATE_HOME to a fresh temporary directory that
contains no fm-agent/opencode subtree.

Approach (attempt 2): override XDG_STATE_HOME with a controlled, empty temp dir
so that any directory existence is attributable to the function under test.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the project root is importable
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# All probe workspace I/O stays inside a fresh temporary directory.
_orig_cwd = os.getcwd()
_probe_work = Path(tempfile.mkdtemp(prefix="probe_secret_dir_"))

# Create an empty temp directory to use as the fake XDG_STATE_HOME.
# The function will return <fake_xdg>/fm-agent/opencode — which does not exist.
_fake_state_home = _probe_work / "fake-state-home"
_fake_state_home.mkdir()

_saved_xdg = os.environ.get("XDG_STATE_HOME")

try:
    os.environ["XDG_STATE_HOME"] = str(_fake_state_home)
    os.chdir(str(_REPO_ROOT))

    from src.configure_llm import LLMConfigInput, secret_path_for_provider

    config = LLMConfigInput(
        provider_id="test-provider-42",
        provider_name="TestProvider",
        api_style="openai",
        base_url="https://test.example.com/v1",
        model_id="test-model",
        api_key="sk-fake-key-123",
        backend="opencode",
    )

    # secret_path_for_provider → _private_opencode_secret_dir → base dir
    secret_path = secret_path_for_provider(config)
    returned_dir = secret_path.parent  # ends with /fm-agent/opencode

    dir_exists = returned_dir.exists() and returned_dir.is_dir()

    if not dir_exists:
        print(
            "CONFIRMED — _private_opencode_secret_dir does not create the "
            "directory it returns.\n"
            f"  XDG_STATE_HOME (fake) : {_fake_state_home}\n"
            f"  Returned path          : {returned_dir}\n"
            f"  Directory exists       : False\n"
            "  Specification requires the directory to exist on the filesystem\n"
            "  after the call returns, but code_evidence shows no mkdir call."
        )
    else:
        print(
            "NOT CONFIRMED — the returned directory already exists on this machine.\n"
            f"  Returned path : {returned_dir}\n"
            f"  Directory exists: True"
        )

except Exception as e:
    import traceback

    traceback.print_exc()
    print(f"ERROR: {e}")

finally:
    os.chdir(_orig_cwd)
    # Restore the original XDG_STATE_HOME (or remove if it wasn't set)
    if _saved_xdg is not None:
        os.environ["XDG_STATE_HOME"] = _saved_xdg
    else:
        os.environ.pop("XDG_STATE_HOME", None)
    shutil.rmtree(_probe_work, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — _private_opencode_secret_dir does not create the directory it returns.
  XDG_STATE_HOME (fake) : /tmp/probe_secret_dir_lwvfnphn/fake-state-home
  Returned path          : /tmp/probe_secret_dir_lwvfnphn/fake-state-home/fm-agent/opencode
  Directory exists       : False
  Specification requires the directory to exist on the filesystem
  after the call returns, but code_evidence shows no mkdir call.
```
