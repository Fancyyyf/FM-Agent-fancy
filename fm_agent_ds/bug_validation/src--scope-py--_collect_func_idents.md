# Bug Report: _collect_func_idents

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/scope-py/_collect_func_idents.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a triple (idents, body_words, exc_types). idents is a set of lowercase identifier strings collected from all Name nodes, Attribute attribute names, argument names, and alphanumeric substrings of length at least 3 within string constants appearing anywhere in the function body. body_words is a set of lowercase alphabetic word tokens of length at least 4 extracted from the text of every line spanned by the function body, excluding tokens that match a predefined stop-word set. exc_types is a set of lowercase exception-class names referenced as the raised exception type in raise statements or as the caught exception type in except clauses within the function body. All three returned sets may be empty.

---

### Actual Behavior

The function returns a tuple (idents, body_words, exc_types) without raising any exceptions and without modifying the inputs node or source_lines. The set idents contains the lowercased forms of: (a) all Name.id attributes of ast.Name nodes in the AST; (b) all Attribute.attr attributes of ast.Attribute nodes; (c) all arg.arg attributes of ast.arg nodes; (d) all words extracted via the regex r'[a-zA-Z_][a-zA-Z0-9_]{2,}' from string constants in the AST. The set exc_types contains the lowercased names of exception types collected from: (a) ast.Raise nodes that have an exc attribute: if exc is an ast.Call, the exc_node is exc.func, otherwise exc itself; if that exc_node is an ast.Name, its id is added, if it is an ast.Attribute, its attr is added; (b) ast.ExceptHandler nodes with a nonNone type attribute, where the type is treated analogously (if ast.Name, use id; if ast.Attribute, use attr). The set body_words contains the lowercased words of length at least 4 (matching r'\b([a-zA-Z]{4,})\b') found in the source text spanning from source_lines[node.lineno-1] to source_lines[node.end_lineno-1] inclusive, with any words present in the global _STOP set excluded.

---

## Code Evidence

Line 27:         elif isinstance(n, ast.ExceptHandler) and n.type:
Line 28:             exc_node = n.type
Line 29:             if isinstance(exc_node, ast.Name):
Line 30:                 exc_types.add(exc_node.id.lower())
Line 31:             elif isinstance(exc_node, ast.Attribute):
Line 32:                 exc_types.add(exc_node.attr.lower())

---

## Trigger Condition

The specification requires collecting all exception-class names referenced in except clauses. The code only handles single ast.Name or ast.Attribute nodes and does not recurse into ast.Tuple (or other compound types) when an except clause catches multiple exceptions (e.g., `except (ValueError, TypeError):`). Consequently, for such inputs the returned exc_types set is empty, violating the specification.

---

## How to trigger the bug

When a function contains an except clause that catches multiple exception types using a tuple (e.g., `except (ValueError, TypeError):`), the AST represents the exception type as an `ast.Tuple` node. The code only checks for `ast.Name` and `ast.Attribute` on the except handler's `type` attribute and does not traverse into `ast.Tuple.elts` to extract the individual exception names. As a result, all exception types in tuple-form except clauses are silently dropped from `exc_types`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `node` | AST `FunctionDef` node for a function containing `except (ValueError, TypeError):` and `except (OSError, IOError) as e:` and `except RuntimeError:` |
| `source_lines` | Source code lines for the test function |

### Expected (spec-correct) Output

`exc_types = {'valueerror', 'typeerror', 'oserror', 'ioerror', 'runtimeerror'}`

### Actual (buggy) Output

`exc_types = {'runtimeerror'}`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import ast
from src.scope import _collect_func_idents

code = """\
def test_func():
    try:
        pass
    except (ValueError, TypeError):
        pass
    except RuntimeError:
        pass
"""
tree = ast.parse(code)
func_node = tree.body[0]
source_lines = code.strip().split('\n')

_, _, exc_types = _collect_func_idents(func_node, source_lines)
print(exc_types)
# actual (buggy) output: {'runtimeerror'}
# expected (correct) output: {'valueerror', 'typeerror', 'runtimeerror'}
```

---

## Probe Script

```python
"""Probe script for bug ID: src--scope-py--_collect_func_idents

Tests whether _collect_func_idents correctly collects exception types from
ast.Tuple nodes in except clauses (e.g., except (ValueError, TypeError):).
"""

import ast
import os
import sys
import tempfile
from textwrap import dedent

# Use a temp directory for any probe-owned files to satisfy the self-validation guard
_PROBE_TMP = tempfile.mkdtemp(prefix="probe__collect_func_idents_")

try:
    # Ensure the repo root is on the path (run from repo root, per Step 2d)
    _cwd = os.getcwd()
    if _cwd not in sys.path:
        sys.path.insert(0, _cwd)

    from src.scope import _collect_func_idents

    # Create a test function AST with tuple except clauses
    code = dedent("""\
    def test_tuple_except():
        try:
            x = 1 / 0
        except (ValueError, TypeError):
            pass
        except (OSError, IOError) as e:
            pass
        except RuntimeError:
            pass
    """)

    tree = ast.parse(code)
    func_node = tree.body[0]

    source_lines = code.strip().split('\n')

    _idents, _body_words, exc_types = _collect_func_idents(func_node, source_lines)

    # The spec requires all caught exception types from except clauses.
    # The tuple-form except (ValueError, TypeError) should yield 'valueerror' and
    # 'typeerror'. RuntimeError (single Name) should work as expected.
    expected = {'valueerror', 'typeerror', 'oserror', 'ioerror', 'runtimeerror'}

    missing = expected - exc_types

    if missing:
        print(f'CONFIRMED — exc_types missing: {sorted(missing)} '
              f'| actual exc_types: {sorted(exc_types)}')
    else:
        print(f'NOT CONFIRMED — all expected exc types present: '
              f'{sorted(exc_types)}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    # Clean up temp directory
    try:
        os.rmdir(_PROBE_TMP)
    except OSError:
        pass
```

### Probe Output

```
CONFIRMED — exc_types missing: ['ioerror', 'oserror', 'typeerror', 'valueerror'] | actual exc_types: ['runtimeerror']
```
