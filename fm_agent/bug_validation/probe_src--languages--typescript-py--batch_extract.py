"""
Probe script for bug: src--languages--typescript-py--batch_extract

The specification claims batch_extract returns only top-level function definitions,
but get_functions_by_file (which it delegates to) returns ALL functions/methods
including nested ones. This probe mocks CodeGraphExtractor to return both top-level
and nested functions, then verifies batch_extract does not filter to top-level only.
"""

import os
import sys

# Add repo root to path so 'src' package is importable
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, repo_root)

from unittest.mock import MagicMock, patch

bug_id = "src--languages--typescript-py--batch_extract"

try:
    from src.languages.typescript import batch_extract

    # Create a mock scenario: codegraph returns a TypeScript file with both
    # a top-level function and a nested function.
    mock_filepath = "/tmp/test_project/src/utils.ts"
    mock_functions = [
        # Top-level function
        ("exportData", "export function exportData(items: Item[]): string {\n  return JSON.stringify(items);\n}\n"),
        # Nested function (should NOT appear per spec)
        ("formatItem", "function formatItem(item: Item): string {\n  return item.name + ':' + item.value;\n}\n"),
    ]

    mock_cg = MagicMock()
    mock_cg.get_functions_by_file.return_value = {mock_filepath: mock_functions}

    with patch('src.languages.typescript.CodeGraphExtractor') as mock_cls:
        mock_cls.from_proj_dir.return_value = mock_cg

        actual = batch_extract("/tmp/test_project")

    actual_funcs = actual.get(mock_filepath, [])
    actual_names = [name for name, _ in actual_funcs]

    # Spec says: only top-level functions → expected names = ["exportData"]
    expected_names = ["exportData"]

    # Bug CONFIRMED if nested function "formatItem" leaks through
    has_nested = "formatItem" in actual_names
    has_top_level = "exportData" in actual_names

    if not has_top_level:
        print("NOT CONFIRMED — top-level function missing from results:", actual_names)
    elif has_nested:
        print(f"CONFIRMED — batch_extract returns nested functions (violates spec).")
        print(f"  Actual names:  {actual_names}")
        print(f"  Expected names: {expected_names}")
        print(f"  The nested function 'formatItem' should not appear per spec claim.")
    else:
        print(f"NOT CONFIRMED — only top-level functions returned as expected: {actual_names}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
