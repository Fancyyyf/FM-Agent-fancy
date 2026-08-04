"""Probe script for bug src--languages--erlang-py--_SourceIndex::build.

Tests whether _SourceIndex.build correctly computes byte offsets
(as required by the specification) rather than character offsets
(as the current len()-based code does).
"""

import sys
import os
import tempfile

# Add the FM-Agent source root to the import path before changing directories.
repo_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
src_root = os.path.join(repo_root, "src")
if src_root not in sys.path:
    sys.path.insert(0, src_root)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Do the import BEFORE changing directory — config resolution may rely on cwd.
try:
    from languages.erlang import _SourceIndex
except Exception as e:
    print(f"ERROR: Failed to import _SourceIndex: {e}")
    sys.exit(1)

# Work in a fresh temporary directory — do not use the active repo workspace.
os.chdir(tempfile.mkdtemp())

# Test string with a two-byte UTF-8 character (é = U+00E9, encodes as 0xC3 0xA9)
# "Hé\n" = H(1 byte) + é(2 bytes) + \n(1 byte) = 4 bytes
# But len("Hé\n") = 3 characters
source = "Hé\nW\n"

try:
    index = _SourceIndex.build(source)
except Exception as e:
    print(f"ERROR: _SourceIndex.build() raised: {e}")
    sys.exit(1)

# Compute correct byte offsets by encoding to UTF-8
encoded = source.encode("utf-8")
byte_offsets = [0]
prev = -1
for i, b in enumerate(encoded):
    if b == ord("\n"):
        byte_offsets.append(i + 1)

# Check: does the code match the spec (byte offsets) or the buggy behavior?
# The spec requires byte offsets into source. The code uses len(line) which
# counts Unicode code points, not bytes. For multi-byte characters they differ.
spec_matches = index.line_offsets == byte_offsets

if spec_matches:
    print(
        f"NOT CONFIRMED — offsets match spec (byte positions): {index.line_offsets}"
    )
else:
    print(
        f"CONFIRMED — actual (char offsets): {index.line_offsets} | "
        f"expected (byte offsets): {byte_offsets}"
    )
