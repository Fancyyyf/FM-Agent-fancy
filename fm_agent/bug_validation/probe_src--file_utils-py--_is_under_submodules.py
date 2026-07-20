import sys
try:
    from src.file_utils import _is_under_submodules

    # Trigger: path with multiple './' prefixes
    # Spec says: strip './' once → './sub/file' → does NOT match 'sub/' → False
    # Buggy code: strips ALL './' in a loop → 'sub/file' → matches 'sub/' → True
    actual = _is_under_submodules("././sub/file", ["sub"])
    expected = False  # spec-correct: single-strip gives "./sub/file" which doesn't start with "sub/"

    passed = actual != expected  # True if bug is reproduced (actual=True but expected=False)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
