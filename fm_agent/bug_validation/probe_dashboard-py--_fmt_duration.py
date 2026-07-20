import sys
import os
import math

# Ensure the repo root is on the path so `import dashboard` works
# probe is at fm_agent/bug_validation/ — go up 3 levels to repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from dashboard import _fmt_duration

    # Trigger input: negative seconds where int() and math.floor() diverge.
    # int(-1.2) = -1, but floor(-1.2) = -2.
    actual = _fmt_duration(-1.2)

    # Spec-correct behavior (using math.floor as the spec requires):
    # floor(-1.2) = -2, which is < 60, so just the bare second segment.
    expected = f"{math.floor(-1.2)}s"   # '-2s'

    passed = actual != expected
    if passed:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
