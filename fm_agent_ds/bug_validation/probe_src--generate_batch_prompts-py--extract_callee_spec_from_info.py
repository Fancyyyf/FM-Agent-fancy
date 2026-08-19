"""Probe for extract_callee_spec_from_info: missing "name" key bug — attempt 3."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.generate_batch_prompts import extract_callee_spec_from_info
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Attempt 3: Same bug class but with callee that HAS "name" key set to empty
# string and missing "name" key variants — all tested together. The spec
# requires a "string-typed 'name' field" (must exist and be string). An entry
# with name="" technically has that field, but if empty string matches a
# candidate, the function might return it. Entries without a "name" key should
# never match. We test both.

def test_bug(title, info_dict, callee_fqn, aliases, expect_none):
    actual = extract_callee_spec_from_info(info_dict, callee_fqn, aliases)
    bug_reproduced = (actual is not None) if expect_none else False
    print(f"  {title}: actual={actual!r}, expect_none={expect_none}, bug={bug_reproduced}")
    return bug_reproduced

any_confirmed = False

# Case A: callee explicitly has name="" with empty callee_fqn
any_confirmed |= test_bug(
    "name='' explicit + empty callee_fqn",
    {"callees": [{"name": "", "signature": "void bad()", "pre_condition": "", "post_condition": ""}]},
    "", None, expect_none=True  # spec says should return None
)

# Case B: callee missing "name" key with empty callee_fqn
any_confirmed |= test_bug(
    "missing name key + empty callee_fqn",
    {"callees": [{"signature": "void bad()", "pre_condition": "", "post_condition": ""}]},
    "", None, expect_none=True
)

# Case C: callee missing "name" key first in list, then a valid one
any_confirmed |= test_bug(
    "missing name first + valid callee second",
    {"callees": [
        {"signature": "void bad()", "pre_condition": "", "post_condition": ""},
        {"name": "real_func", "signature": "void real_func()", "pre_condition": "", "post_condition": ""},
    ]},
    "real_func", None, expect_none=False  # should return the valid one
)

if any_confirmed:
    print("CONFIRMED — at least one test reproduced the bug")
else:
    print("NOT CONFIRMED — all tests behaved per spec")
