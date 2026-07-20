import sys
sys.path.insert(0, '.')

try:
    from src.scope import _score_class

    # Class with non-ASCII word in docstring: "naive" (5 chars, contains 'i' = U+00EF)
    # The regex r'\b([a-zA-Z]{4,})\b' on line 364 only matches ASCII [a-zA-Z],
    # so it will NOT extract "naive" despite it being alphabetic (isalpha()=True)
    cls = {
        'name': 'TestClass',
        'docstring': 'Handles naïve encoding and decoding',
    }

    # signals with "naive" explicitly in all_words (spec allows any alphabetic token)
    signals = {
        'backtick_idents': set(),
        'plain_idents': set(),
        'all_words': {'naïve'},
        'dotted_classes': set(),
    }

    actual = _score_class(cls, signals)

    # Per spec: each matching docstring token (alphabetic, >=4 chars, not stop word)
    # that intersects all_words adds W_CLASS_DOC_MATCH (2.0) per match.
    # "naive" is 5 chars, alphabetic (Python str.isalpha() = True), NOT in _STOP.
    # Expected: 2.0 (one token x W_CLASS_DOC_MATCH)
    # Actual:   0.0 (regex fails to capture non-ASCII characters)
    expected = 2.0

    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED - actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED - actual matched expected: {actual!r}')
