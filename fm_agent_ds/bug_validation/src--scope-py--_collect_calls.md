# Bug Report: _collect_calls

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/scope-py/_collect_calls.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a set of zero or more strings, each representing the syntactic name used at a call site within the function body. For a call to f(), the name 'f' is collected. For a call to x.f(), the attribute name 'f' is collected. Each unique call-site name appears at most once in the returned set.

---

### Actual Behavior

The returned set `calls` contains exactly the strings gathered from the `func` attribute of every `ast.Call` node encountered during a walk of the AST rooted at `node` (including `node` itself and all sub-nodes). For each such call `c`, if `c.func` is an `ast.Name` node, its `id` string is added; if `c.func` is an `ast.Attribute` node, its `attr` string is added. No other call forms (e.g., `ast.Subscript`, `ast.Lambda`, `ast.Call`, etc.) contribute to the set. The set has no side effects, does not modify `node`, and contains no duplicates. Formally: `\result = { n.func.id | n \in ast.walk(node) \land isinstance(n, ast.Call) \land isinstance(n.func, ast.Name) } \cup { n.func.attr | n \in ast.walk(node) \land isinstance(n, ast.Call) \land isinstance(n.func, ast.Attribute) }`.

---

## Code Evidence

Line 3: for n in ast.walk(node):

---

## Trigger Condition

The specification requires collecting only call-site names that occur within the function body. The code walks the entire ast.FunctionDef/AsyncFunctionDef node, which includes decorators (decorator_list). Calls inside decorators are not part of the function body but are nevertheless collected, adding extra names to the returned set.

---

## How to trigger the bug

A decorated function like `@mydecorator(42) def foo(a, b): bar()` causes `_collect_calls` to include `'mydecorator'` in the returned set because the decorator expression `mydecorator(42)` is an `ast.Call` node stored in the FunctionDef's `decorator_list`, which `ast.walk()` traverses. The specification requires only call-site names within the function body, so decorator calls should be excluded.

### Inputs

| Parameter | Value |
|-----------|-------|
| `node` | `ast.FunctionDef` for `def foo(a, b): bar()` decorated with `@mydecorator(42)` |

### Expected (spec-correct) Output

`{'bar'}`

### Actual (buggy) Output

`{'bar', 'mydecorator'}`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import ast
from src.scope import _collect_calls

source = """
@mydecorator(42)
def foo(a, b):
    bar()
"""
tree = ast.parse(source)
func_node = tree.body[0]
calls = _collect_calls(func_node)
print(calls)
# actual (buggy) output: {'bar', 'mydecorator'}
# expected (correct) output: {'bar'}
```

---

## Probe Script

```python
import sys
import ast

try:
    from src.scope import _collect_calls
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

source = """
@mydecorator(42)
def foo(a, b):
    bar()
"""

tree = ast.parse(source)
func_node = tree.body[0]  # The FunctionDef node

calls = _collect_calls(func_node)

expected = {'bar'}
actual = calls
passed = actual != expected

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: {'bar', 'mydecorator'} | expected: {'bar'}
```
