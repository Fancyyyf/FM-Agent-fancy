"""Probe script for bug: _generic_func_info body_words regex misses non-ASCII alphabetic chars."""
import sys

try:
    from src.scope import _generic_func_info

    # Simulate a non-Python source file body containing:
    #   "word"  — all ASCII, 4 chars, should be in body_words
    #   "café"  — contains non-ASCII é, 4 chars, should be in body_words per spec
    source_lines = ["// function body with word and café"]
    name = "test_func"
    lang_cfg = {"keywords": {"if", "else", "for", "while", "return"}}

    result = _generic_func_info(name, start0=0, end0=0, source_lines=source_lines, lang_cfg=lang_cfg)

    body_words = result["body_words"]

    # Spec claim: body_words should contain all lowercased alphabetic words of length ≥ 4
    # "word" should be present (ASCII)
    # "café" should be present (non-ASCII é is still alphabetic)
    expected = {"word", "café"}
    actual = body_words

    # Bug confirmed if actual is missing "café" (the non-ASCII word)
    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {sorted(actual)} | expected: {sorted(expected)}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {sorted(actual)}")
