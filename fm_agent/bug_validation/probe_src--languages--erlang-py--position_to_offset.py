import sys
try:
    from src.languages.erlang import _position_to_offset

    # The bug: position_to_offset returns "base + index" where index counts
    # characters, but base is a byte offset. For multi-byte UTF-8 characters,
    # character count != byte count within the line.
    #
    # 'é' is U+00E9 (BMP, 1 UTF-16 unit), but 2 bytes in UTF-8: 0xC3 0xA9
    # 'a' is U+0061 (BMP, 1 UTF-16 unit), 1 byte in UTF-8: 0x61
    # Source string "éa" has bytes: [0xC3, 0xA9, 0x61] → total 3 bytes
    #
    # position {"line": 0, "character": 1}: second character 'a'
    # Expected byte offset: 2 (skip 2 bytes of 'é')
    # Buggy return: base(0) + index(1) = 1 → WRONG

    source = "\u00e9a"  # "éa" — multi-byte start
    position = {"line": 0, "character": 1}
    actual = _position_to_offset(source, position)
    expected = 2  # byte offset of 'a' after 2-byte 'é'

    # Verify the actual byte: source[actual] should be 'a' but is 0xA9 (middle of é)
    actual_byte = source.encode("utf-8")[actual]
    expected_byte = ord("a")  # 0x61

    passed = actual != expected
except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(
        f'CONFIRMED — actual offset: {actual} (points to byte 0x{actual_byte:02X}), '
        f'expected offset: {expected} (character "a" at byte 0x{expected_byte:02X})'
    )
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
