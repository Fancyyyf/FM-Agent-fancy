import sys
sys.path.insert(0, '.')
try:
    from src.incremental_reasoner import _extract_leading_spec_comments

    # Bug: the code strips spec_marker before comparing (line 481),
    # which means a spec_marker with leading/trailing whitespace
    # incorrectly matches a line that lacks that whitespace.
    # The spec says: stripped line must equal spec_marker (verbatim).
    #
    # Here: spec_marker has a trailing space, but the actual content line does not.
    # Spec says: "# [SPEC]" (stripped line) != "# [SPEC] " (spec_marker) → return None
    # Code does: "# [SPEC]" != "# [SPEC]" (both stripped) → continues, returns prefix

    content = "# [SPEC]\n# [SPEC]\ndef foo():\n    pass\n"
    comment_prefix = "#"
    spec_marker = "# [SPEC] "  # trailing space — the key to triggering the bug

    actual = _extract_leading_spec_comments(content, comment_prefix, spec_marker)

    # Per specification: stripped first non-blank line ("# [SPEC]") does NOT
    # equal spec_marker ("# [SPEC] "), so the function should return None.
    expected = None
    passed = actual != expected

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
