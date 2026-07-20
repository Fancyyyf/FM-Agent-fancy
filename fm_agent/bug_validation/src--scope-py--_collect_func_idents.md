# Bug Report: _collect_func_idents

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/scope-py/_collect_func_idents.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a 3tuple (idents, body_words, exc_types) where each element is a
    set[str] whose members are lowercased. No returned set contains the empty string.
  - idents contains every identifier whose value is read at least once within the
    function body. An identifier whose value is read includes: any name resolved as a
    value (Load context), the attribute name in any attributeaccess expression, and
    any functionparameter name that appears in the body in a value position.
    Identifiers that only appear in write (Store) or deletion (Del) contexts are
    excluded.
  - body_words contains every distinct alphabetic word of at least 3 characters that
    appears in the source text spanning from the function's first line through its
    last line (inclusive), after excluding any word whose text originates inside a
    comment, a string literal, or the docstring of the function.
  - exc_types contains every exception type name that is either raised (via a raise
    statement with a named exception instance or class), caught (via an except clause
    that names a type), or otherwise referenced as an exception class anywhere within
    the function body.

---

### Actual Behavior

After execution, the function returns a tuple (idents, body_words, exc_types) such that:

- idents = {s.lower() | n  ast.walk(node), (s = n.id if isinstance(n, ast.Name)) or (s = n.attr if isinstance(n, ast.Attribute)) or (s = n.arg if isinstance(n, ast.arg)) or (isinstance(n, ast.Constant) and isinstance(n.value, str) and s  re.findall(r'[a-zA-Z_][a-zA-Z0-9_]{2,}', n.value))}
- exc_types = {e.lower() | n  ast.walk(node), ((isinstance(n, ast.Raise) and n.exc != None and (let exc_ref = n.exc.func if isinstance(n.exc, ast.Call) else n.exc in (e = exc_ref.id if isinstance(exc_ref, ast.Name)) or (e = exc_ref.attr if isinstance(exc_ref, ast.Attribute)))) or (isinstance(n, ast.ExceptHandler) and n.type != None and ((e = n.type.id if isinstance(n.type, ast.Name)) or (e = n.type.attr if isinstance(n.type, ast.Attribute))))}
- body_words = {w | w  re.findall(r'\b([a-zA-Z]{4,})\b', body_text.lower()) and w  _STOP} where body_text = '\n'.join(source_lines[node.lineno - 1 : node.end_lineno])

Inputs `node` and `source_lines` are not modified, and the function raises no exceptions.

---

## Code Evidence

Line 34: body_words = {w for w in re.findall(r'\b([a-zA-Z]{4,})\b', body_text.lower())

---

## Trigger Condition

The specification requires body_words to contain every distinct alphabetic word of at least 3 characters (after exclusions). The regex uses {4,} so a 3-letter word like 'bar' is omitted from body_words.

---

## How to trigger the bug

The `_collect_func_idents` function builds `body_words` by extracting alphabetic words from the function's source body text. The regex `r'\b([a-zA-Z]{4,})\b'` on line 304 of `src/scope.py` uses a minimum of 4 characters, while the specification requires a minimum of 3 characters. As a result, any 3-letter alphabetic word in the function body is silently excluded from `body_words`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `node` | `ast.FunctionDef` representing `def dummy_func():\n    x = bar + baz\n` |
| `source_lines` | `['def dummy_func():', '    x = bar + baz', '']` |

### Expected (spec-correct) Output

`body_words` should contain `{'bar', 'baz'}` (both are 3-letter alphabetic words, ≥3 chars as spec requires)

### Actual (buggy) Output

`body_words` is `set()` (empty) — neither "bar" nor "baz" are included because the regex `{4,}` requires at least 4 characters

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import ast
from src import scope

source = "def dummy_func():\n    x = bar + baz\n"
tree = ast.parse(source)
func_node = tree.body[0]
source_lines = source.splitlines()

idents, body_words, exc_types = scope._collect_func_idents(func_node, source_lines)

# body_words should contain 'bar' and 'baz' (≥3 chars per spec)
# but buggy regex {4,} excludes them → body_words is empty
print(body_words)  # actual (buggy) output: set()
# expected (correct) output: {'bar', 'baz'}
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — 3-letter word "bar" not in body_words (spec requires ≥3 chars, regex uses ≥4).
  body_words: []
  "bar" present: False
  "baz" present: False
  idents: ['bar', 'baz', 'x']
```
