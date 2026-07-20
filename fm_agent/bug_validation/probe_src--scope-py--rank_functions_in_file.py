import sys
import os
import tempfile
from pathlib import Path

# Add snapshot root to sys.path so `from src.scope import ...` resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.scope import rank_functions_in_file

    # Create a temporary Python file with a simple parseable function
    tmp = tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False)
    tmp.write("def hello():\n    return 'world'\n")
    tmp.close()
    src_path = Path(tmp.name)

    # Build minimal signals dict (all keys required by the spec)
    signals = {
        'traceback_funcs': set(),
        'backtick_idents': set(),
        'dotted_refs': set(),
        'dotted_classes': set(),
        'plain_idents': {'hello'},
        'exception_types': set(),
        'all_words': {'hello'},
    }

    actual = rank_functions_in_file(
        filepath='test_file.py',
        src_path=src_path,
        issue='test issue about hello',
        signals=signals,
        top_k=5,
    )

    # Spec requires a list of dicts. Bug claims code returns None instead.
    expected_type = list
    passed = not isinstance(actual, expected_type)  # True → bug reproduced

    if passed:
        print(f'CONFIRMED — actual: {type(actual).__name__} ({actual!r}) | expected: list')
    else:
        print(f'NOT CONFIRMED — actual matched expected type list: {actual!r}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    try:
        os.unlink(tmp.name)
    except (NameError, OSError):
        pass
