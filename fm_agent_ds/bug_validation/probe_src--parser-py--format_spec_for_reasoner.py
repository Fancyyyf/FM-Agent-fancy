import sys
import os

# Ensure the repo root is on sys.path for package import
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.parser import format_spec_for_reasoner
except Exception as e:
    print(f"ERROR: Could not import src.parser: {e}")
    sys.exit(1)

try:
    # Trigger condition: spec values ending with newline
    spec = {
        'signature': 'def foo(x: int) -> int:\n',
        'pre_condition': 'x > 0\n',
        'post_condition': 'Returns x + 1\n'
    }

    actual = format_spec_for_reasoner(spec)

    # Spec-correct: exactly one blank line between adjacent sections
    expected = (
        "def foo(x: int) -> int:\n"
        "\n"
        "Pre-condition:\n"
        "x > 0\n"
        "\n"
        "Post-condition:\n"
        "Returns x + 1\n"
    )

    # Bug confirmed if actual (double blank lines) differs from expected (single blank line)
    passed = actual != expected

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
