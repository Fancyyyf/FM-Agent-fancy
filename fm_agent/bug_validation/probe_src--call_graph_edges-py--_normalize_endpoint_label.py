import sys
sys.path.insert(0, '.')

try:
    from src.call_graph_edges import normalize_fqn_label
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# The spec says: strip only the leading "./" sequence, then exclude "." and
# empty parent-directory components.  ".." is a valid parent-directory ref and
# should be PRESERVED.
# The code uses lstrip("./") which strips ALL leading '.' and '/' chars
# individually, destroying "../" prefixes.
test_cases = [
    # (input, expected per spec)
    ("../src/test.c::func",       "..::src::test-c::func"),
    ("./src/test.c::func",        "src::test-c::func"),
    ("src/test.c::func",          "src::test-c::func"),
    ("../../lib/util.h::do_work", "..::..::lib::util-h::do_work"),
]

confirmed = False
for label, expected in test_cases:
    try:
        actual = normalize_fqn_label(label)
    except Exception as e:
        print(f'ERROR on input {label!r}: {e}')
        sys.exit(1)

    if actual != expected:
        print(f'CONFIRMED — input: {label!r} | actual: {actual!r} | expected: {expected!r}')
        confirmed = True
        break

if not confirmed:
    print('NOT CONFIRMED — all outputs matched expected')
