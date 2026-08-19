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
    # Both are 2 UTF-16 units. Character 0-2 = first emoji, 2-4 = second.
    lsp_range3 = {"start": {"line": 0, "character": 2}, "end": {"line": 0, "character": 4}}
    actual3 = index3.source_for_range(lsp_range3)
    expected3 = "\U0001F431"

    # ── Test 4: Empty range ──
    lsp_range4 = {"start": {"line": 0, "character": 1}, "end": {"line": 0, "character": 1}}
    actual4 = index1.source_for_range(lsp_range4)
    expected4 = ""

    # ── Test 5: Verify position_to_offset actually returns code point offsets ──
    # For source "a😀b": len=3 code points, 😀 is at code point index 1
    # Verify that position_to_offset returns 1 for character position 1 (not a byte offset like 1)
    cp_offset = index1.position_to_offset({"line": 0, "character": 1})
    # If cp_offset is a code point index, then source1[cp_offset] should access the emoji
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

    # Now check if the bug EXISTS: the bug would manifest if source_for_range
    # returns the wrong substring for multi-byte characters
    bug_exists = not all_passed

    # Print detailed output
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
