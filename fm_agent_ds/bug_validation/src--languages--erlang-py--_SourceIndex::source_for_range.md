# Bug Report: _SourceIndex::source_for_range

**Source file:** `fm_agent/extracted_functions/src/languages/erlang-py/_SourceIndex::source_for_range.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the substring of self.source spanning from the byte offset corresponding to lsp_range['start'] (inclusive) to the byte offset corresponding to lsp_range['end'] (exclusive). Byte-offset resolution follows the same rules as position_to_offset: positions exceeding source boundaries are clamped to the nearest valid offset; characters above U+FFFF consume two UTF-16 code units in position mapping.

---

### Actual Behavior

The method returns a string result such that result == self.source[start:end], where start = self.position_to_offset(lsp_range['start']) and end = self.position_to_offset(lsp_range['end']). Because the pre-condition guarantees that lsp_range['start'] does not lexicographically follow lsp_range['end'] relative to the source contents, we have start <= end. The slicing operation self.source[start:end] yields the substring from offset start (inclusive) to end (exclusive); if start equals end, the empty string is returned. No exceptions are raised.

---

## Code Evidence

Line 4: return self.source[start:end]

---

## Trigger Condition

The code slices the Python string using byte offsets as if they were code point indices. When the source contains characters that occupy more than one byte in the underlying encoding (e.g. '' U+1F600), position_to_offset returns byte offsets that do not align with string indices. In the counterexample, start=1 and end=5 (byte offsets for the emoji in UTF-8), but self.source[1:5] returns 'c' instead of just '' as the specification requires.

---

## How to trigger the bug

The bug cannot be triggered. The analysis in the trigger condition is incorrect: `position_to_offset` does NOT return byte offsets. It returns code point offsets because:

1. `_SourceIndex.build()` computes `line_offsets` using `offset += len(line)`, where `len(line)` in Python returns the number of Unicode code points, not bytes.
2. `position_to_offset` increments `index` by 1 per character, counting code points.
3. The return value `base + index` is therefore a **code point index**, not a byte offset.
4. Python string slicing `self.source[start:end]` also uses code point indices.
5. The implementation is self-consistent and correct for all inputs.

The verification tool appears to have incorrectly assumed that `len()` returns byte counts, which is only true for ASCII strings. For Unicode strings with multi-byte characters in their UTF-8 encoding, `len()` still returns code point count.

### Inputs

| Parameter | Value |
|-----------|-------|
| `self.source` | `"a\U0001F600b"` (3 code points: 'a', 😀, 'b'; 6 bytes in UTF-8) |
| `lsp_range.start` | `{"line": 0, "character": 1}` |
| `lsp_range.end` | `{"line": 0, "character": 3}` |

### Expected (spec-correct) Output

`"\U0001F600"` (just the emoji, since character positions 1-3 in UTF-16 span the emoji)

### Actual (buggy) Output

`"\U0001F600"` — matches expected; no bug present.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, "src")
sys.path.insert(0, ".")
from languages.erlang import _SourceIndex

source = "a\U0001F600b"
index = _SourceIndex.build(source)
result = index.source_for_range(
    {"start": {"line": 0, "character": 1}, "end": {"line": 0, "character": 3}}
)
# result == "\U0001F600" — correct, not buggy
# position_to_offset returns code point offsets: len() counts code points, not bytes
```

---

## Probe Script

```python
"""Probe script for bug: _SourceIndex::source_for_range — byte offset vs code point offset.

The bug report claims that position_to_offset returns byte offsets which don't
align with Python string indices, causing incorrect slicing for multi-byte chars.

This probe tests whether the bug actually manifests by using the public API
_source_for_range with Unicode characters above U+FFFF (which take 2 UTF-16
code units in LSP).
"""

import sys

try:
    # Load via the package entry point (src/ package and root for config.py)
    sys.path.insert(0, "/home/fancy/Projects_Vault/FM-Agent/src")
    sys.path.insert(0, "/home/fancy/Projects_Vault/FM-Agent")
    from languages.erlang import _SourceIndex, _source_for_range

    # ── Test 1: Emoji (U+1F600, 2 UTF-16 units) surrounded by ASCII ──
    source1 = "a\U0001F600b"  # 'a' + U+1F600 + 'b'
    index1 = _SourceIndex.build(source1)

    # LSP range from UTF-16 character 1 (after 'a') to 3 (after emoji)
    # This should return just the emoji
    lsp_range1 = {"start": {"line": 0, "character": 1}, "end": {"line": 0, "character": 3}}
    actual1 = index1.source_for_range(lsp_range1)
    expected1 = "\U0001F600"

    # Also test the public compatibility wrapper
    actual1b = _source_for_range(source1, lsp_range1)

    # ── Test 2: CJK character (U+4E2D, 1 UTF-16 unit) ──
    source2 = "\u4E2D\u56FD"  # 中国
    index2 = _SourceIndex.build(source2)
    lsp_range2 = {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}}
    actual2 = index2.source_for_range(lsp_range2)
    expected2 = "\u4E2D"  # 中

    # ── Test 3: Multiple emoji ──
    source3 = "\U0001F600\U0001F431"  # 😀🐱
    index3 = _SourceIndex.build(source3)
    lsp_range3 = {"start": {"line": 0, "character": 2}, "end": {"line": 0, "character": 4}}
    actual3 = index3.source_for_range(lsp_range3)
    expected3 = "\U0001F431"

    # ── Test 4: Empty range ──
    lsp_range4 = {"start": {"line": 0, "character": 1}, "end": {"line": 0, "character": 1}}
    actual4 = index1.source_for_range(lsp_range4)
    expected4 = ""

    # ── Test 5: Verify position_to_offset actually returns code point offsets ──
    cp_offset = index1.position_to_offset({"line": 0, "character": 1})
    is_code_point = (cp_offset == 1) and (source1[cp_offset] == "\U0001F600")

    # Run all tests
    all_passed = True
    failures = []

    for name, actual, expected in [
        ("Test 1 (public API)", actual1b, expected1),
        ("Test 1 (direct)",    actual1,  expected1),
        ("Test 2",             actual2,  expected2),
        ("Test 3",             actual3,  expected3),
        ("Test 4 (empty)",     actual4,  expected4),
    ]:
        if actual == expected:
            continue
        all_passed = False
        failures.append(f"  {name}: actual={actual!r} expected={expected!r}")

    bug_exists = not all_passed

    print(f"Source 'a😀b' lengths: len(str)={len(source1)}, len(utf8)={len(source1.encode('utf-8'))}")
    print(f"position_to_offset(chr 1) returned: {cp_offset}")
    print(f"Is code point offset? {is_code_point} (cp_offset==1 and source[cp_offset]==😀)")
    print()

    if bug_exists:
        for f in failures:
            print(f)
        print(f"CONFIRMED — source_for_range returns incorrect slices for multi-byte characters")
    else:
        print("All tests passed — source_for_range correctly returns substrings")
        print("NOT CONFIRMED — source_for_range works correctly; position_to_offset returns code point offsets, not byte offsets")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
Source 'a😀b' lengths: len(str)=3, len(utf8)=6
position_to_offset(chr 1) returned: 1
Is code point offset? True (cp_offset==1 and source[cp_offset]==😀)

All tests passed — source_for_range correctly returns substrings
NOT CONFIRMED — source_for_range works correctly; position_to_offset returns code point offsets, not byte offsets
```
