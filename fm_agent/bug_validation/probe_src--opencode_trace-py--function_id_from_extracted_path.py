import sys
try:
    from src.opencode_trace import function_id_from_extracted_path

    # Per spec: extension is "the shortest suffix beginning with the final '.' in the filename".
    # For '.hidden', the final '.' is at position 0 of the basename, so the extension is '.hidden'
    # and the basename should be empty.
    # os.path.splitext('.hidden') returns ('.hidden', '') — retaining the leading dot as part of the name.
    actual   = function_id_from_extracted_path("extracted_functions/src/.hidden")
    expected = "src::"

    passed   = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
