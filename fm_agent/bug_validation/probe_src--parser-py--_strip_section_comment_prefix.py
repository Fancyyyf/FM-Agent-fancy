import sys
import re
sys.path.insert(0, '.')

try:
    from src.parser import _strip_section_comment_prefix
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Correct regex per spec: one or more of each comment char (not two+ for / and -)
_correct_re = re.compile(r'^(\s*)(?:/+|#+|-+|%+)\s?')

tests = [
    (" / comment", " / comment"),
    (" - comment", " - comment"),
]

any_confirmed = False
for line, label in tests:
    actual = _strip_section_comment_prefix(line)
    expected = _correct_re.sub(r'\1', line)

    if actual != expected:
        any_confirmed = True
        print(f'CONFIRMED ({label}): actual={actual!r} | expected={expected!r}')
    else:
        print(f'NOT CONFIRMED ({label}): actual matched expected: {actual!r}')

if not any_confirmed:
    print('NOT CONFIRMED — all inputs matched expected output')
