import sys
import os

# Add workspace root to path so `src` is importable
_workspace = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _workspace not in sys.path:
    sys.path.insert(0, _workspace)

try:
    from src.languages.erlang import _symbol_line_span

    # Trigger condition: character=0.5 (a non-zero float).
    # The code uses int(character) which truncates 0.5 to 0, so it
    # erroneously treats character as zero and subtracts 1 from end.
    # Spec says non-zero character → end should be the raw end line (no subtraction).
    symbol_range = {
        "start": {"line": 0},
        "end":   {"line": 2, "character": 0.5},
    }
    actual   = _symbol_line_span(symbol_range)
    expected = (0, 2)  # spec-correct: end=2 because character is non-zero
    passed   = actual != expected

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
