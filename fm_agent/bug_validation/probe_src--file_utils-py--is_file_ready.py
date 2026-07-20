import sys
import os
import tempfile

try:
    from src.file_utils import is_file_ready
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# The spec says: marker lines must have "a language-appropriate single-line
# comment prefix followed immediately by the bracketed section label".
# The spec does NOT forbid leading whitespace on marker lines.
# The bug claim: _READY_MARKER_RE.fullmatch(line) fails when marker lines
# have leading whitespace, causing a valid file to be rejected.

# Create a temp file with leading whitespace on all marker lines
# and proper comment-only content between them.
test_content = """  # [SPEC]
  # Unit: test.py
  #
  # Test function
  # [SPEC]

  # [INFO]
  # (no callees)
  # [INFO]
"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(test_content)
    tmp_path = f.name

try:
    actual = is_file_ready(tmp_path)
    # According to the spec, this file should be VALID (all markers present
    # in order, consistent prefix '#', no non-comment content between markers,
    # leading whitespace is NOT forbidden).
    expected = True
    passed = actual != expected  # True means bug reproduced (should be True but got False)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    os.unlink(tmp_path)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
