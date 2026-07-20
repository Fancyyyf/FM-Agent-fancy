import sys
sys.path.insert(0, '.')
try:
    from src.scope import _base_score

    # Construct inputs that trigger the W_BACKTICK_BODY bug.
    # The spec only permits name-component ↔ backtick_idents intersections (T2).
    # The buggy code also adds body-ident ↔ backtick_idents (T2b), which contributes
    # W_BACKTICK_BODY * |idents ∩ backtick_idents| = 2.0 * 2 = 4.0.
    #
    # We choose a name with zero overlap with any signal category, and idents that
    # DO overlap with backtick_idents. All other signal categories are empty so
    # every permitted intersection is zero. The spec requires 0.0;
    # the buggy code returns > 0.0.

    name = "foo"
    idents = {"parse", "token"}
    body_words = set()
    exc_types = set()
    body_lines = 10
    signals = {
        'traceback_funcs': set(),
        'backtick_idents': {"parse", "token"},
        'dotted_refs': set(),
        'plain_idents': set(),
        'all_words': set(),
        'exception_types': set(),
    }

    actual = _base_score(name, idents, body_words, exc_types, body_lines, signals)
    expected = 0.0  # spec-correct: no permitted category has any overlap

    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
