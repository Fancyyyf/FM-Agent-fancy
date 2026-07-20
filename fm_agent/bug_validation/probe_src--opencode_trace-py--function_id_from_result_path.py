import sys
import os

# Add repo root to path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.opencode_trace import function_id_from_result_path

    # Trigger condition: dot-file in path where os.path.splitext fails to strip
    # the extension because the leading dot is treated as part of the basename.
    # Input: 'fm_agent/logic_verification_results/folder/.hidden'
    # Actual (buggy): 'folder::.hidden' (splitext returns ('folder/.hidden', ''))
    # Expected (spec): 'folder::' (final segment .hidden stripped entirely from last '.')
    test_input = "fm_agent/logic_verification_results/folder/.hidden"
    actual = function_id_from_result_path(test_input)
    expected = "folder::"
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
