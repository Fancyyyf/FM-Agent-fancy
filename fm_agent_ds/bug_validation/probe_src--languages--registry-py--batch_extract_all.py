"""Probe for batch_extract_all bug: dict.update overwrites same-file-path entries from earlier languages."""
import sys
import tempfile
import os

try:
    from unittest.mock import patch
    from src.languages.registry import batch_extract_all, REGISTRY

    # Two mock handlers that both extract functions from the *same* file path.
    def mock_extract_lang_a(proj_dir):
        return {"/fake/shared.py": [("func_a", "def func_a(): pass")]}

    def mock_extract_lang_b(proj_dir):
        return {"/fake/shared.py": [("func_b", "def func_b(): pass")]}

    class MockHandler:
        def __init__(self, fn):
            self.batch_extract = fn

    mock_registry = {
        "lang_a": MockHandler(mock_extract_lang_a),
        "lang_b": MockHandler(mock_extract_lang_b),
    }

    # Clear original REGISTRY and replace with mock
    with patch.dict("src.languages.registry.REGISTRY", mock_registry, clear=True):
        funcs, langs = batch_extract_all("/tmp/dummy_proj_dir")

    # Specification: all functions from that file across all supported languages
    # should be present.  Actual: dict.update keeps only the last language's entries.
    expected = {"func_a", "func_b"}
    actual = {name for name, _ in funcs.get("/fake/shared.py", [])}

    # Bug confirmed when actual == only last language's func ("func_b"),
    # not the full expected set.
    bug_confirmed = actual != expected

    if bug_confirmed:
        print(f'CONFIRMED — actual: {sorted(actual)!r} | expected: {sorted(expected)!r} '
              f'(dict.update dropped functions from earlier language)')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {sorted(actual)!r}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
