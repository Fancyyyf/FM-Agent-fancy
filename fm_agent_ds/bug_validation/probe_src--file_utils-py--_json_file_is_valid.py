import sys
import tempfile
import os

try:
    from src.file_utils import _json_file_is_valid
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

test_dir = tempfile.mkdtemp(prefix="probe_json_valid_")

try:
    # Create a file with invalid UTF-8 bytes (0xFF is never valid in UTF-8)
    bad_file = os.path.join(test_dir, "bad_utf8.bin")
    with open(bad_file, "wb") as f:
        f.write(b'\xff\xfe\x00\x00')  # UTF-16 BOM-like bytes, invalid as standalone UTF-8

    # Expected (spec-correct) output: False (never raises, every error caught)
    expected = False

    bug_confirmed = False
    try:
        actual = _json_file_is_valid(bad_file)
        # If no exception raised, the bug is NOT confirmed
        # But wait: what if the bytes happen to decode? 0xFF is always invalid UTF-8.
        print(f'NOT CONFIRMED — no exception raised, returned: {actual!r}')
    except UnicodeDecodeError:
        # Bug confirmed: UnicodeDecodeError escaped the except clause
        bug_confirmed = True
    except Exception as e:
        print(f'NOT CONFIRMED — unexpected exception type: {type(e).__name__}: {e}')
        sys.exit(1)

    if bug_confirmed:
        print(f'CONFIRMED — _json_file_is_valid raised UnicodeDecodeError instead of returning {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected or no UnicodeDecodeError raised')

finally:
    # Cleanup temp files
    import shutil
    try:
        shutil.rmtree(test_dir)
    except Exception:
        pass
