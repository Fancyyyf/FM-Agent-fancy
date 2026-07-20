# Bug Report: _trim_source_file

**Source file:** `src/entry_reasoning_pipeline.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When the file extension does not map to a recognized language key in
    EXT_TO_LANG, the file is left untouched and (0, 0) is returned
  - When the file has no detected function bodies (spans is empty), the file
    is left untouched and (0, 0) is returned
  - When the file has detected function bodies: every function body whose name
    is a member of keep_names is preserved, every function body whose name is
    not a member of keep_names is removed, and all source lines that do not
    belong to any function body are preserved in their original order and form
  - The source file at filepath is overwritten with the resulting content; the
    file path does not change
  - Returns a tuple (kept, removed) where kept is the count of function bodies
    preserved, removed is the count of function bodies removed, and both are
    non-negative integers whose sum equals the total number of function bodies
    detected in the original file
  - File encoding is preserved (the original raw lines are written back)

---

### Actual Behavior

After the execution of _trim_source_file, one of the following scenarios holds:

1. (Normal return) The function returns a tuple (kept, removed) where kept and removed are non-negative integers, and the file at filepath is in a consistent state.

   - Compute ext = os.path.basename(filepath).rsplit(".", 1)[-1] if "." in os.path.basename(filepath) else "".
   - Compute lang_key = EXT_TO_LANG.get(ext).
   - If lang_key is falsy: kept = 0, removed = 0, and the file at filepath is unchanged (identical to its pre-execution content).
   - Otherwise, let (spans, raw_lines) = _function_spans(filepath, lang_key, proj_dir) (assuming no exception).
        * If spans is empty: kept = 0, removed = 0, and the file at filepath is unchanged.
        * Else:
              + kept = |{ (n, s, e)  spans | n  keep_names }|.
              + removed = |{ (n, s, e)  spans | n  keep_names }|.
              + Define drop = { i |  (n, s, e)  spans : n  keep_names  i  [s, e] } (line indices to delete).
              + If drop is empty: the file at filepath is unchanged.
              + If drop is non-empty: the file at filepath is overwritten with the list [ ln for idx, ln in enumerate(raw_lines) if idx  drop ] (preserving order of the remaining lines). The new content replaces the original file content.

    The file write uses `open(filepath, "w")` which defaults to the system preferred encoding. When the original file was encoded in something other than the system default, the byte-level content of the file changes even though the logical line list is preserved. This violates the "File encoding is preserved" clause of the specification.

---

## Code Evidence

Line 28 (extracted) / Line 149 (source): `with open(filepath, "w") as f:`

The file is opened in default text mode (`"w"`) without capturing or reusing the encoding from the original file. When the file is overwritten, its bytes are re-encoded using the system default, which may differ from the original encoding, failing to preserve the file encoding as required by the specification.

---

## Trigger Condition

The code opens the file in default text mode ('w') without capturing or reusing the encoding from the original file. When the file is overwritten, its bytes are re-encoded using the system default, which may differ from the original encoding, failing to preserve the file encoding as required by the specification.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| filepath | Absolute path to a Python source file containing non-ASCII bytes encoded in Latin-1 (e.g., `é` as byte `0xE9`) |
| keep_names | `{"foo"}` (keep only the `foo` function) |
| proj_dir | None (default) |

### Expected (spec-correct) Output

The file on disk should contain the same bytes as before the call. The Latin-1 encoded characters `é` (0xE9) and `è` (0xE8) should survive the trim operation unchanged. The file's byte-level encoding should be preserved.

### Actual (buggy) Output

The file is re-encoded using the system default encoding (UTF-8 on modern Linux). The Latin-1 bytes 0xE9 and 0xE8 are replaced with the UTF-8 encoding of the Unicode replacement character U+FFFD (0xEF 0xBF 0xBD). The original encoding is lost.

Original file: 150 bytes, non-ASCII bytes: [0xE9, 0xE8]
After trim: 83 bytes, non-ASCII bytes: [0xEF, 0xBF, 0xBD, 0xEF, 0xBF, 0xBD]

### How to Reproduce

1. Navigate to the repo root.
2. Create a Python file with Latin-1 encoded non-ASCII bytes in a comment and two functions (`foo` and `bar`).
3. Run the following snippet (uses the package entry point):

```python
from src.entry_reasoning_pipeline import _trim_source_file

# Create a file with Latin-1 encoded bytes (0xE9 = é)
with open("/tmp/test.py", "wb") as f:
    f.write(b"# Caf\xe9\n\ndef foo():\n    pass\n\ndef bar():\n    pass\n")

# Read original bytes
with open("/tmp/test.py", "rb") as f:
    orig = f.read()

# Trim: keep only foo
_trim_source_file("/tmp/test.py", {"foo"})

# Read new bytes
with open("/tmp/test.py", "rb") as f:
    new = f.read()

print("Original:", orig)   # Contains 0xE9
print("New:", new)         # Contains 0xEF 0xBF 0xBD instead
# actual (buggy) output: bytes differ; encoding not preserved
# expected (correct) output: bytes identical; encoding preserved
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — encoding NOT preserved: original=150B, new=83B; orig non-ASCII bytes: [233, 232], new non-ASCII bytes: [239, 191, 189, 239, 191, 189]
```
