# Bug Report: _extract_classes

**Source file:** `src/scope-py/_extract_classes.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of dicts, one per class definition that appears as a direct child of the module body (not nested inside another class definition). Each dict contains at minimum: 'name' (non-empty string, the class identifier as written in source), 'docstring' (string, the class-level docstring extracted from the first expression statement in the class body, or the empty string when no docstring is present), and 'method_linenos' (list of positive ints, each a 1-indexed line number where a FunctionDef or AsyncFunctionDef node starts within the class body). The list is empty when the module contains no top-level class definitions. The function does not modify tree or source_lines.

---

### Actual Behavior

Post-condition in natural language:
The function returns a list `classes` containing one dictionary per `ast.ClassDef` node in the AST tree `tree`. Each dictionary has the following keys:
- 'name': the name attribute of the ClassDef node (string).
- 'lineno': the starting line number of the class definition (integer).
- 'end_lineno': the ending line number of the class definition (integer).
- 'docstring': the docstring of the class as returned by `ast.get_docstring`, or an empty string if no docstring.
- 'method_linenos': a list of integers representing the line numbers of all FunctionDef and AsyncFunctionDef nodes that are descendants of this class node, in no specified order (effectively the order yielded by `ast.walk` over the class node). These include nested functions inside methods.
The order of the dictionaries in the returned list is unspecified (depends on `ast.walk` order). The argument `source_lines` is not accessed in the function body and thus does not affect the result.

Formal logic:
Let Classes = { n | n ∈ walk(tree) ∧ isinstance(n, ClassDef) } where walk denotes ast.walk.
Then classes is a list such that:
- length(classes) = |Classes|
- There exists a bijective mapping from classes to Classes such that for each d in classes and corresponding c in Classes:
  - d['name'] = c.name
  - d['lineno'] = c.lineno
  - d['end_lineno'] = c.end_lineno
  - d['docstring'] = (ast.get_docstring(c) or '')
  - d['method_linenos'] = [ f.lineno | f ∈ walk(c) ∧ isinstance(f, (FunctionDef, AsyncFunctionDef)) ]
No exceptions are raised, no side effects occur, and source_lines remains unchanged.

---

## Code Evidence

Line 8: for node in ast.walk(tree):
Line 9: if not isinstance(node, ast.ClassDef):
Line 10: continue

---

## Trigger Condition

The code iterates over all ClassDef nodes in the entire AST (via ast.walk), including nested classes, whereas the specification restricts the output to class definitions that are direct children of the module body. A module with both a top-level and a nested class will cause extra entries.

---

## How to trigger the bug

The function uses `ast.walk(tree)` to iterate over all nodes in the AST, which traverses the entire tree recursively. This means nested class definitions (classes defined inside another class body) are also collected, violating the specification that only direct children of the module body should be returned. The correct implementation should iterate over `tree.body` directly and filter for `ast.ClassDef` nodes.

### Inputs

| Parameter | Value |
|-----------|-------|
| `tree` | AST of a Python module containing both top-level classes (`TopLevel`, `Outer`) and a nested class (`Inner` inside `Outer`) |
| `source_lines` | Source code split into lines |

### Expected (spec-correct) Output

`[{'name': 'TopLevel', ...}, {'name': 'Outer', ...}]` — only the two top-level classes

### Actual (buggy) Output

`[{'name': 'TopLevel', ...}, {'name': 'Outer', ...}, {'name': 'Inner', ...}]` — includes the nested class `Inner`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import ast
from src.scope import _extract_classes

source = """
class TopLevel:
    '''Docstring for TopLevel'''
    pass

class Outer:
    '''Docstring for Outer'''
    class Inner:
        '''Nested class — should NOT appear'''
        pass
    def method(self):
        pass
"""

tree = ast.parse(source)
result = _extract_classes(tree, source.splitlines(keepends=True))
names = [d['name'] for d in result]
print(names)
# actual (buggy) output: ['TopLevel', 'Outer', 'Inner']
# expected (correct) output: ['TopLevel', 'Outer']
```

---

## Probe Script

```python
import sys
import os
import ast
import tempfile

# Create a fresh temp directory for all probe work
tmpdir = tempfile.mkdtemp(prefix="probe_extract_classes_")
os.chdir(tmpdir)

# We need to import from the project root. Add the project root to sys.path
# so that 'src' is importable. We do NOT use the repo as workspace.
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

try:
    from src.scope import _extract_classes

    # Build a Python module AST with both top-level and nested classes
    source = """
class TopLevel:
    '''Docstring for TopLevel'''
    def method_one(self):
        pass
    async def method_two(self):
        pass

class Outer:
    '''Docstring for Outer'''
    class Inner:
        '''Docstring for Inner — this is nested and should NOT appear'''
        def inner_method(self):
            pass
    def outer_method(self):
        pass

def not_a_class():
    pass
"""
    tree = ast.parse(source)
    source_lines = source.splitlines(keepends=True)

    result = _extract_classes(tree, source_lines)

    # The spec requires only direct children of the module body:
    #   TopLevel, Outer
    # The buggy code (using ast.walk) also returns:
    #   Inner (the nested class)
    actual_names = sorted([d['name'] for d in result])
    expected_names = sorted(['TopLevel', 'Outer'])

    # Bug confirmed if 'Inner' shows up where it shouldn't
    nested_found = 'Inner' in actual_names

    if nested_found:
        print(f'CONFIRMED — actual classes: {actual_names} | expected: {expected_names} '
              f'(nested class "Inner" unwantedly appears due to ast.walk)')
    else:
        print(f'NOT CONFIRMED — actual classes: {actual_names} | expected: {expected_names}')

except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)

finally:
    # Cleanup temp directory
    import shutil
    os.chdir(proj_root)
    shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — actual classes: ['Inner', 'Outer', 'TopLevel'] | expected: ['Outer', 'TopLevel'] (nested class "Inner" unwantedly appears due to ast.walk)
```
