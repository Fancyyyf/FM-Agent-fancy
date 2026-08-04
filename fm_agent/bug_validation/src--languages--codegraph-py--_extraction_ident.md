# Bug Report: _extraction_ident

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/codegraph-py/_extraction_ident.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a canonicalized fully-qualified function identifier using '::' as the component separator. Each component of the qualified name is first stripped of tree-sitter decorations (type signatures, template bodies, and parameter lists) to yield the bare identifier, then transformed for filesystem and FQN safety by replacing every '/' character with '_'. The number of components equals the number of identifier segments after splitting qualified_name on '::' and '.' boundaries, preserving left-to-right order.

---

### Actual Behavior

The function returns a string R that satisfies: Let C = _qualified_parts(name, qualified_name), a list of component strings obtained by splitting qualified_name on '::' and '.' boundaries, defaulting to [name] if no components arise. Then R = '::'.join(canonicalize(_bare_function_name(p)) for p in C). For each p, _bare_function_name(p) strips tree-sitter decorations, leaving the bare identifier, and canonicalize(s) replaces every '/' with '_'. Hence R is a class-qualified identifier with '::' separators, free of slashes and tree-sitter artifacts, and safe for filesystem use.

---

## Code Evidence

Line 15: return "::".join(
Line 16:     canonicalize(_bare_function_name(p))
Line 17:     for p in _qualified_parts(name, qualified_name)
Line 18: )

---

## Trigger Condition

When qualified_name starts with '::' (e.g., '::foo'), _qualified_parts splits on '::' boundaries yielding an empty first component. The code includes this empty component in the joined result, producing '::foo'. The specification requires the number of components to equal the number of identifier segments (i.e., non-empty parts), so the expected result is 'foo'.

---

## How to trigger the bug

The bug occurs when `_qualified_parts` produces a component that `_bare_function_name` transforms to an empty string, which then becomes a leading `"::"` separator in the joined result. The simplest reproducing case uses `qualified_name = ":: foo"` — the space after `::` survives `rstrip(":.")` in `_qualified_parts`, becomes a whitespace component, and `_bare_function_name(" ")` returns `""`. The `"::".join(["", "foo"])` then produces `"::foo"` instead of the expected `"foo"`.

### Inputs

| Parameter | Value |
|-----------|-------|
| name | `"foo"` |
| qualified_name | `":: foo"` |

### Expected (spec-correct) Output

`"foo"`

### Actual (buggy) Output

`"::foo"`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

from languages.codegraph import _extraction_ident

# The bug: qualified_name ":: foo" produces a whitespace component
# that _bare_function_name reduces to "", then join produces a leading "::"
result = _extraction_ident('foo', ':: foo')
# actual (buggy) output: '::foo'
# expected (correct) output: 'foo'
```

---

## Probe Script

```python
import sys
import os

# Add repo root (for config module) and src/ (for languages package) to path
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _repo_root)
sys.path.insert(0, os.path.join(_repo_root, 'src'))

try:
    from languages.codegraph import _extraction_ident, _qualified_parts

    # Bug trigger: qualified_name starting with "::" where _qualified_parts
    # produces a component that _bare_function_name reduces to empty string,
    # which then produces a leading "::" in the joined result.
    #
    # The spec says: "Returns a canonicalized fully-qualified function identifier
    # using '::' as the component separator." The number of components should
    # equal the number of identifier segments (non-empty parts).
    #
    # Test case: ":: foo" - the space after :: creates a whitespace component
    # that _bare_function_name() turns into "", which then joins to produce "::foo"
    # instead of "foo".
    name = 'foo'
    qualified_name = ':: foo'

    actual = _extraction_ident(name, qualified_name)
    expected = 'foo'  # spec-correct: only one identifier segment -> just 'foo'

    passed = (actual != expected)  # True -> bug reproduced

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: '::foo' | expected: 'foo'
```
