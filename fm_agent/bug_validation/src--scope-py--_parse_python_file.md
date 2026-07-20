# Bug Report: _parse_python_file

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/scope-py/_parse_python_file.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If the source text is syntactically valid Python and can be parsed into an AST
    without raising an exception, returns a 3‑tuple (funcs_info, source_lines, classes)
    where:
      * funcs_info is a list of dicts, one per function defined at module scope.
        Each dict contains at minimum the following keys:
          - 'name' (str): the function name as written in the source
          - 'start' (int): 1‑based line number of the `def` or `async def` header
          - 'end' (int): 1‑based line number of the last line of the function body
          - 'calls' (collection of str): every name that is the direct target of a
            function‑call expression within the function body
          - 'idents' (collection of str): every identifier whose value is read
            within the function body
          - 'body_words' (collection of str): every distinct alphabetic token of at
            least 3 characters appearing in the function body source text, excluding
            tokens inside comments, string literals, and the docstring
          - 'exc_types' (collection of str): every exception type name that is
            raised, caught, or bound within the function body
          - 'docstring' (str): the docstring text of the function, or the empty
            string when no docstring is present
      * funcs_info includes both synchronous functions (FunctionDef) and
        asynchronous functions (AsyncFunctionDef); the schema of entries is identical
        regardless of the function kind.
      * source_lines is a list[str] containing every line of the source file in
        original order, with trailing newline characters removed
      * classes is a list of dicts, one per class defined at module scope, each
        containing the class name, 1‑based line range, method line numbers, and
        per‑method entries following the same field schema as funcs_info entries
  - If AST construction raises any exception (including SyntaxError, memory errors,
    or IO errors during file read), returns (None, None, None).
  - The function does not write to or rename any file; src_path is read only.

---

### Actual Behavior

After execution, the function returns a tuple. If an exception was raised during the reading, parsing, or splitting of the file (i.e., any Exception caught in the try block), the return value is (None, None, None). Otherwise, the return value is a 3‑tuple (funcs, source_lines, classes) where: (1) funcs is a list of dicts, one for each toplevel ast.FunctionDef or ast.AsyncFunctionDef node walked in the tree, each dict containing keys 'name', 'start', 'end', 'calls' (result of _collect_calls on that node), 'idents', 'body_words', 'exc_types' (results of _collect_func_idents on that node), 'docstring' (the function's docstring or ''); (2) source_lines is a list of strings, the lines obtained by splitting the file content; and (3) classes is the result of _extract_classes(tree, source_lines), a list of dicts per toplevel class with analogous fields. The function has no sideeffects other than logging a warning on failure. Formal postcondition: ( e: Exception, e raised inside the try block ⇒ result = (None, None, None)) ∧ ( ¬∃ e: Exception, e raised inside the try block ⇒ content, tree, L: content = src_path.read_text() ∧ tree = ast.parse(content) ∧ L = content.splitlines() ∧ result = (funcs, L, _extract_classes(tree, L)) ∧ funcs = [ { 'name':n.name, 'start':n.lineno, 'end':n.end_lineno, 'calls':_collect_calls(n), 'idents':i, 'body_words':bw, 'exc_types':et, 'docstring':ast.get_docstring(n) or '' } for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) ] where (i,bw,et) = _collect_func_idents(n, L) ).

---

## Code Evidence

```
Line 11: for node in ast.walk(tree):
Line 12:     if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
Line 13:         continue
```

---

## Trigger Condition

The code uses ast.walk which visits all nodes, including nested function/class definitions. This causes method definitions inside a class (e.g., bar) to be collected into the funcs list. The specification requires funcs_info to contain only functions defined at module scope. Therefore, for a file with a class containing a method and no top-level functions, the code incorrectly returns a non-empty funcs list, whereas the specification expects an empty one.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| src_path | Path to a .py file containing only a class with a method (no module-level functions) |

### Expected (spec-correct) Output

Empty `funcs` list `[]` — the method `my_method` is inside a class, not at module scope.

### Actual (buggy) Output

Non-empty `funcs` list containing `[{'name': 'my_method', ...}]` — `ast.walk()` traverses the class body and picks up the nested `FunctionDef` node.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from pathlib import Path
from src.scope import _parse_file

# File with a class method but no module-level functions
source = """
class MyClass:
    def my_method(self):
        pass
"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(source)
    tmp_path = Path(f.name)

funcs, source_lines, classes = _parse_file(tmp_path)
tmp_path.unlink(missing_ok=True)

# actual (buggy) output: len(funcs) == 1, funcs[0]['name'] == 'my_method'
# expected (correct) output: len(funcs) == 0
print(funcs)
```

---

## Probe Script

```python
import sys
import tempfile
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from src.scope import _parse_file
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

source = """
class MyClass:
    def my_method(self):
        pass
"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(source)
    tmp_path = Path(f.name)

try:
    funcs, source_lines, classes = _parse_file(tmp_path)
except Exception as e:
    print(f'ERROR: {e}')
    tmp_path.unlink(missing_ok=True)
    sys.exit(1)
finally:
    tmp_path.unlink(missing_ok=True)

if funcs is None:
    print('ERROR: _parse_file returned None')
    sys.exit(1)

method_names = [f['name'] for f in funcs]
expected_empty = True
actual_non_empty = len(funcs) > 0

if actual_non_empty:
    print(f'CONFIRMED — funcs contains class methods: {method_names} | expected: [] (empty)')
else:
    print(f'NOT CONFIRMED — funcs is empty as expected')
```

### Probe Output

```
CONFIRMED — funcs contains class methods: ['my_method'] | expected: [] (empty)
```
