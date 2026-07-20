import sys
import tempfile
import os

try:
    from src.extract import extract_functions_from_file

    # Minimal C++ source containing operator, overloading — the comma operator
    cpp_source = 'class Foo {\npublic:\n  void operator,(int a, int b) { }\n};\n'

    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write(cpp_source)
        tmp_path = f.name

    try:
        funcs = extract_functions_from_file(tmp_path, 'cpp')

        # spec-claim: the comma operator signature should be recognized and
        # the full operator token 'operator,' returned as the function name.
        # actual (buggy): _extract_func_name_brace returns None because the
        # regex character class misses ','; the function is skipped entirely.
        actual = len(funcs)
        expected = 1

        passed = actual != expected

        if passed:
            print(f'CONFIRMED — actual extracted count: {actual} | expected: {expected}')
        else:
            print(f'NOT CONFIRMED — actual matched expected: {actual} function(s) extracted')
    finally:
        os.unlink(tmp_path)

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
