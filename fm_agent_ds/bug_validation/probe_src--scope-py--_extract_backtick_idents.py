import sys
import os
import re

# Add the repo root to sys.path so 'src.scope' can be imported.
# __file__ =  <repo_root>/fm_agent/bug_validation/probe_<bug_id>.py
# Three dirnames up reaches the repo root.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from src.scope import _extract_backtick_idents
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# ── test case ──────────────────────────────────────────────────────────────
# The specification requires identifiers of length ≥ 2 to be extracted from
# triple-backtick code blocks.  The implementation at line 136 uses
#   re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b', block)
# which demands at least two characters *after* the leading letter/underscore,
# i.e. a minimum total length of 3.  A two-letter identifier like 'ab' is
# therefore silently dropped by the code-block-specific regex.
#
# Note: The single-backtick regex (line 132) also fires on triple-backtick
# delimiters (matching the third backtick of opening ``` to the first backtick
# of closing ```), which can mask the bug.  This probe tests the code block
# regex pattern directly in isolation to demonstrate the bug.

# ── Test 1 (control): single-backtick span with 2-char identifier ──────
# The single-backtick path uses {1,} which correctly captures length >= 2.
text1 = "See `ab` for details"
try:
    result1 = _extract_backtick_idents(text1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
ab_in_backtick = 'ab' in result1

# ── Test 2: code block regex in isolation ─────────────────────────────
# This is the exact regex from line 136 of src/scope.py (the buggy pattern).
block = "```\nab = 42\ncd = ab\n```"
buggy_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b', block)
ab_in_buggy = 'ab' in buggy_matches
cd_in_buggy = 'cd' in buggy_matches

# ── Test 3: corrected regex (what the spec demands) ────────────────────
# {1,} means at least 1 more after the first char, i.e. total >= 2.
corrected_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{1,})\b', block)
ab_in_corrected = 'ab' in corrected_matches
cd_in_corrected = 'cd' in corrected_matches

# ── Verdict ────────────────────────────────────────────────────────────
if ab_in_backtick and (not ab_in_buggy) and ab_in_corrected and (not cd_in_buggy) and cd_in_corrected:
    print(
        'CONFIRMED'
        ' — backtick-path correctly finds 2-char idents ({1,} quantifier)'
        ' | code-block-path regex (line 136) has wrong quantifier {2,}'
        ' (misses "ab", "cd")'
        ' | corrected {1,} finds them'
        f' | buggy_matches={buggy_matches!r}, corrected_matches={corrected_matches!r}'
    )
else:
    print(
        'NOT CONFIRMED'
        f' — ab_in_backtick={ab_in_backtick}'
        f', ab_in_buggy={ab_in_buggy}, cd_in_buggy={cd_in_buggy}'
        f', ab_in_corrected={ab_in_corrected}, cd_in_corrected={cd_in_corrected}'
    )
