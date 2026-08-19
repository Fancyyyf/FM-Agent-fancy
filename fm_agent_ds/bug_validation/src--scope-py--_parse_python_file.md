# Bug Report: _parse_python_file

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/scope-py/_parse_python_file.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When the file content is valid Python syntax parsable by ast.parse: returns a triple (funcs, source_lines, classes). funcs is a list of zero or more dicts, each representing a top-level function definition (FunctionDef or AsyncFunctionDef) found at module scope. Each func dict contains: 'name' (string, the function identifier), 'start' (int, the 1-indexed line where the function definition begins), 'end' (int, the 1-indexed line where the function definition ends), 'calls' (list of string names of functions called within the body), 'idents' (set of lowercase identifier strings used in the function), 'body_words' (set of lowercase word tokens from the function body text), 'exc_types' (set of lowercase exception-type names referenced in the function body), and 'docstring' (string, the function's docstring or the empty string when none exists). source_lines is a list of strings, one per line of the file content. classes is a list of dicts, each containing at least a 'name' key (string) and a 'docstring' key (string), representing classes found at module scope. When ast.parse raises any exception, returns (None, None, None). The function does not modify the source file.

---

### Actual Behavior

After execution, the function returns a tuple r. If an exception of type Exception (or any subclass) is raised during the reading of the file (line 4) or during the AST parsing (line 5), then r = (None, None, None). Otherwise, let content = src_path.read_text(errors='replace'), source_lines = content.splitlines(), and tree = ast.parse(content) (which is guaranteed to be a valid ast.Module instance). Then r = (funcs, source_lines, classes) where: - source_lines is the list of strings representing the lines of the file, as produced by str.splitlines(content) (no linebreak characters retained). - funcs is a list of dictionaries, one for each function or async function definition found by walking the entire AST (ast.walk(tree)). For each such node n (of type ast.FunctionDef or ast.AsyncFunctionDef), the corresponding dictionary has the keys: 'name' (str, the function name), 'start' (int, line number of the definition), 'end' (int, end line number of the definition), 'calls' (list of strings returned by _collect_calls(n)), 'idents' (set of lowercase identifier strings from _collect_func_idents(n, source_lines)[0]), 'body_words' (set of lowercase word tokens from _collect_func_idents(n, source_lines)[1]), 'exc_types' (set of lowercase exception class names from _collect_func_idents(n, source_lines)[2]), and 'docstring' (the docstring of the function as a string, or '' if none, obtained from ast.get_docstring(n) or ''). The order of funcs is the same as the order in which ast.walk(tree) yields the corresponding nodes (a deterministic preorder walk). - classes is the result of _extract_classes(tree, source_lines): a list of dictionaries, one for each toplevel class definition in the module, with at least the keys 'name', 'docstring', and 'method_linenos' as described in the function's specification. If no toplevel classes exist, classes is an empty list. Formally, let R be the returned tuple. Then: (  exc  Exception  (reading or parsing raised...

---

## Code Evidence

Line 11: for node in ast.walk(tree):

---

## Trigger Condition

The code uses ast.walk(tree) which traverses all nodes in the AST, including nested function definitions inside other functions or classes. The specification explicitly states that funcs should only contain top-level function definitions at module scope. Therefore, the inclusion of nested functions violates the specification.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|---|---|
| src_path | A Python file containing a top-level function with a nested function definition inside it |

### Expected (spec-correct) Output

`funcs` containing only top-level function definitions at module scope: `['outer', 'standalone']`

### Actual (buggy) Output

`funcs` containing all functions found by `ast.walk()`, including nested functions: `['outer', 'standalone', 'inner', 'method', 'nested_in_method']`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from pathlib import Path
from src.scope import _parse_python_file

test_content = """\
def outer():
    def inner():
        pass
    return inner

class MyClass:
    def method(self):
        def nested_in_method():
            pass

def standalone():
    pass
"""

# Write to a temp file
import tempfile
with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(test_content)
    tmp_path = Path(f.name)

funcs, _, _ = _parse_python_file(tmp_path)
print([f['name'] for f in funcs])
# actual (buggy) output: ['outer', 'standalone', 'inner', 'method', 'nested_in_method']
# expected (correct) output: ['outer', 'standalone']
```

---

## Probe Script

```python
"""Probe script for bug src--scope-py--_parse_python_file.

Bug: _parse_python_file uses ast.walk(tree) which includes nested function
definitions, but the spec requires only top-level function definitions at
module scope.
"""
import sys
import tempfile
import os
from pathlib import Path

# Add repo root to sys.path so 'src' package is importable
_repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_repo_root))

try:
    from src.scope import _parse_python_file
except Exception as e:
    print(f'ERROR importing _parse_python_file: {e}')
    sys.exit(1)

# Create a temp directory for test fixtures (self-validation guard).
with tempfile.TemporaryDirectory(prefix='fm_agent_probe_') as tmpdir:
    test_file = Path(tmpdir) / 'test_nested.py'
    test_file.write_text("""\
def outer():
    def inner():
        pass
    return inner

class MyClass:
    def method(self):
        def nested_in_method():
            pass

def standalone():
    pass
""")

    try:
        funcs, source_lines, classes = _parse_python_file(test_file)
    except Exception as e:
        print(f'ERROR calling _parse_python_file: {e}')
        sys.exit(1)

    if funcs is None:
        print('ERROR: _parse_python_file returned None (parse failure)')
        sys.exit(1)

    func_names = [f['name'] for f in funcs]
    # Bug: ast.walk(tree) includes nested functions (inner, nested_in_method)
    # Spec: only top-level functions (outer, standalone) should be included.
    nested_found = [n for n in func_names if n in ('inner', 'nested_in_method')]
    top_level_found = [n for n in func_names if n in ('outer', 'standalone', 'method')]

    print(f'All functions found: {func_names}')
    print(f'Top-level functions found: {top_level_found}')
    print(f'Nested functions found: {nested_found}')

    has_nested = len(nested_found) > 0
    # Spec says: funcs should contain ONLY top-level definitions.
    # Bug says: nested functions are incorrectly included.
    # So nested functions appearing = bug confirmed.
    if has_nested:
        expected_names = {'outer', 'standalone'}  # spec-correct (top-level only)
        actual_names = set(func_names)
        print(f'CONFIRMED — Nested functions {nested_found} incorrectly included. '
              f'Spec expects only top-level: {expected_names}. '
              f'Actual (buggy): {actual_names}')
    else:
        print(f'NOT CONFIRMED — No nested functions found in funcs: {func_names}')
```

### Probe Output

```
All functions found: ['outer', 'standalone', 'inner', 'method', 'nested_in_method']
Top-level functions found: ['outer', 'standalone', 'method']
Nested functions found: ['inner', 'nested_in_method']
CONFIRMED — Nested functions ['inner', 'nested_in_method'] incorrectly included. Spec expects only top-level: {'standalone', 'outer'}. Actual (buggy): {'nested_in_method', 'outer', 'standalone', 'method', 'inner'}
```
