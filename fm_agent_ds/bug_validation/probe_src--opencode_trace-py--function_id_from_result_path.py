import sys
import os

# Ensure the repo root is on sys.path so 'src' is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

test_input = r"fm_agent\logic_verification_results\test.py"
expected = "fm_agent::logic_verification_results::test"

try:
    from src.opencode_trace import function_id_from_result_path

    actual = function_id_from_result_path(test_input)
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
