# Bug Report: _split_env_paths

**Source file:** `src/domain_knowledge-py/_split_env_paths.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If value is None or empty, returns an empty list
  - For a non-empty value, the function treats both the OS path separator (os.pathsep) and newline characters as path element separators, producing a list of individual path strings
  - Every element in the returned list is a non-empty string with no leading or trailing whitespace
  - The relative order of the returned path elements corresponds to their order of appearance in value
  - Empty path components (those that become empty after whitespace stripping) are discarded and do not appear in the result

---

### Actual Behavior

The function returns a list of strings with no empty elements. If the input `value` is None or an empty string, or if after replacing newlines with the OS path separator and splitting by that separator all resulting parts consist solely of whitespace characters, the list is empty. Otherwise, each element is a string obtained by splitting the modified input (with newlines replaced by `os.pathsep`) by `os.pathsep`, stripping whitespace from both ends, and keeping those that are non-empty, in the original order. Formally: let `value` be the argument. If `value` is None or `not value` is True, return `[]`. Else define `s = value.replace("\n", os.pathsep)`. Let `L = s.split(os.pathsep)`. Then the returned list is `[x.strip() for x in L if x.strip() != ""]`.

---

## Code Evidence

Line 4: normalized = value.replace("\n", os.pathsep)

---

## Trigger Condition

The specification requires treating both the OS path separator and newline characters as path element separators. 'newline characters' typically include carriage return ('\r') in addition to line feed ('\n'). The code only replaces '\n' with `os.pathsep`, ignoring '\r'. As a result, an input like `"a\rb"` does not get split on the carriage return, and the function returns `["a\rb"]` instead of the expected `["a", "b"]`.

---

## How to trigger the bug

The function `_split_env_paths` is called by the public function `collect_domain_knowledge_paths` when the environment variable `FM_AGENT_DOMAIN_KNOWLEDGE` is set. Setting this variable to a value containing carriage return characters (`\r`) between valid markdown filenames triggers the bug: the carriage return is not treated as a separator, causing the combined string to be misidentified as a single filename.

### Inputs

| Parameter | Value |
|-----------|-------|
| `FM_AGENT_DOMAIN_KNOWLEDGE` (env var) | `"a.md\rb.md"` |
| `cli_paths` (arg to collect_domain_knowledge_paths) | `[]` (empty list) |
| `base_dir` | temp directory containing valid `a.md` and `b.md` files |

### Expected (spec-correct) Output

`collect_domain_knowledge_paths` should return 2 resolved absolute paths (one for `a.md`, one for `b.md`), because `_split_env_paths` should split `"a.md\rb.md"` into `["a.md", "b.md"]`.

### Actual (buggy) Output

`collect_domain_knowledge_paths` raises `ValueError: domain knowledge file does not exist: a.md\rb.md`, because `_split_env_paths` returns `["a.md\rb.md"]` (the `\r` was not treated as a separator), and the downstream `resolve_domain_knowledge_paths` cannot find a file literally named `a.md\rb.md`.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, sys, tempfile
sys.path.insert(0, '.')
from src import domain_knowledge

with tempfile.TemporaryDirectory() as tmpdir:
    for name in ('a', 'b'):
        with open(os.path.join(tmpdir, f'{name}.md'), 'w') as f:
            f.write('# test\n')
    os.environ['FM_AGENT_DOMAIN_KNOWLEDGE'] = 'a.md\rb.md'
    result = domain_knowledge.collect_domain_knowledge_paths(
        cli_paths=[], base_dir=tmpdir,
    )
    # expected: 2 resolved paths
    # actual (buggy): ValueError raised
```

---

## Probe Script

```python
"""Probe for _split_env_paths bug: \r not treated as path separator."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from src import domain_knowledge

actual = None
expected = 2  # Should resolve 2 files
passed = False

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two valid .md files
        a_path = os.path.join(tmpdir, 'a.md')
        b_path = os.path.join(tmpdir, 'b.md')
        for p in (a_path, b_path):
            with open(p, 'w') as f:
                f.write('# test\n')

        # Set env var with \r separator between two valid filenames
        # Spec says both \n and "newline characters" (includes \r) should be separators
        # Buggy code only replaces \n, so "a.md\rb.md" becomes a single path element
        os.environ['FM_AGENT_DOMAIN_KNOWLEDGE'] = 'a.md\rb.md'

        try:
            result = domain_knowledge.collect_domain_knowledge_paths(
                cli_paths=[],
                base_dir=tmpdir,
            )
            # If we reach here without ValueError, the bug might still exist:
            # _split_env_paths returned ["a.md\rb.md"] (didn't split on \r)
            # but resolve_domain_knowledge_paths somehow resolved it
            actual = len(result)
            passed = actual != expected  # Bug: only 1 file resolved, not 2
        except ValueError as e:
            # If ValueError, _split_env_paths returned ["a.md\rb.md"] (single element)
            # and resolve_domain_knowledge_paths couldn't find a file named "a.md\rb.md"
            actual = f'ValueError: {e}'
            passed = True  # Bug confirmed: \r was not treated as separator

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED - actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED - actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED - actual: 'ValueError: domain knowledge file does not exist: a.md\rb.md' | expected: 2
```
