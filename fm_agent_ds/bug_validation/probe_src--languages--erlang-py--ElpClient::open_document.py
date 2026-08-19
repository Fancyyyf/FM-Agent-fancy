"""Probe for bug: ElpClient.open_document raises FileNotFoundError when source=None
and the file does not exist, but the spec only allows exceptions for
server unreachable, notification rejection, or connection loss.

Bug ID: src--languages--erlang-py--ElpClient::open_document

Expected (spec): Only server-reachable, notification-rejection, or
connection-loss exceptions are allowed. File-read errors like
FileNotFoundError should not propagate from open_document.

Actual (bug): document.read_text() on line 247 raises FileNotFoundError
when the file doesn't exist, before any notification is attempted.
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure repo root is on sys.path so 'src' package resolves
repo_root = os.path.dirname(os.path.abspath(__file__))
for _ in range(5):
    if os.path.isdir(os.path.join(repo_root, "src")) and os.path.isfile(os.path.join(repo_root, "config.py")):
        break
    repo_root = os.path.dirname(repo_root)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# --- Save environment relevant to FM_AGENT config ---
_saved_env = {k: os.environ.get(k) for k in (
    "FM_AGENT_CONFIG", "LLM_API_KEY", "LLM_API_BASE_URL",
    "FM_AGENT_MODEL_BACKEND", "LLM_MODEL",
)}
for k in _saved_env:
    if k in os.environ:
        del os.environ[k]

tmpdir = None
confirmed = None

try:
    from src.languages.erlang import ElpClient
except Exception as e:
    print(f"ERROR: Failed to import ElpClient: {e}")
    sys.exit(1)

try:
    # Create a temporary directory for the probe workspace
    tmpdir = tempfile.mkdtemp(prefix="probe_open_document_")
    nonexistent_file = Path(tmpdir) / "nonexistent_file.erl"

    # Ensure the file genuinely does not exist
    if nonexistent_file.exists():
        nonexistent_file.unlink()

    # Create an ElpClient pointing at the temp dir (no server started)
    client = ElpClient(str(tmpdir))

    # Attempt to open a non-existent document with source=None
    # Spec allows only server/network exceptions, but this should raise
    # FileNotFoundError — a file-read exception not covered by the spec.
    client.open_document(str(nonexistent_file), source=None)

    # If we reach here, no exception was raised — bug NOT confirmed
    print(
        "NOT CONFIRMED — open_document() completed without raising "
        f"FileNotFoundError for non-existent file: {nonexistent_file}"
    )

except Exception as e:
    if isinstance(e, FileNotFoundError) or (
        hasattr(e, "__class__") and e.__class__.__name__ == "FileNotFoundError"
    ):
        print(
            f"CONFIRMED — FileNotFoundError raised by open_document() "
            f"when source=None and the file does not exist. "
            f"The spec only allows exceptions for server unreachable, "
            f"notification rejection, or connection loss. "
            f"Exception: {type(e).__name__}: {e}"
        )
    elif isinstance(e, PermissionError):
        print(
            f"CONFIRMED — PermissionError raised by open_document() "
            f"when source=None and the file is not readable. "
            f"This is also a file-read exception not allowed by the spec. "
            f"Exception: {type(e).__name__}: {e}"
        )
    else:
        import traceback
        traceback.print_exc()
        print(f"ERROR: unexpected exception type: {type(e).__name__}: {e}")

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
