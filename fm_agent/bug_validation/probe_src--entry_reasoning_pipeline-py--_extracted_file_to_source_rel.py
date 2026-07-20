import sys
import os

# Add repo root to sys.path so the 'src' package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.entry_reasoning_pipeline import _entry_func_source_rel

    # Test: parent directory starts with a hyphen (e.g. '-loader' from source '.loader')
    # The FQN "proj::-loader::some_func" is split by "::" then joined to form a path.
    # extracted_rel = "proj/-loader/some_func"
    # func_dir = "proj/-loader", dir_name = "-loader", rfind('-') = 0
    # hyphen > 0 is False → source_base = '-loader'
    # Returns os.path.join("proj", "-loader") = "proj/-loader"
    # Spec says: when no hyphen after first character, return dir_name unchanged
    # with NO parent prefix → expected = "-loader"

    entry_func = "proj::-loader::some_func"

    actual = _entry_func_source_rel(entry_func)
    expected = '-loader'

    passed = actual != expected

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
