"""Probe script for src--reasoner-py--_split_into_blocks bug validation.

Bug: _split_into_blocks calls func.strip() before splitting, which removes
leading/trailing whitespace including newlines. The spec claims that concatenation
of all returned blocks reconstructs the original func, but stripping violates this.
"""
import os
import sys

# Ensure repo root is on sys.path for package imports
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.reasoner import _split_into_blocks
except Exception as e:
    print(f"ERROR: Failed to import _split_into_blocks: {e}", file=sys.stderr)
    sys.exit(1)

# Trigger condition: input with leading and trailing newlines
func_with_whitespace = "\n\nline1\nline2\n\n"
expected_concat = func_with_whitespace  # spec says concatenation must reconstruct original

try:
    blocks = _split_into_blocks(func_with_whitespace)
    actual_concat = "".join(blocks)
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

# Bug is confirmed if the concatenated result does NOT match the original input
passed = actual_concat != expected_concat

if passed:
    print(f"CONFIRMED — actual: {actual_concat!r} | expected: {expected_concat!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual_concat!r}")
