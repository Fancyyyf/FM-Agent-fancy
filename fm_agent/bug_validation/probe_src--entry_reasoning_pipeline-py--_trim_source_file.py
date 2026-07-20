"""Probe script for _trim_source_file encoding preservation bug.

Bug: open(filepath, "w") on line 74 (extracted) / line 149 (source) does
not specify an encoding parameter, so the file is re-encoded using the
system default. This violates the spec: "File encoding is preserved
(the original raw lines are written back)."

Test: Creates a Python file with non-ASCII bytes in Latin-1 encoding
(invalid as UTF-8), invokes _trim_source_file via the package entry point,
and verifies that the encoding is NOT preserved (original bytes differ
from bytes after trim).
"""
import sys
import os
import tempfile

# The script is run from repo root, so CWD is the repo root.
# Add CWD to sys.path so src/ is importable.
sys.path.insert(0, os.getcwd())

# --- Arrange ---

# Create a Python source file whose bytes are valid Latin-1 but NOT valid UTF-8.
# The Latin-1 byte 0xE9 (é) is followed by 0x41 (A), making it invalid in UTF-8
# (0xE9 starts a 3-byte sequence but 0x41 is not a valid continuation byte).
# The file must contain at least one valid function so _function_spans detects it.

# Build the content with raw bytes for the Latin-1 character
comment_line = b"# Caf\xe9 - tr\xe8s bon\n"  # "Café - très bon" in Latin-1

source_content = (
    comment_line +
    b"\n"
    b"def foo():\n"
    b'    """A simple test function."""\n'
    b"    return 42\n"
    b"\n"
    b"def bar():\n"
    b'    """Another test function to be removed."""\n'
    b"    return 0\n"
)

fd, test_file = tempfile.mkstemp(suffix=".py", prefix="_fm_test_trim_")
os.close(fd)

try:
    # Write the file as raw bytes (Latin-1 encoded, but also a valid Python file)
    with open(test_file, "wb") as f:
        f.write(source_content)

    # Read original raw bytes for comparison
    with open(test_file, "rb") as f:
        original_bytes = f.read()

    # --- Act: call _trim_source_file through the package entry point ---
    # We import from the src package which is the primary public module
    # structure of this project.
    from src.entry_reasoning_pipeline import _trim_source_file

    kept, removed = _trim_source_file(test_file, {"foo"})

    # --- Assert ---
    # Read the file again after trimming
    with open(test_file, "rb") as f:
        new_bytes = f.read()

    if kept == 1 and removed == 1:
        # Verify encoding corruption: non-ASCII bytes should differ
        # The Latin-1 0xE9 (é) should be corrupted to UTF-8 U+FFFD bytes
        # when read with errors="replace" and written back in system encoding
        if original_bytes != new_bytes:
            # Find the differing bytes for reporting
            orig_non_ascii = [b for b in original_bytes if b > 127]
            new_non_ascii = [b for b in new_bytes if b > 127]
            print(
                f"CONFIRMED — encoding NOT preserved: "
                f"original={len(original_bytes)}B, new={len(new_bytes)}B; "
                f"orig non-ASCII bytes: {orig_non_ascii!r}, "
                f"new non-ASCII bytes: {new_non_ascii!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — encoding preserved "
                f"(original == new, {len(original_bytes)}B)"
            )
    else:
        print(
            f"ERROR: unexpected return values: kept={kept}, removed={removed}; "
            f"expected kept=1, removed=1"
        )
        sys.exit(1)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)
