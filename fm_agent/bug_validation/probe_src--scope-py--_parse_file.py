import sys
import os
from pathlib import Path

# Add snapshot root to sys.path so `from src.scope import rank_functions_in_file` resolves
# The probe script is at fm_agent/bug_validation/probe_...py, so go up 3 levels to reach the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.scope import rank_functions_in_file

    # Use a non-existent .py file with a valid recognized extension
    src_path = Path('/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/nonexistent_12345_test.py')

    # Verify the file does NOT exist
    assert not src_path.exists(), f"Test file unexpectedly exists: {src_path}"

    # Build minimal signals dict
    signals = {
        'traceback_funcs': set(),
        'backtick_idents': set(),
        'dotted_refs': set(),
        'dotted_classes': set(),
        'plain_idents': set(),
        'exception_types': set(),
        'all_words': set(),
    }

    # Spec says: for a non-existent file with recognized extension,
    # the function should return (None, None, None) internally,
    # and rank_functions_in_file should return [] gracefully.
    # Bug claims: FileNotFoundError is raised instead.
    actual = rank_functions_in_file(
        filepath='test_nonexistent.py',
        src_path=src_path,
        issue='test issue',
        signals=signals,
        top_k=5,
    )

    # Spec requires: when _parse_file returns (None, None, None),
    # rank_functions_in_file returns [] (empty list).
    expected = []

    passed = actual != expected  # True → bug reproduced (unexpected output or exception)

    if passed:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

except FileNotFoundError:
    print('CONFIRMED — FileNotFoundError raised instead of returning (None, None, None)')
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
