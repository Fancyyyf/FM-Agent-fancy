# Bug Report: _extract_functions_indent

**Source file:** `src/extract-py/_extract_functions_indent.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of (raw_name, start, end) tuples, ordered by ascending
    start index
  - Each tuple identifies one function definition found in lines:
    * raw_name is the function identifier extracted from the definition line
    * start is the zero-based index of the block's first line: either the
      definition line itself, or the earliest immediately-preceding decorator
      line when the definition line is preceded by one or more consecutive
      decorator lines
    * end is the zero-based index of the last non-blank line in the function
      body
  - The contiguous span lines[start..end] contains exactly one function
    definition header; every non-blank line in that span either belongs to
    the function body (indented more deeply than the definition header) or
    forms a continuation of the header at the same indentation level
  - Lines whose indentation is shallower than or equal to the definition
    header, that are not header continuations, are classified as belonging
    to a subsequent top-level construct and are excluded from the span
  - Blank lines within the span do not affect boundary detection
  - Trailing blank lines after the last non-blank body line are excluded
    from the span (end is reduced to the last non-blank line)
  - Returns an empty list when no line in the input matches the
    function-definition pattern for the language
  - Function names are returned as raw identifiers extracted directly from
    the definition line; deduplication of duplicate names is the caller's
    responsibility

---

### Actual Behavior

Let `L` be the returned list. Then:
1. L is a list of triples (name, start, end) with 0  start  end < len(lines).
2. For each (n, s, e)  L, there exists an indentation level I and an index d  [s, e] such that line d matches the regex `^\s*def\s+(\w+)\s*\(`, capturing I as len(leading whitespace) and n as the function name; all lines from s to d1 are decorators (start with '@'); s is the start of the contiguous decorator block; e is the last non-blank line within the function body; the body comprises lines after d with indentation > I or (indentation == I and matches `\)\s*(:|->)`), and breaks at the first non-blank line that has indentation  I and does not match that continuation pattern; trailing blank lines are excluded from e.
3. The intervals in L are disjoint, non-nested, and ordered by start index.
4. For every line index d matching the def pattern with indentation I, if d is not inside any interval of L (i.e., there is no (n,s,e)L with s  d  e), then there exists a tuple in L whose interval contains d.
Thus L contains exactly all top-level function definitions.

---

## Code Evidence

Line 28:             if line_indent == indent and re.match(r'\)\s*(:|->)', l.lstrip())
Line 31:             if line_indent <= indent:
Line 32:                 break

---

## Trigger Condition

The code only treats a same-indentation line as a header continuation if it begins with a closing parenthesis followed by ':' or '->'. This misses valid continuation lines like 'b):' that do not start with ')'. The specification requires that any line at the same indentation that continues the function header be included in the span.

---

## How to trigger the bug

The bug manifests when a function header spans multiple lines and a continuation line at the same indentation level as the `def` keyword does not begin with `)` after stripping whitespace. For example, the valid Python code:

```python
def foo(a,
b): return 42
```

Here line `b): return 42` has the same indentation as `def foo(a,` but after `lstrip()` it becomes `b): return 42`, which does not match the regex `^\)\s*(:|->)`. The algorithm treats it as a non-continuation, same-indentation line and breaks, truncating the function body.

### Inputs

| Parameter | Value |
|-----------|-------|
| filepath | Temporary `.py` file containing: `def foo(a,\nb): return 42\n` |
| lang_key | `'python'` |

### Expected (spec-correct) Output

```
[('foo', 'def foo(a,\nb): return 42\n')]
```

The function `foo` should span lines [0, 1], containing both the definition line and the continuation/body line.

### Actual (buggy) Output

```
[('foo', 'def foo(a,\n')]
```

The function is truncated to line [0, 0]; the continuation line `b): return 42` is excluded.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
import os
from src.extract import extract_functions_from_file

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write("def foo(a,\nb): return 42\n")
    tmp_path = f.name

try:
    result = extract_functions_from_file(tmp_path, 'python')
    name, source = result[0]
    # actual (buggy) output: source == 'def foo(a,\n'  (function body truncated)
    # expected (correct) output: source should include 'b): return 42'
    print(f"BUG CONFIRMED: source = {source!r} (missing 'return 42')")
finally:
    os.unlink(tmp_path)
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Ensure repo root is on the path so `src.extract` resolves
_PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJ_ROOT not in sys.path:
    sys.path.insert(0, _PROJ_ROOT)

try:
    from src.extract import extract_functions_from_file

    # Create a temporary Python file with the bug-triggering code.
    # The function header continuation line "b): return 42" has the same
    # indentation as "def" but does NOT start with ')' after lstrip,
    # so the regex r'\)\s*(:|->)' fails to recognise it as a continuation.
    buggy_code = "def foo(a,\nb): return 42\n"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(buggy_code)
        tmp_path = f.name

    try:
        result = extract_functions_from_file(tmp_path, 'python')

        if len(result) == 0:
            print(f'CONFIRMED — extract_functions_from_file returned empty list for valid function')
        elif len(result) != 1:
            print(f'CONFIRMED — expected 1 function but got {len(result)}: {result}')
        else:
            name, source = result[0]
            # Spec-correct behaviour: the span should include the continuation
            # line "b): return 42" and thus contain "return 42".
            if 'return 42' in source:
                print(f'NOT CONFIRMED — function body correctly included return 42 in source: {source!r}')
            else:
                print(f'CONFIRMED — function body truncated; "return 42" missing. Got: {source!r}')
    finally:
        os.unlink(tmp_path)

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — function body truncated; "return 42" missing. Got: 'def foo(a,\n'
```
