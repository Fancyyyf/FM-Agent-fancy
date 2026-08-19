import sys
import os
import tempfile
import shutil

# Add repo root to Python path so 'src' package is importable.
# The probe is executed from the repo root per the validator instructions.
sys.path.insert(0, os.getcwd())

try:
    from src.env_check import _load_ignored
except Exception as e:
    print(f'ERROR: Failed to import _load_ignored from src.env_check: {e}')
    sys.exit(1)

# Create a temporary directory with a .env_check_memory file containing
# invalid UTF-8 bytes (0xff is never valid UTF-8 by itself).
tmp_dir = tempfile.mkdtemp(prefix='bug_probe_')
file_path = os.path.join(tmp_dir, '.env_check_memory')

try:
    with open(file_path, 'wb') as f:
        f.write(b'\xff\xfe')

    # _load_ignored opens the file in text mode (default encoding),
    # which should raise UnicodeDecodeError on invalid UTF-8.
    actual = _load_ignored(tmp_dir)

    # If we reach here, no exception was raised — bug NOT confirmed.
    print(f'NOT CONFIRMED — _load_ignored returned {actual!r} without raising UnicodeDecodeError')
except UnicodeDecodeError:
    # The spec requires returning an empty set when the file "cannot be read."
    # UnicodeDecodeError is not caught by the except IOError handler,
    # so the exception propagates — bug CONFIRMED.
    print('CONFIRMED — UnicodeDecodeError propagated instead of returning empty set')
except Exception as e:
    print(f'ERROR: Unexpected exception: {type(e).__name__}: {e}')
    sys.exit(1)
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)
