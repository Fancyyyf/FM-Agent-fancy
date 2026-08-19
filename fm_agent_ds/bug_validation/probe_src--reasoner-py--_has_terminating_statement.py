import sys
import os

# Add repo root to path so we can import src.* modules
repo_root = os.path.abspath(os.path.dirname(__file__) + "/../..")
sys.path.insert(0, repo_root)

try:
    from src.reasoner import _has_terminating_statement
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Bug: default regex on line 175 omits 'break' and 'continue'.
# For any language not in _TERMINATING_PATTERNS, a block containing
# only 'break' or 'continue' causes the function to return False
# instead of the spec-required True.

language = "zig"  # not in _TERMINATING_PATTERNS → uses default regex
bug_found = False

# Test 1: break should be detected as a terminating statement
actual_break = _has_terminating_statement("break", language)
expected_break = True
if actual_break != expected_break:
    print(f"BUG: break not detected — actual: {actual_break!r}, expected: {expected_break!r}")
    bug_found = True

# Test 2: continue should be detected as a terminating statement
actual_continue = _has_terminating_statement("continue", language)
expected_continue = True
if actual_continue != expected_continue:
    print(f"BUG: continue not detected — actual: {actual_continue!r}, expected: {expected_continue!r}")
    bug_found = True

# Sanity check: return still works correctly
actual_return = _has_terminating_statement("return x", language)
if not actual_return:
    print("ERROR: return not detected — function is broken")
    sys.exit(1)

if bug_found:
    print("CONFIRMED")
else:
    print("NOT CONFIRMED")
