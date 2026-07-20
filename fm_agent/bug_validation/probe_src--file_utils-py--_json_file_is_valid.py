import sys
import os
import tempfile

# Add repo root to path so 'from src.file_utils import ...' works
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

# Create a temp file with byte 0xFF — never valid in any UTF-8 sequence
tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
tmp.write(b'\xff')
tmp_path = tmp.name
tmp.close()

try:
    from src.file_utils import _json_file_is_valid

    # The spec says: returns False when content is not well-formed JSON,
    # and does NOT raise exceptions.
    # The current code only catches OSError and json.JSONDecodeError —
    # UnicodeDecodeError (raised by the text decoder on invalid UTF-8)
    # will propagate to the caller.

    actual = _json_file_is_valid(tmp_path)
    expected = False  # spec says: return False for unparseable content

    # If we got here without exception, the code handled it (either correctly or incorrectly)
    if actual is False:
        print(f'NOT CONFIRMED — returned False as expected (no exception raised)')
    else:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r} (invalid UTF-8 produced wrong result)')

except UnicodeDecodeError:
    # Bug confirmed: the function raised an exception instead of returning False
    print(f'CONFIRMED — UnicodeDecodeError propagated to caller; spec requires return False and no exceptions')
    sys.exit(0)

except Exception as e:
    print(f'ERROR: unexpected exception type: {type(e).__name__}: {e}')
    sys.exit(1)

finally:
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
