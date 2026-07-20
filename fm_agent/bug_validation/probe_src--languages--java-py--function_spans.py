import sys
sys.path.insert(0, '.')
from unittest.mock import MagicMock, patch

try:
    from src.languages.java import function_spans
except Exception as e:
    print(f'ERROR: import failed: {e}')
    sys.exit(1)

# Mock CodeGraphExtractor to return UNORDERED function spans.
# func_b starts at line 30 (index 29), func_a starts at line 10 (index 9).
# If function_spans properly orders by appearance, it would return [(func_a, 9, 19), (func_b, 29, 39)].
# If it delegates without sorting (the bug), it returns the mock's order: [(func_b, 29, 39), (func_a, 9, 19)].

mock_cg = MagicMock()
mock_cg.get_function_spans.return_value = [
    ("func_b", 29, 39),  # starts later, appears first (unordered)
    ("func_a", 9,  19),  # starts earlier, appears second (unordered)
]

spec_expected = [
    ("func_a", 9,  19),  # ordered by start_idx: 9 < 29
    ("func_b", 29, 39),
]

try:
    with patch('src.languages.java.CodeGraphExtractor') as mock_extractor:
        mock_extractor.from_proj_dir.return_value = mock_cg
        actual = function_spans("/fake/proj", "/fake/File.java")
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Bug reproduced if actual matches the mock's unordered output (no sorting applied).
bug_present = actual == mock_cg.get_function_spans.return_value
spec_correct = actual == spec_expected

if bug_present:
    print(f'CONFIRMED — function_spans does NOT order by appearance.')
    print(f'  actual (unordered, matches mock):  {actual}')
    print(f'  expected (spec-ordered):           {spec_expected}')
elif spec_correct:
    print(f'NOT CONFIRMED — function_spans correctly orders by appearance.')
    print(f'  actual: {actual}')
else:
    print(f'NOT CONFIRMED — unexpected ordering.')
    print(f'  actual: {actual}')
    print(f'  expected (spec-ordered): {spec_expected}')
