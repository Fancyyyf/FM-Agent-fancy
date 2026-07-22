import sys
import os

# Add the repo root to sys.path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.entry_reasoning_pipeline import _extracted_file_to_source_rel

    # Trigger: a path where a directory component starts with a hyphen
    # e.g., "-cpp/func.cpp" — the component "-cpp" has hyphen at index 0,
    # so "hyphen > 0" is False and the loop skips it.
    input_path = "-cpp" + os.sep + "func.cpp"
    actual = _extracted_file_to_source_rel(input_path)

    # Per spec: "-cpp" should be recognized as extraction dir,
    # producing empty base + ".cpp" => ".cpp"
    expected = ".cpp"

    # Bug is reproduced if actual != expected
    passed = actual != expected

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
