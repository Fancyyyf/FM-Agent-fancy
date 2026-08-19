"""Probe script for bug: _SourceIndex::position_to_offset returns character index
instead of byte offset for multi-byte UTF-8 characters."""

import sys
import tempfile
import os

# The probe's runtime workspace is a fresh temp dir.
# We still load the package from the repo root via sys.path.
_workspace = tempfile.mkdtemp(prefix="probe_position_to_offset_")

# Ensure the repo root is on the path so that 'from src.languages import erlang' resolves.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.languages.erlang import _position_to_offset
except Exception as e:
    print(f"ERROR: Failed to import _position_to_offset: {e}")
    sys.exit(1)

# ---------------------------------------------------------------
# Source: "😀\n"
#   😀 (U+1F600) = 4 bytes in UTF-8, 2 UTF-16 code units
#   \n          = 1 byte in UTF-8, 1 UTF-16 code unit
#
# Position: {"line": 0, "character": 2}
#   This points to the position just after the emoji (2 UTF-16 code units into line 0).
#   The correct byte offset of this position within the source is 4
#   (the emoji occupies bytes 0-3, the newline starts at byte 4).
# ---------------------------------------------------------------
SOURCE = "\U0001F600\n"  # 😀 followed by newline
POSITION = {"line": 0, "character": 2}
EXPECTED = 4  # byte offset of the newline character

try:
    actual = _position_to_offset(SOURCE, POSITION)
    passed = actual != EXPECTED  # True = bug reproduced (actual does NOT match spec)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {EXPECTED!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

# Clean up workspace
try:
    os.rmdir(_workspace)
except OSError:
    pass
