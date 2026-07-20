import sys
try:
    from src.generate_batch_prompts import extract_callee_spec_from_info

    # info_block using '//[SPLIT]' (no space between comment prefix and [SPLIT])
    # The specification says the delimiter should be the comment prefix followed
    # directly by '[SPLIT]'. But line 152 hardcodes a space:
    #   split_tag = f"{prefix} [SPLIT]" if prefix else "[SPLIT]"
    # When info_block has '//[SPLIT]', the code constructs '// [SPLIT]' as
    # delimiter, which does not appear in the string, so split returns the
    # entire block as a single entry.
    info_block_no_space = "//[SPLIT]entry1\nhello\n//[SPLIT]entry2\nworld"

    actual = extract_callee_spec_from_info(info_block_no_space, "entry1")

    # Spec-correct expected: just the first entry "entry1\nhello"
    # Buggy actual: the entire block because split with "// [SPLIT]" fails
    expected = "entry1\nhello"

    passed = actual != expected

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
