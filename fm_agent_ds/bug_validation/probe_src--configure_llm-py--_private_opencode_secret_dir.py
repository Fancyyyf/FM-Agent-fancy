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
