import sys
import os

# Ensure the repo root is on sys.path so that 'import dashboard' works.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    import dashboard
    actual   = dashboard._price_for('/ai21.j2-mid-v1')
    expected = None   # spec says unrecognized model (no provider prefix) → None
    passed   = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
