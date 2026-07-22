import sys
try:
    from src.languages.erlang import _SourceIndex

    # Trigger condition: source contains a vertical tab (\v) which is NOT a newline
    # The specification requires line boundaries correspond only to newline chars,
    # but splitlines(keepends=True) also splits on \v, \f, \x85, etc.
    source = 'hello\vworld'
    idx = _SourceIndex.build(source)

    # Spec-correct: \v is not a newline → source should be 1 line
    # Buggy actual: splitlines(keepends=True) splits on \v → 2 lines
    expected_lines = 1  # 'hello\vworld' is a single line with no newline
    actual_lines = len(idx.lines)

    passed = actual_lines != expected_lines

    if passed:
        print(f'CONFIRMED — actual lines: {actual_lines!r} | expected lines: {expected_lines!r}')
        print(f'lines: {idx.lines!r}')
        print(f'line_offsets: {idx.line_offsets!r}')
        print(f'source: {source!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual_lines} lines')
        print(f'lines: {idx.lines!r}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
