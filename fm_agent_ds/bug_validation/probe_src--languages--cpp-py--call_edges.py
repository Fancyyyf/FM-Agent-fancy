import os
import sys

# Repo root is 3 levels up from fm_agent/bug_validation/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import patch

try:
    from src.languages.codegraph import CodeGraphExtractor

    # Simulate: from_proj_dir returns a valid extractor (init succeeds),
    # but get_call_edges returns None (e.g. C++ not indexed / DB missing cpp tables).
    # The spec says: when init succeeds, return a dict. The code passes through
    # whatever get_call_edges returns, which could be None.
    with patch.object(CodeGraphExtractor, 'get_call_edges', return_value=None):
        with patch.object(CodeGraphExtractor, 'from_proj_dir', return_value=CodeGraphExtractor.__new__(CodeGraphExtractor)):
            from src.languages.cpp import call_edges
            result = call_edges('/tmp/fake_proj')

    # Spec-correct behavior: when CodeGraph init succeeds, must return a dict
    expected = {}  # Safe default when no cpp edges exist
    # Buggy behavior: returns None because get_call_edges returned None
    passed = result is None

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {result!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {result!r}')
