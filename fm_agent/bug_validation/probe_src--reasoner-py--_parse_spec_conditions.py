import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    import src.reasoner as reasoner_mod

    # A spec with an intermediate "Note:" section between Pre-condition and Post-condition.
    # The spec claims pre_condition should stop at the "next section boundary".
    # The buggy regex only looks for "Post-condition:" as boundary, so "Note:" gets included.
    spec = (
        "Pre-condition:\n"
        "x > 0\n"
        "Note:\n"
        "  test\n"
        "Post-condition:\n"
        "result > 0"
    )

    pre, post = reasoner_mod._parse_spec_conditions(spec)

    # Expected: pre should be "x > 0" (stopping at "Note:" section boundary)
    # Actual (buggy): pre includes "Note:\n  test" because regex doesn't recognize "Note:" as boundary
    expected_pre = "x > 0"
    expected_post = "result > 0"

    bug_confirmed = (pre == expected_pre + "\nNote:\n  test" or "Note:" in pre)
    post_ok = (post == expected_post)

    if bug_confirmed and post_ok:
        print(f'CONFIRMED — pre_condition: {pre!r} | expected: {expected_pre!r}')
    elif not bug_confirmed:
        print(f'NOT CONFIRMED — pre_condition: {pre!r} | post_condition: {post!r}')
    else:
        print(f'NOT CONFIRMED — pre_condition: {pre!r} | expected_pre: {expected_pre!r} | post_condition: {post!r} | expected_post: {expected_post!r}')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
