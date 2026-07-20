import sys
sys.path.insert(0, '.')

try:
    from src.incremental_reasoner import _split_spec_and_info
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Trigger condition: block with text before the first [SPEC] delimiter and two [SPEC] delimiters
# The spec requires spec_block from (and including) the first spec-delimiter line
# through (and including) the second. The buggy code instead uses lines[:spec_end+1],
# incorrectly including all lines from the start of block up to the second delimiter.
block = "extra\n[SPEC]\ncontent\n[SPEC]"
comment_prefix = "#"
spec_marker = "[SPEC]"

try:
    actual_spec, actual_info = _split_spec_and_info(block, comment_prefix, spec_marker)

    # Per spec: spec_block should be from first [SPEC] through second [SPEC] (inclusive),
    # with leading and trailing blank lines removed.
    expected_spec = "[SPEC]\ncontent\n[SPEC]"
    expected_info = None

    # Bug confirmed if actual_spec != expected_spec
    passed = actual_spec != expected_spec

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual_spec!r} | expected: {expected_spec!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual_spec!r}')
