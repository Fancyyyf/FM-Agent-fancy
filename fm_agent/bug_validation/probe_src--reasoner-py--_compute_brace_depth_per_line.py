"""
Probe script for bug: src--reasoner-py--_compute_brace_depth_per_line
Bug: _compute_brace_depth_per_line does not carry block-comment state across
     lines. Braces inside a multi-line block comment (/* ... */) are miscounted.

Spec claim: Braces inside block comments spanning multiple lines must be excluded.
Actual behavior: Each line is processed independently; block comment state resets
                 per line, so braces in a multi-line comment are counted.

This probe exercises the bug by passing lines containing a multi-line block
comment with a brace inside it. The spec requires depth [0,0,0] (all braces
excluded), but the buggy code produces [0,1,1] (brace counted on line 1).
"""

import sys
import os

# Make repo root importable
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.reasoner import _compute_brace_depth_per_line
except ImportError as e:
    print(f"ERROR: Failed to import _compute_brace_depth_per_line: {e}")
    sys.exit(1)

# ── Test: multi-line block comment containing a brace ──
# Lines: "/*" (comment start), "{" (brace inside comment), "*/" (comment end)
# Spec says the brace on line 1 must be excluded because it's inside the comment.
lines = [
    "/*",
    "{",
    "*/",
]

# Expected (per spec): depth stays 0 throughout — the brace is in a comment
expected = [0, 0, 0]

try:
    actual = _compute_brace_depth_per_line(lines)
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual} | expected: {expected}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual}")
