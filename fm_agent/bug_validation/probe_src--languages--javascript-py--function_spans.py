"""Probe script for bug src--languages--javascript-py--function_spans.

Tests whether function_spans violates its spec by returning an unsorted list
when the codegraph backend returns spans in non-ascending order.
"""

import sys
import os
from unittest.mock import MagicMock, patch

# The project root must be on sys.path so we can import src.languages.javascript
PROJECT_ROOT = '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot'
sys.path.insert(0, PROJECT_ROOT)

# --- Design the mock: get_function_spans returns spans out of order ---
UNSORTED_SPANS = [
    ("func_c", 40, 52),   # starts at line 40
    ("func_a", 5,  18),   # starts at line 5  — should be first
    ("func_b", 22, 35),   # starts at line 22
]

# Spec requires ascending start_idx: [("func_a",5,18), ("func_b",22,35), ("func_c",40,52)]

mock_cg = MagicMock()
mock_cg.get_function_spans.return_value = UNSORTED_SPANS

try:
    with patch(
        'src.languages.javascript.CodeGraphExtractor',
        autospec=True,
    ) as MockExtractorClass:
        MockExtractorClass.from_proj_dir.return_value = mock_cg

        from src.languages.javascript import function_spans

        result = function_spans('/fake/proj_dir', '/fake/file.js')

    # --- Evaluate ---
    expected = sorted(UNSORTED_SPANS, key=lambda t: t[1])  # order by start_idx

    if result != expected:
        print(f'CONFIRMED — actual: {result} | expected: {expected}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {result}')

except Exception as exc:
    print(f'ERROR: {exc}')
    sys.exit(1)
