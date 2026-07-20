import ast
import sys
import os

# Ensure we import from the package root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src import scope

    # Build a minimal AST for a function whose body contains a 3-letter word.
    # The spec says body_words must include words of at least 3 characters.
    # The buggy regex uses {4,} so 3-letter words like "bar" are excluded.
    source = """\
def dummy_func():
    x = bar + baz
"""
    tree = ast.parse(source)
    func_node = tree.body[0]  # ast.FunctionDef
    source_lines = source.splitlines()

    idents, body_words, exc_types = scope._collect_func_idents(func_node, source_lines)

    # Spec says "bar" must be in body_words (≥3 chars).
    # Buggy code excludes "bar" because regex uses {4,}.
    expected_in = 'bar'
    actual_has_bar = expected_in in body_words

    # Also check that "baz" is included (it's 3 letters too)
    actual_has_baz = 'baz' in body_words

    # CONFIRMED = the bug exists: "bar" and "baz" are NOT in body_words
    # when the spec says they should be (words ≥ 3 characters).
    bug_confirmed = not actual_has_bar

    if bug_confirmed:
        print(f'CONFIRMED — 3-letter word "bar" not in body_words (spec requires ≥3 chars, regex uses ≥4).')
        print(f'  body_words: {sorted(body_words)}')
        print(f'  "bar" present: {actual_has_bar}')
        print(f'  "baz" present: {actual_has_baz}')
        print(f'  idents: {sorted(idents)}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: body_words={sorted(body_words)}')

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
    sys.exit(1)
