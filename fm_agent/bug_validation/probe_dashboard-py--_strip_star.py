import sys
import os

# Ensure the repo root is on the path so `import dashboard` works
# probe is at fm_agent/bug_validation/ — go up 3 levels to repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from dashboard import _strip_star

    d = {42: 'test'}
    expected = {42: 'test'}   # spec-correct: non-string key unchanged, no crash

    try:
        actual = _strip_star(d)
        # If we got here, no exception was raised — unexpected for the buggy code
        passed = actual != expected
        if passed:
            print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
        else:
            print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
    except AttributeError:
        # The bug: k.startswith('*') fails on non-string keys like int
        actual = 'AttributeError raised'
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
