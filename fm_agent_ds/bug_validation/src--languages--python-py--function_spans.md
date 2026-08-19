# Bug Report: function_spans

**Source file:** `fm_agent/extracted_functions/src/languages/python-py/function_spans.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of (name, start_idx, end_idx) tuples, one per top-level function defined in filepath, where start_idx and end_idx are 0-indexed inclusive line numbers bounding each function's body, if a CodeGraph index exists for proj_dir and covers the file. Returns None if CodeGraph is unavailable or the file is not indexed, signalling the caller to fall back to regex-based extraction

---

### Actual Behavior

Given that proj_dir is a directory path and filepath is a path to a Python source file contained within proj_dir, the function may terminate normally or raise an exception. If it terminates normally, the return value R satisfies: ( ( cg : cg = CodeGraphExtractor.from_proj_dir(proj_dir)  cg is falsy)  R = None )  ( ( cg : cg = CodeGraphExtractor.from_proj_dir(proj_dir)  cg is truthy)  ( (cg.get_function_spans('python', filepath) = None)  R = None )  ( (cg.get_function_spans('python', filepath) = L where L is a list)  R = L ) ). Here L is a list of tuples (name, start_idx, end_idx) where name is a string, start_idx and end_idx are integers representing 0-indexed inclusive line indices of a function definition in filepath; the list may be empty. If an exception E is raised during the evaluation of CodeGraphExtractor.from_proj_dir(proj_dir) or during the call to cg.get_function_spans('python', filepath) when cg is truthy, the function raises E.

---

## Code Evidence

Line 8: return cg.get_function_spans("python", filepath) if cg else None

---

## Trigger Condition

Specification requires only top-level functions, but the code returns whatever get_function_spans provides, which may include nested functions, violating the specification.

---

## How to trigger the bug

The `function_spans` wrapper in `src/languages/python.py` delegates to `CodeGraphExtractor.get_function_spans("python", filepath)`, which queries codegraph's SQLite database with:

```sql
SELECT name, qualified_name, start_line, end_line
FROM nodes
WHERE kind IN ('function', 'method') AND language IN ('python') AND file_path = ?
ORDER BY start_line
```

This query has no filter for nesting depth — it returns all functions and methods regardless of whether they are top-level or nested inside other functions. The `_extraction_ident` helper preserves scoped identifiers like `"_parse_spec_check_json::_nonempty_string"` for nested functions, making them distinguishable in the output.

For `src/prompts.py`, codegraph stores `_nonempty_string` (lines 64-65) inside `_parse_spec_check_json` (lines 32-94) as a function node with `kind='function'` and `qualified_name='_parse_spec_check_json::_nonempty_string'`. The `get_function_spans` query returns it alongside top-level functions.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `/home/fancy/Projects_Vault/FM-Agent` (project root containing `.codegraph/codegraph.db`) |
| `filepath` | `/home/fancy/Projects_Vault/FM-Agent/src/prompts.py` (Python source file with nested function `_nonempty_string` at lines 64-65 inside `_parse_spec_check_json` at lines 32-94) |

### Expected (spec-correct) Output

Top-level functions only: `['_load_spec_check_json', '_parse_spec_check_json', '_parse_post_condition_json', '_generate_block_post_condition', '_check_post_implies_spec']`

### Actual (buggy) Output

Includes nested function: `['_load_spec_check_json', '_parse_spec_check_json', '_parse_spec_check_json::_nonempty_string', '_parse_post_condition_json', '_generate_block_post_condition', '_check_post_implies_spec']`

The nested function `_parse_spec_check_json::_nonempty_string` should not be present.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
from src.languages.python import function_spans

proj_dir = os.getcwd()  # Must contain .codegraph/codegraph.db
filepath = os.path.join(proj_dir, "src", "prompts.py")
spans = function_spans(proj_dir, filepath)

names = [n for n, _, _ in spans]
nested = [n for n in names if "::" in n]
# nested = ['_parse_spec_check_json::_nonempty_string'] — BUG
# spec requires only top-level functions (no "::" in names)
```

---

## Probe Script

```python
import sys
import os

# The project root is where we run the probe from. Add it to the Python path
# so that "from src.languages.python import function_spans" resolves.
proj_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, proj_dir)

try:
    from src.languages.python import function_spans
except Exception as e:
    print(f'ERROR: Failed to import function_spans: {e}')
    sys.exit(1)

# Use src/prompts.py which has _nonempty_string (line 64-65) nested inside
# _parse_spec_check_json (line 32-94).
# Codegraph stores nested functions with qualified_name like
# "_parse_spec_check_json::_nonempty_string", which _extraction_ident
# preserves in the returned name.
filepath = os.path.join(proj_dir, 'src', 'prompts.py')

try:
    spans = function_spans(proj_dir, filepath)

    if spans is None:
        print('NOT CONFIRMED — function_spans returned None (codegraph not available or file not indexed)')
        sys.exit(0)

    # The spec says "one per top-level function". A nested function
    # (defined inside another function) should NOT appear. The _extraction_ident
    # function in codegraph.py returns "Parent::Nested" for nested functions,
    # keeping the qualified scope. Top-level functions have no "::" in their name.
    all_names = [name for name, _start, _end in spans]
    nested = [n for n in all_names if '::' in n]
    top_level = [n for n in all_names if '::' not in n]

    has_nested = len(nested) > 0

    if has_nested:
        # This is the buggy behavior: nested functions are returned when the
        # spec says only top-level functions should be.
        print(f'CONFIRMED — nested function(s) returned by function_spans')
        print(f'  Top-level functions: {top_level}')
        print(f'  Nested functions (BUG — should not be present): {nested}')
        print(f'  Spec requires only top-level functions, but {len(nested)} nested function(s) are returned.')
    else:
        print(f'NOT CONFIRMED — no nested functions found.')
        print(f'  All functions: {all_names}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — nested function(s) returned by function_spans
  Top-level functions: ['_load_spec_check_json', '_parse_spec_check_json', '_parse_post_condition_json', '_generate_block_post_condition', '_check_post_implies_spec']
  Nested functions (BUG — should not be present): ['_parse_spec_check_json::_nonempty_string']
  Spec requires only top-level functions, but 1 nested function(s) are returned.
```
