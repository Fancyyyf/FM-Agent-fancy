# Bug Report: _extract_functions_indent

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/src/extract-py/_extract_functions_indent.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of (name, start_idx, end_idx) tuples, one per top-level function definition found in lines. start_idx and end_idx are 0-based inclusive line indices. The span from start_idx to end_idx covers the entire function: any preceding decorator lines, the function definition header (which may span multiple lines), and the function body  but excludes trailing blank lines that follow the last non-blank body line. name is the identifier token appearing immediately after the function-definition keyword on the definition line. Functions are returned in the order they appear in lines. Returns an empty list when no function definitions are found.

---

### Actual Behavior

The function returns a list `functions` of tuples `(name, start, end)`, where each tuple corresponds to a top-level function definition found in `lines`. A function definition is a line matching the pattern `def name(` (with any indentation). `start` is the index of the first line of the function, including any preceding decorator lines (lines starting with '@'). `end` is the index of the last non-blank line of the function body. The body consists of lines after the definition with indentation greater than the definition's indentation, blank lines, and lines that have exactly the definition's indentation but start with a closing parenthesis followed by ':' or '->' (continuation of a multi-line signature). The body ends just before the first line that is not blank, has indentation less than or equal to the definition's indentation, and is not a signature continuation. Functions are extracted in the order their `def` lines appear, skipping any `def` lines that lie within the body of a previously extracted function (i.e., only outermost functions are extracted). The input `lines` and `lang_cfg` are not modified.

---

## Code Evidence

Line 28: if line_indent == indent and re.match(r')\s*(:|->)', l.lstrip()):

---

## Trigger Condition

The code only recognizes a multi-line function signature when a line with the definition's indentation starts with ')' followed by ':' or '->'. When a continuation line at the same indentation does not start with ')', such as an argument line or the closing line without the prefix ')', the code incorrectly treats it as the end of the function, truncating the span. In the counterexample, line 'b):' has indentation 0, equal to the def's indent, but does not match the signature-continuation regex, so the inner loop breaks, yielding a span of [0,0] instead of covering the whole function.

---

## How to trigger the bug

The bug is triggered when a Python function definition has a multi-line signature where parameter continuation lines at the same indentation level as `def` do not start with `)`. The signature-continuation regex `r'\)\s*(:|->)'` only matches lines beginning with `)`, so parameter lines at the def indentation are incorrectly treated as the end of the function.

### Inputs

| Parameter | Value |
|-----------|-------|
| lines | `["def foo(a,", "b):", "    pass"]` |
| lang_cfg | Python language config (`"body": "indent"`) |

### Expected (spec-correct) Output

`[("foo", 0, 2)]` — span covering the full function: `def foo(a,\nb):\n    pass\n`

### Actual (buggy) Output

`[("foo", 0, 0)]` — span truncated to just the first line: `def foo(a,\n`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
import os

from src.extract import extract_functions_from_file

# Create a temp file with a multi-line function signature
with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    temp_path = f.name
    f.write('def foo(a,\n')
    f.write('b):\n')
    f.write('    pass\n')

results = extract_functions_from_file(temp_path, 'python')
name, source = results[0]
# actual (buggy) output: 'def foo(a,\n'
# expected (correct) output: 'def foo(a,\nb):\n    pass\n'
print(repr(source))

os.unlink(temp_path)
```

---

## Probe Script

```python
r"""Probe script for bug: src--extract-py--_extract_functions_indent

Bug: _extract_functions_indent uses regex r'\)\s*(:|->)' to detect multi-line
signature continuations, missing continuation lines that don't start with ')'.
When a parameter line at the same indentation does not match, the function span
is truncated.

Counterexample:
    def foo(a,
    b):
        pass

The 'b):' line has indent 0 (same as def), but doesn't match the continuation
regex, so the function span becomes [0,0] instead of [0,2].
"""

import os
import sys
import tempfile

# Ensure the src package is importable from the repo root
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(_REPO_ROOT, "pyproject.toml")):
    parent = os.path.dirname(_REPO_ROOT)
    if parent == _REPO_ROOT:
        print("ERROR: Could not find repo root")
        sys.exit(1)
    _REPO_ROOT = parent

sys.path.insert(0, _REPO_ROOT)


def main():
    # Counterexample that triggers the bug:
    # 'b):' at indent 0 does NOT start with ')', so the continuation regex
    # fails and the function span is truncated.
    counterexample = """def foo(a,
b):
    pass
"""

    tmpdir = None
    try:
        tmpdir = tempfile.mkdtemp(prefix="probe_extract_indent_")
        test_file = os.path.join(tmpdir, "test_func.py")
        with open(test_file, "w") as f:
            f.write(counterexample)

        from src.extract import extract_functions_from_file

        results = extract_functions_from_file(test_file, "python")

        if not results:
            print("CONFIRMED — no functions extracted from valid Python file")
            return 0

        name, source = results[0]

        # The spec says the span should cover the entire function body.
        # 'pass' is in the function body — it should be present in the
        # extracted source if the span is correct.
        if "pass" not in source:
            print(
                "CONFIRMED — function body truncated."
                f" Extracted source: {source!r}"
            )
            return 0
        else:
            print(
                "NOT CONFIRMED — full function body present."
                f" Extracted source: {source!r}"
            )
            return 0

    except ImportError as e:
        print(f"ERROR: Import failed — {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        if tmpdir is not None:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — function body truncated. Extracted source: 'def foo(a,\n'
```
