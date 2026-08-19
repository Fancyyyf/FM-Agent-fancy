import sys
import os

# Add repo root to sys.path so we can import from src
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, repo_root)

try:
    from src.domain_knowledge import _flatten_paths

    # Test 1: non-string integers should NOT appear in output per spec,
    # but the code appends any truthy value
    result = _flatten_paths([1, 2, 3])
    expected_str_only = []  # spec says only strings; integers should be excluded
    bug_confirmed = result != expected_str_only

    if bug_confirmed:
        print(f"CONFIRMED — Test 1 passed: _flatten_paths([1, 2, 3]) returned {result!r} "
              f"but spec expects only strings ({expected_str_only!r})")
    else:
        print(f"NOT CONFIRMED — Test 1: _flatten_paths([1, 2, 3]) returned {result!r}, "
              f"matched expected {expected_str_only!r}")

    # Test 2: mixed types
    result2 = _flatten_paths(["a", 1, "b"])
    expected2 = ["a", "b"]  # only strings should remain
    bug_confirmed2 = result2 != expected2

    if bug_confirmed2:
        print(f"CONFIRMED — Test 2 passed: _flatten_paths(['a', 1, 'b']) returned {result2!r} "
              f"but spec expects only strings ({expected2!r})")
    else:
        print(f"NOT CONFIRMED — Test 2: returned {result2!r}, matched expected {expected2!r}")

    # Test 3: nested with integers
    result3 = _flatten_paths([[1, 2], "a"])
    expected3 = ["a"]  # only strings should remain
    bug_confirmed3 = result3 != expected3

    if bug_confirmed3:
        print(f"CONFIRMED — Test 3 passed: _flatten_paths([[1, 2], 'a']) returned {result3!r} "
              f"but spec expects only strings ({expected3!r})")
    else:
        print(f"NOT CONFIRMED — Test 3: returned {result3!r}, matched expected {expected3!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
