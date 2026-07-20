import sys
import os
import tempfile

# Ensure repo root is on the path so `src.extract` resolves
_PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJ_ROOT not in sys.path:
    sys.path.insert(0, _PROJ_ROOT)

try:
    from src.extract import extract_functions_from_file

    # Create a temporary Python file with the bug-triggering code.
    # The function header continuation line "b): return 42" has the same
    # indentation as "def" but does NOT start with ')' after lstrip,
    # so the regex r'\)\s*(:|->)' fails to recognise it as a continuation.
    buggy_code = "def foo(a,\nb): return 42\n"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(buggy_code)
        tmp_path = f.name

    try:
        result = extract_functions_from_file(tmp_path, 'python')

        if len(result) == 0:
            print(f'CONFIRMED — extract_functions_from_file returned empty list for valid function')
        elif len(result) != 1:
            print(f'CONFIRMED — expected 1 function but got {len(result)}: {result}')
        else:
            name, source = result[0]
            # Spec-correct behaviour: the span should include the continuation
            # line "b): return 42" and thus contain "return 42".
            if 'return 42' in source:
                print(f'NOT CONFIRMED — function body correctly included return 42 in source: {source!r}')
            else:
                print(f'CONFIRMED — function body truncated; "return 42" missing. Got: {source!r}')
    finally:
        os.unlink(tmp_path)

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
    sys.exit(1)
