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
