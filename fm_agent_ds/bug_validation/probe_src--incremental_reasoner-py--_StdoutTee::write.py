import sys
import io
import os
import tempfile
from pathlib import Path

# Ensure the repo root is on sys.path so 'src' can be imported.
_repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo_root))

try:
    from src.incremental_reasoner import _StdoutTee

    # Create a read-only file stream (open but not writable)
    fd, tmp_path = tempfile.mkstemp()
    os.close(fd)
    read_only_console = open(tmp_path, 'r')
    log_stream = io.StringIO()

    # /***** ACTUAL RESULT (what the code does) *****/
    tee = _StdoutTee(read_only_console, log_stream)
    actual = None
    bug_reproduced = False
    try:
        actual = tee.write("hello")
    except io.UnsupportedOperation as e:
        actual = f"UnsupportedOperation: {e}"
        bug_reproduced = True
    except Exception as e:
        actual = f"{type(e).__name__}: {e}"
        bug_reproduced = True

    # /***** EXPECTED RESULT (what the spec requires) *****/
    # Spec: "The string data is written to the console stream."
    #        "Returns len(data), the number of characters in data."
    # The spec does NOT say the console stream must be writable — only that it's open.
    expected = 5  # len("hello") = 5

    # Bug is confirmed if actual != expected (exception instead of returning len)
    passed = actual != expected

    read_only_console.close()
    os.unlink(tmp_path)

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
