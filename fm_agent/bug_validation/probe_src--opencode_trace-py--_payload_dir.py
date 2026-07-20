import sys
import os
import tempfile

# Add repo root to sys.path so 'src' and 'config' are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src import opencode_trace

    # Create a temp directory to serve as trace_dir
    trace_dir = tempfile.mkdtemp(prefix="probe_payload_dir_")

    # Create a *file* named "payloads" inside trace_dir (not a directory)
    # This triggers the bug: os.makedirs(path, exist_ok=True) raises FileExistsError
    payloads_path = os.path.join(trace_dir, "payloads")
    with open(payloads_path, "w") as f:
        f.write("this is a file, not a directory")

    # Spec requires: returns a path, directory exists after call
    # Buggy behavior: FileExistsError raised because a file blocks directory creation
    expected = os.path.join(trace_dir, "payloads")
    passed = False
    actual = None
    error_msg = None

    try:
        actual = opencode_trace._payload_dir(trace_dir)
        # If we reached here, the function didn't raise - check if the returned path
        # exists as a directory. The spec says the directory at the returned path
        # exists on the filesystem after the call.
        passed = not os.path.isdir(actual)
    except FileExistsError as e:
        # This confirms the bug: the spec says the function returns a path and
        # directory exists, but instead FileExistsError is raised.
        error_msg = str(e)
        passed = True
    except Exception as e:
        error_msg = str(e)
        passed = False  # unexpected error

    # Cleanup
    os.remove(payloads_path)
    os.rmdir(trace_dir)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    if error_msg:
        print(f"CONFIRMED — FileExistsError raised: {error_msg!r}")
    else:
        print(f"CONFIRMED — actual: {actual!r} | expected directory, but not a dir")
else:
    print(f"NOT CONFIRMED — actual: {actual!r}")
