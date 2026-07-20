# Bug Report: _extract_classes

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/scope-py/_extract_classes.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of dicts, one per class defined at module scope in tree.
  - The list is ordered by ascending class start line (1‑based lineno).
  - Each dict contains at minimum these keys:
      * 'name' (str): the class name as written in the source code.
      * 'lineno' (int): the 1‑based line number of the class definition header.
      * 'end_lineno' (int): the 1‑based line number of the last line of the class
        body.
      * 'docstring' (str): the docstring text of the class, or the empty string
        when no docstring is present.
      * 'method_linenos' (list[int]): the 1‑based line numbers of every method
        (FunctionDef or AsyncFunctionDef) defined directly within the class body,
        sorted in ascending order.
  - Each dict also contains per‑method detail entries following the same field
    schema as funcs_info entries. Every method defined within the class is described
    by a sub‑dict with keys: 'name' (str), 'start' (int), 'end' (int), 'calls'
    (collection of str), 'idents' (collection of str), 'body_words' (collection of
    str), 'exc_types' (collection of str), and 'docstring' (str).
  - If tree contains no class definitions at module scope, returns an empty list.

---

### Actual Behavior

The function returns a list `C` of dictionaries such that:
- Natural language: The list contains one entry for every class definition in the AST, visited in depth-first preorder (the order produced by `ast.walk`). Each entry is a dict with keys `name`, `lineno`, `end_lineno`, `docstring`, `method_linenos`. The value for `name` is the class name (string). The values for `lineno` and `end_lineno` are the starting and ending line numbers of the class definition (integers from the AST node). The value for `docstring` is the class's docstring as extracted by `ast.get_docstring`, or an empty string if none is present. The value for `method_linenos` is a list of integers containing the line numbers of every `ast.FunctionDef` and `ast.AsyncFunctionDef` node that is a descendant of the class node, in the order they are encountered by `ast.walk` within the class subtree.
- Formal logic:
  Let `nodes = list(ast.walk(tree))`.
  Let `classes = [n for n in nodes if isinstance(n, ast.ClassDef)]`.
  Then `len(C) == len(classes)` and for all `i` in `range(len(C))`:
    `C[i] == {
      'name': classes[i].name,
      'lineno': classes[i].lineno,
      'end_lineno': classes[i].end_lineno,
      'docstring': ast.get_docstring(classes[i]) if ast.get_docstring(classes[i]) is not None else '',
      'method_linenos': [n.lineno for n in ast.walk(classes[i]) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    }`.
  Moreover, the order of `C` matches the order of first occurrence of each class node in `nodes` (i.e., depth-first preorder). The function never raises an exception under the given pre-condition.

---

## Code Evidence

Line 8: for node in ast.walk(tree):
Line 9: if not isinstance(node, ast.ClassDef):
Line 10: continue

---

## Trigger Condition

The code collects all ClassDef nodes in the entire AST tree, including nested classes. The specification requires only classes defined at module scope. For the given input, the output includes an extra dictionary for the nested class `Inner`, violating the specification. Additionally, required per-method detail sub-dicts are entirely missing from the output.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `tree` | `ast.parse()` result of a Python module containing a module-level class `Outer` with a nested class `Inner` and a standalone function |
| `source_lines` | The source lines split by newline |

### Expected (spec-correct) Output

A list containing one dict for `Outer` only (module scope), ordered by ascending lineno, with per-method detail sub-dicts for each method (name, start, end, calls, idents, body_words, exc_types, docstring).

### Actual (buggy) Output

A list containing two dicts (`Outer` and `Inner`), both missing per-method detail sub-dicts. Each dict only contains: `name`, `lineno`, `end_lineno`, `docstring`, `method_linenos`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import ast
from src.scope import _extract_classes

source = (
    "class Outer:\n"
    "    '''Outer docstring'''\n"
    "    def outer_method(self):\n"
    "        '''outer method doc'''\n"
    "        pass\n"
    "    \n"
    "    class Inner:\n"
    "        '''Inner docstring'''\n"
    "        def inner_method(self):\n"
    "            '''inner method doc'''\n"
    "            pass\n"
    "\n"
    "def standalone():\n"
    "    pass\n"
)

tree = ast.parse(source)
classes = _extract_classes(tree, source.split('\n'))
print([c['name'] for c in classes])
# actual (buggy) output: ['Outer', 'Inner']
# expected (correct) output: ['Outer']

print([sorted(c.keys()) for c in classes])
# actual (buggy) keys: [['docstring', 'end_lineno', 'lineno', 'method_linenos', 'name']]
# expected keys: includes per-method detail keys (start, end, calls, idents, etc.)
```

---

## Probe Script

```python
import sys
import os
import ast

# Add snapshot root to sys.path so `from src.scope import ...` resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.scope import _extract_classes

    # Python source with a module-level class containing a nested class
    source = (
        "class Outer:\n"
        "    '''Outer docstring'''\n"
        "    def outer_method(self):\n"
        "        '''outer method doc'''\n"
        "        pass\n"
        "    \n"
        "    class Inner:\n"
        "        '''Inner docstring'''\n"
        "        def inner_method(self):\n"
        "            '''inner method doc'''\n"
        "            pass\n"
        "\n"
        "def standalone():\n"
        "    pass\n"
    )

    tree = ast.parse(source)
    source_lines = source.split('\n')

    classes = _extract_classes(tree, source_lines)
    class_names = [c['name'] for c in classes]

    # Bug 1: Nested class 'Inner' should NOT be in the output.
    # Spec says "one per class defined at module scope in tree".
    # ast.walk visits ALL ClassDef nodes including nested ones.
    bug_nested = 'Inner' in class_names

    # Bug 2: Per-method detail sub-dicts (name, start, end, calls, idents,
    # body_words, exc_types, docstring) are entirely missing from the output.
    # The class dict should contain these per-method detail keys alongside
    # name, lineno, end_lineno, docstring, method_linenos.
    per_method_keys = {'start', 'end', 'calls', 'idents', 'body_words', 'exc_types'}
    bug_missing_details = False
    for cls in classes:
        cls_keys = set(cls.keys())
        # If none of the per-method detail keys are present, details are missing
        if not per_method_keys & cls_keys:
            bug_missing_details = True
            break

    # Bug is confirmed if either issue exists
    if bug_nested or bug_missing_details:
        reasons = []
        if bug_nested:
            reasons.append(
                f"nested class 'Inner' included in output "
                f"(spec requires module-scope classes only)"
            )
        if bug_missing_details:
            reasons.append(
                f"per-method detail sub-dicts (start, end, calls, idents, "
                f"body_words, exc_types, docstring) missing from output"
            )
        print(f"CONFIRMED — {'; '.join(reasons)}")
        print(f"  actual classes: {class_names}")
        print(f"  expected (spec): ['Outer'] (module-scope only, excluding nested Inner)")
        print(f"  actual class keys: {[sorted(c.keys()) for c in classes]}")
        print(f"  expected keys per spec: name, lineno, end_lineno, docstring, "
              f"method_linenos + per-method detail sub-dicts")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {class_names}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — nested class 'Inner' included in output (spec requires module-scope classes only); per-method detail sub-dicts (start, end, calls, idents, body_words, exc_types, docstring) missing from output
  actual classes: ['Outer', 'Inner']
  expected (spec): ['Outer'] (module-scope only, excluding nested Inner)
  actual class keys: [['docstring', 'end_lineno', 'lineno', 'method_linenos', 'name'], ['docstring', 'end_lineno', 'lineno', 'method_linenos', 'name']]
  expected keys per spec: name, lineno, end_lineno, docstring, method_linenos + per-method detail sub-dicts
```
