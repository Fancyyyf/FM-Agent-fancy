import sys
import os

# Ensure repo root is in sys.path for package import
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.generate_batch_prompts import _detect_comment_prefix
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Valid comment prefixes from the spec
VALID_PREFIXES = {'#', '//', '%', '--'}

# Trigger: content where [SPEC] is preceded by "hello" — NOT a valid comment prefix
content = "hello [SPEC]\n# Unit: test\nhello [SPEC]\n"

try:
    result = _detect_comment_prefix(content)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Per spec, the returned value should be a valid comment prefix (or None if none found).
# The bug: _detect_comment_prefix returns "hello" (not a valid prefix) without validation.
expected = None  # Per spec, non-comment text before [SPEC] should not be treated as a prefix
actual = result

# Bug is CONFIRMED if: result is non-None AND result is NOT a valid comment prefix
bug_confirmed = result is not None and result not in VALID_PREFIXES

if bug_confirmed:
    print(f'CONFIRMED — actual: {actual!r} | expected valid prefix or None; '
          f'_detect_comment_prefix returned invalid comment prefix "{actual}"')
else:
    print(f'NOT CONFIRMED — actual: {actual!r} | expected: {expected!r}')
