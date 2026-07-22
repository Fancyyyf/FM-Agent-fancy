import sys
import os

# Probe runs from repo root; add cwd to path so src.languages.erlang resolves.
sys.path.insert(0, os.getcwd())

try:
    from src.languages.erlang import _source_for_range
except Exception as e:
    print(f'ERROR importing _source_for_range: {e}')
    sys.exit(1)

source = "hello"

# Trigger condition: start character 2 > end character 1 on the same line.
# start  = line 0, character 2   (byte offset 2 → points to 'l')
# end    = line 0, character 1   (byte offset 1 → points to 'e')
# start > end
lsp_range = {
    "start": {"line": 0, "character": 2},
    "end":   {"line": 0, "character": 1},
}

try:
    actual = _source_for_range(source, lsp_range)
except Exception as e:
    print(f'ERROR calling _source_for_range: {e}')
    sys.exit(1)

# Per spec: "Returns the substring of source that spans from the start
# position (inclusive) to the end position (exclusive)."
# When start offset 2 > end offset 1, the span from start to end is
# empty → expected ""
expected = ""

passed = actual != expected   # True  → the buggy output differs from spec
                              # False → actual matches spec

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
