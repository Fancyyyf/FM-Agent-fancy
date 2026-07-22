# Bug Report: _qualified_parts

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/languages/codegraph-py/_qualified_parts.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of non-empty strings
  - The last element of the returned list equals name
  - When qualified_name is non-empty and has name as a suffix, the elements before the last are the scope qualifier components extracted from the prefix of qualified_name that precedes name, split on "::" or "."
  - When qualified_name is empty or does not have name as a suffix, the returned list is [name]
  - The character used as the scope separator in qualified_name ("." or "::") does not affect the set or order of components in the returned list
  - The same (name, qualified_name) pair always produces the same returned list

---

### Actual Behavior

The function returns a list L with the following behavior. Let q = qualified_name.strip(). If q is the empty string or does not end with name, L = [name]. Otherwise, let scope = q[:-len(name)].rstrip(':.') . If scope is the empty string, L = [name]. Otherwise, L = [p for p in re.split(r'::|\.', scope) if p != ''] + [name]. No exceptions are raised because inputs are strings and operations are safe for strings.

---

## Code Evidence

Line 14: q = (qualified_name or "").strip()

---

## Trigger Condition

The specification requires extracting the scope prefix from the original qualified_name (without stripping), but the code strips whitespace via Line 14 before processing. For qualified_name=' bar::foo', the specification would yield [' bar', 'foo'] because the prefix ' bar::' split on '::' gives ' bar', while the code strips to 'bar::foo' and returns ['bar', 'foo'], violating the requirement that the returned list reflects the scope components of the original qualified_name prefix.

---

## How to trigger the bug

The code strips whitespace from `qualified_name` via `.strip()` on Line 62 of `src/languages/codegraph.py` before extracting scope components. When `qualified_name` contains leading whitespace that is part of the scope prefix (e.g., `' bar::foo'`), the spec requires preserving it in the output (`[' bar', 'foo']`), but the code strips it away and returns `['bar', 'foo']`.

### Inputs

| Parameter | Value |
|-----------|-------|
| name | `'foo'` |
| qualified_name | `' bar::foo'` |

### Expected (spec-correct) Output

`[' bar', 'foo']`

### Actual (buggy) Output

`['bar', 'foo']`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
from src.languages.codegraph import _qualified_parts

result = _qualified_parts('foo', ' bar::foo')
# actual (buggy) output: ['bar', 'foo']
# expected (correct) output: [' bar', 'foo']
```

---

## Probe Script

```python
import sys
import os

# Add the repo root to sys.path so that 'src' can be imported
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, repo_root)

try:
    from src.languages.codegraph import _qualified_parts

    # Trigger condition: qualified_name=' bar::foo', name='foo'
    # Spec says: prefix of original qualified_name preceding name is ' bar::'
    #   split on '::' or '.' -> [' bar', ''] -> non-empty: [' bar']
    #   expected result: [' bar', 'foo']
    # Code strips whitespace first, so ' bar::foo' -> 'bar::foo', prefix is 'bar'
    #   result: ['bar', 'foo']
    actual = _qualified_parts('foo', ' bar::foo')
    expected = [' bar', 'foo']  # spec-correct value

    passed = actual != expected  # True -> bug reproduced
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: ['bar', 'foo'] | expected: [' bar', 'foo']
```
