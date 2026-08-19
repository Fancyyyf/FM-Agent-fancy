"""Probe: _ensure_trace_dirs does not guarantee writability of payloads directory.

Spec claim: After _ensure_trace_dirs runs, the 'payloads' subdirectory exists as a writable directory.
Actual behavior: os.makedirs(payload_dir, exist_ok=True) only creates the directory if it doesn't exist;
when the directory already exists with read-only permissions, it remains non-writable.

This probe tests through the public API (append_event), which calls _ensure_trace_dirs internally.
"""
import os
import stat
import sys
import tempfile

# Ensure the repo root is on sys.path so that `src.trace_writer` resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    # Import through public entry point
    from src.trace_writer import append_event
except Exception as e:
    print(f"ERROR: Failed to import src.trace_writer: {e}")
    sys.exit(1)

try:
    # Create a temp directory as our trace_dir
    trace_dir = tempfile.mkdtemp(prefix="bug_probe_")
    payload_dir = os.path.join(trace_dir, "payloads")
    os.makedirs(payload_dir)

    # Make payloads directory read-only (remove write perms)
    os.chmod(payload_dir, stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    # Now call append_event — this internally calls _ensure_trace_dirs
    # which does os.makedirs(payload_dir, exist_ok=True), but since payload_dir
    # already exists, it does nothing — writability is NOT restored.
    append_event(trace_dir, {"test": True, "probe": "ensure_trace_dirs"})

    # After the call, try to write to payloads/ — if the spec were satisfied,
    # the directory would be writable.
    writable = os.access(payload_dir, os.W_OK)
    path_test_file = os.path.join(payload_dir, "can_i_write.txt")

    if writable:
        # Directory is writable — spec satisfied (bug NOT confirmed)
        try:
            with open(path_test_file, "w") as f:
                f.write("ok")
            os.remove(path_test_file)
        except Exception:
            pass
        print(f"NOT CONFIRMED — payloads directory is writable after _ensure_trace_dirs")
    else:
        # Directory is NOT writable — spec violated (bug CONFIRMED)
        print(f"CONFIRMED — actual: payloads directory is NOT writable (os.access says: {writable}) | expected: writable directory per spec. os.makedirs(exist_ok=True) with read-only pre-existing directory does NOT ensure writability.")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    # Cleanup the temporary directory
    try:
        if 'payload_dir' in dir() and os.path.isdir(payload_dir):
            os.chmod(payload_dir, stat.S_IRWXU)
    except Exception:
        pass
    try:
        if 'trace_dir' in dir() and os.path.isdir(trace_dir):
            import shutil
            shutil.rmtree(trace_dir)
    except Exception:
        pass
