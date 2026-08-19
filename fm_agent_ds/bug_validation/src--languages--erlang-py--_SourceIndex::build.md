# Bug Report: _SourceIndex.build

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a _SourceIndex instance that indexes source by line boundaries. The returned instance contains the full source text verbatim (with all line-ending characters preserved) and a list of zero-indexed byte offsets where each line begins within source. The first offset is always 0. Successive offsets increase monotonically — each offset equals the sum of byte lengths of all preceding lines (including their line-ending characters). The number of offsets equals the number of newline-delimited lines in source. The returned instance enables callers to map any valid line index and character position to the corresponding byte offset within source, and to extract contiguous substrings spanning an inclusive start byte offset to an exclusive end byte offset.

---

### Actual Behavior

Returns an instance r of _SourceIndex such that r.source == source, r.lines == source.splitlines(keepends=True), and for all i in 0..len(r.lines)-1: r.line_offsets[i] == sum(len(r.lines[j]) for j in range(i)).

---

## Code Evidence

Line 7: offset += len(line)

---

## Trigger Condition

The specification explicitly requires byte offsets into the source text, but the code uses len(line) which returns the number of Unicode code points (characters). For strings containing multi-byte characters (e.g., non-ASCII), character length differs from byte length, causing incorrect byte offsets. The counterexample demonstrates this with a string containing the two-byte character 'é'.

---

## How to trigger the bug

The `_SourceIndex.build` classmethod uses `len(line)` (Python's built-in) to accumulate offsets, but `len()` returns the count of Unicode code points, not the byte length. For strings containing multi-byte UTF-8 characters like `é` (U+00E9, 2 bytes in UTF-8), this produces incorrect byte offsets.

### Inputs

| Parameter | Value |
|-----------|-------|
| `source` | `"Hé\nW\n"` |

The string contains the two-byte UTF-8 character `é` (U+00E9) which encodes as `0xC3 0xA9`.

### Expected (spec-correct) Output

`line_offsets == [0, 4]`

Because:
- Line 0 (`"Hé\n"`) occupies bytes [0, 3]: H (1 byte) + é (2 bytes) + \n (1 byte)
- Line 1 (`"W\n"`) starts at byte 4

### Actual (buggy) Output

`line_offsets == [0, 3]`

Because `len("Hé\n")` returns 3 (the number of code points), not 4 (the number of UTF-8 bytes).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import _SourceIndex

source = "Hé\nW\n"             # é = U+00E9, 2-byte UTF-8 character
idx = _SourceIndex.build(source)

# line_offsets should be [0, 4] (byte offsets)
# but actual result is [0, 3] (character-length offsets)
print(idx.line_offsets)         # actual (buggy) output: [0, 3]
# expected (correct) output:    [0, 4]
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — actual (char offsets): [0, 3] | expected (byte offsets): [0, 4, 6]
```
