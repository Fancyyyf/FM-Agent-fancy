# Bug Report: _function_spans

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/extract-py/_function_spans.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a pair (spans, raw_lines). raw_lines is a list of strings containing every line of the file, each with its trailing newline character preserved; the file is decoded with replacement characters on decoding error. spans is a list of (name, start_idx, end_idx) tuples where start_idx and end_idx are 0-based inclusive line indices delimiting each function definition found in the file. Each name is the function's canonicalized identifier  free of characters unsafe for filesystem paths and FQNs  with a disambiguation suffix appended when multiple distinct functions share the same canonicalized name: the first occurrence retains the bare canonicalized name, while each subsequent occurrence appends '_N' where N is the 1-based count of prior occurrences of that canonicalized name. The ordering of spans reflects the order in which function definitions appear in the source file.

---

### Actual Behavior

After successful execution (no uncaught exceptions), the function returns a tuple (spans, raw_lines) such that:

1. raw_lines = list of strings, each representing a line from the file at `filepath`, read via `f.readlines()` with `errors='replace'`. Newline characters are preserved exactly as present in the file.

2. Let `norm_lines` = [l.rstrip('\n').rstrip('\r') for l in raw_lines], `lang_cfg` = LANG_CONFIG[lang_key].

3. The detection source for function boundaries is determined as:
   - If `proj_dir is not None` and `function_spans_for_file(proj_dir, filepath, lang_key)` returns a list (i.e. not `None`), that list is used as `raw_funcs`.
   - Otherwise, if the return value from the codegraph call is `None` (or if `proj_dir is None`), then:
        - if `lang_cfg['body'] == 'brace'`: `raw_funcs` = _extract_functions_brace(norm_lines, lang_key, lang_cfg)
        - else: `raw_funcs` = _extract_functions_indent(norm_lines, lang_cfg).
   `raw_funcs` is a list of triples `(name, start_idx, end_idx)` with 0based inclusive line indices, possibly empty if no functions are found.

4. Let `name_counts` be an initially empty dictionary, and `spans` an empty list. For each `(name, start, end)` in `raw_funcs` in order:
   a. `cname` = canonicalize(name), which replaces all '/' characters with '_'.
   b. `count` = current value of `name_counts[cname]` (0 if not present).
   c. If `count == 0`, then `deduped` = `cname`; otherwise `deduped` = `f'{cname}_{count}'`.
   d. Append `(deduped, start, end)` to `spans`.
   e. `name_counts[cname]` = `count + 1`.

5. The function returns `(spans, raw_lines)`, where `spans` is the list of deduplicated named ranges and `raw_lines` the unmodified file lines.

Formally, let `DETECT` be the overall function extraction (as in step 3) that yields a sequence of m triples \\( (n_i, s_i, e_i) \\).  For \\( i=1 \\dots m \\), define \\( C_i = \\texttt{canonicalize}(n_i) \\), \\( k_i = |\\{ j < i \\mid \\... (line truncated to 2000 chars)

---

## Code Evidence

Line 15: with open(filepath, "r", errors="replace") as f:

---

## Trigger Condition

The code opens the file in default text mode without newline='', causing universal newline translation. Consequently, raw_lines will have '\n' line endings instead of the file's original '\r\n' endings, violating the requirement that each line preserve its trailing newline character.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| filepath | Path to a Python source file with CRLF (`\r\n`) line endings |
| lang_key | `"python"` |
| proj_dir | `None` (to bypass codegraph and use regex fallback) |

### Expected (spec-correct) Output

```
(raw_lines containing '\r\n' endings, e.g. ['class Foo:\r\n', '    def bar(self):\r\n', '        pass\r\n'])
```

### Actual (buggy) Output

```
(raw_lines containing only '\n' endings, e.g. ['class Foo:\n', '    def bar(self):\n', '        pass\n'])
```

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, tempfile
sys.path.insert(0, '/home/fancy/Projects_Vault/FM-Agent')
from src.extract import _function_spans

with tempfile.TemporaryDirectory() as tmpdir:
    tf = os.path.join(tmpdir, "test.py")
    with open(tf, "wb") as f:
        f.write(b"class Foo:\r\n    def bar(self):\r\n        pass\r\n")
    spans, raw_lines = _function_spans(tf, "python", proj_dir=None)
    for l in raw_lines:
        assert l.endswith('\r\n'), f"Lost CRLF: {l!r}"
    print("PASSED")
# actual (buggy) output: AssertionError — raw_lines only have '\n'
// expected (correct) output: PASSED
```

---

## Probe Script

```python
"""
Probe script for bug src--extract-py--_function_spans
Tests whether _function_spans preserves trailing newline characters
when the source file uses CRLF line endings.
"""
import sys
import os
import tempfile

try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from src.extract import _function_spans

    # Create a temporary file with \r\n line endings in a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test_probe.py")
        with open(test_file, "wb") as f:
            f.write(b"class Foo:\r\n")
            f.write(b"    def bar(self):\r\n")
            f.write(b"        pass\r\n")

        # Call _function_spans with proj_dir=None to avoid codegraph path
        spans, raw_lines = _function_spans(test_file, "python", proj_dir=None)

        # Check if raw_lines preserves the original \r\n endings
        has_crlf = any(line.endswith('\r\n') for line in raw_lines)

        # The spec claims raw_lines should preserve trailing newline characters.
        # Universal newline translation (no newline='') converts \r\n -> \n.
        # So the buggy behavior means NO raw_lines have \r\n.
        if has_crlf:
            print(f"NOT CONFIRMED — raw_lines preserved \\r\\n ending: {[repr(l) for l in raw_lines]}")
        else:
            print(f"CONFIRMED — raw_lines lost \\r\\n (universal newline translation): {[repr(l) for l in raw_lines]}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — raw_lines lost \r\n (universal newline translation): ["'class Foo:\\n'", "'    def bar(self):\\n'", "'        pass\\n'"]
```
