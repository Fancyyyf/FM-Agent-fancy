import sys

# Load via the package's public API - extract_callee_spec_from_info is the
# simplest public caller that exercises _info_line_mentions_name.
sys.path.insert(0, '.')
from src.generate_batch_prompts import extract_callee_spec_from_info

# Trigger condition: name ending with non-word character '!' followed by space.
# The regex uses \b which does not match between two non-word characters.
# Spec requires matching when name is followed by any non-word character.
info_block = (
    "# [SPLIT]\n"
    "# some_func! bar\n"
    "#   Pre-condition: x is int\n"
    "#   Post-condition: returns int\n"
    "# [SPLIT]\n"
)
callee_fqn = "some_func!"

actual = extract_callee_spec_from_info(info_block, callee_fqn)

# Expected (spec-correct): should return the entry string because "some_func!"
# appears in the first_line at a position followed by a non-word character (space).
expected_behavior = "returns entry (not None)"

# Buggy: returns None because \b fails between non-word chars
is_bug = actual is None

if is_bug:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected_behavior}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
