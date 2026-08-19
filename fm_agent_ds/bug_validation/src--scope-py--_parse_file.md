# Bug Report: _parse_file

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/scope-py/_parse_file.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a tuple (funcs_info, source_lines, classes). funcs_info is a list of dicts each containing keys for function name (string), start line (int), and end line (int), or None when no functions are found or parsing fails. source_lines is the file content as a list of strings (one per line), or None when the file cannot be read. classes is a list of dicts each containing at least a 'name' key (string), or None when no classes are found. Returns (None, None, None) when the file extension is not recognized in the language registry. Python source files are parsed via AST; if the AST parse fails, parsing falls back to the generic line-based extractor. Non-Python registered-language files are parsed via codegraph-backed extraction when proj_dir is provided and the file is indexed, falling back to regex-based extraction otherwise. The function does not raise exceptions; all parse failures and unreadable files produce a None-containing tuple without crashing.

---

### Actual Behavior

After execution, the function returns a 3-tuple (funcs, source_lines, classes). If the file extension is not present in EXT_TO_LANG (lang_key is None), a warning is logged and the return value is (None, None, None). If lang_key is 'python', the function calls _parse_python_file(src_path). On a successful AST parse (_parse_python_file returns funcs that is not None), the result is that same tuple, where funcs is a list of function-metadata dicts (each containing 'name', 'start_line', 'end_line'), source_lines is a list of strings (the file's lines), and classes is a list of class-metadata dicts (each with at least 'name'). These three lists may be empty but are never None in the successful branch. If the AST parse fails (indicating Python 2 syntax or a parse error), or if the language is any other supported language, the function falls back to _parse_generic_file(src_path, lang_key, proj_dir=proj_dir). _parse_generic_file returns either the same 3-tuple structure (with possibly empty lists) or (None, None, None) if the file cannot be read or parsed. The function never raises exceptions; all errors are handled by returning None. Formally, let L = EXT_TO_LANG.get(src_path.suffix.lstrip('.').lower()). Then:

result = 
   (None, None, None)                                 if L == None
   else if L == 'python'  _parse_python_file(src_path) = (F, S, C)  F  None
        then (F, S, C)
   else _parse_generic_file(src_path, L, proj_dir=proj_dir)

where each component of the result is either a list (of dicts or strings) or None, and the tuple is either all None or all lists.

---

## Code Evidence

Line 18: funcs, source_lines, classes = _parse_python_file(src_path)
Line 19: if funcs is not None:
Line 20:     return funcs, source_lines, classes
Line 21: # AST parse failed  fall back to the generic line-based extractor.

---

## Trigger Condition

The code uses funcs != None to decide if the AST parse succeeded, but _parse_python_file can return funcs=None after a successful AST parse when there are no top-level functions. The specification requires fallback to the generic extractor only when AST parsing fails, not when a valid Python file simply lacks top-level functions. For a .py file with a class but no functions, the code incorrectly falls back, losing the class information extracted by the AST.

---

## How to trigger the bug

The bug report claims that `_parse_python_file` can return `funcs=None` for a valid Python file with no top-level functions, causing `_parse_file` to incorrectly fall back to the generic extractor and lose class information.

However, inspection of `_parse_python_file` (in `src/scope.py`, lines 571–600) shows that on a successful AST parse, `funcs` is always initialized as an empty list (`funcs = []`) and returned as a list — never `None`. The only code path that returns `None` is the exception handler (line 579), which triggers only on actual parse failures (e.g., Python 2 syntax or malformed files).

Therefore, for a valid Python file with a class but no functions:
- `funcs` evaluates to `[]` (empty list, not `None`)
- `funcs is not None` evaluates to `True`
- The class information extracted by the AST is correctly returned

**The claimed bug does not exist.**

### Inputs

| Parameter | Value |
|-----------|-------|
| `src_path` | Temporary `.py` file containing two classes (`MyExampleClass`, `AnotherClass`) and no top-level functions |
| `proj_dir` | `None` (default) |

### Expected (spec-correct) Output

`([], <source_lines list>, [{'name': 'MyExampleClass', ...}, {'name': 'AnotherClass', ...}])`

### Actual (buggy) Output

`([], <source_lines list>, [{'name': 'MyExampleClass', ...}, {'name': 'AnotherClass', ...}])`

The actual output matches the expected output. Class information is preserved.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from pathlib import Path
from src.scope import _parse_file

test_file = Path("test_class_only.py")
test_file.write_text("""
class MyExampleClass:
    pass

class AnotherClass:
    pass
""")

funcs, source_lines, classes = _parse_file(test_file)
print(funcs)       # [] — empty list, NOT None
print(classes)     # [{'name': 'MyExampleClass', ...}, {'name': 'AnotherClass', ...}]
# actual (buggy) output: ([], [...], [{'name': 'MyExampleClass', ...}, {'name': 'AnotherClass', ...}])
# expected (correct) output: ([], [...], [{'name': 'MyExampleClass', ...}, {'name': 'AnotherClass', ...}])
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe script for bug src--scope-py--_parse_file.

Tests whether _parse_file correctly preserves class information
for a .py file containing a class but no top-level functions.
"""
import sys
import tempfile
from pathlib import Path

# Ensure the repo root is on sys.path so that 'src.scope' (and its
# relative imports like .extract) resolve correctly.
_repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_repo_root))

# Also ensure src.__init__.py is importable by adding the repo root.
# When run via `python3 fm_agent/bug_validation/probe_...py`, the
# script dir is on sys.path[0] but not the repo root.

try:
    from src.scope import _parse_file
except Exception as exc:
    print(f"ERROR: cannot import _parse_file: {exc}")
    sys.exit(1)

# ── Probe: .py file with a class but no top-level functions ──

# FM-Agent self-validation guard: all test fixtures live in a fresh
# temporary directory, never in the active-run fm_agent/ tree.
with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    test_file = tmp_path / "test_class_only.py"
    test_file.write_text("""
class MyExampleClass:
    \"\"\"A test class with no standalone functions in the module.\"\"\"
    pass

class AnotherClass:
    \"\"\"Second class, also no functions.\"\"\"
    pass
""", encoding="utf-8")

    try:
        result = _parse_file(test_file)
    except Exception as exc:
        print(f"ERROR: _parse_file raised: {exc}")
        sys.exit(1)

    funcs, source_lines, classes = result

    # ── Oracle ──
    # Spec claim: when AST parsing succeeds, funcs is a list (possibly empty),
    # source_lines is a list of strings, classes is a list (possibly empty).
    # The bug report claims that funcs can be None when there are no functions,
    # causing an incorrect fallback to _parse_generic_file and loss of classes.
    #
    # Expected (correct) behavior: funcs = [] (empty list, not None),
    # classes = [{'name': 'MyExampleClass', ...}, {'name': 'AnotherClass', ...}]

    bug_hit = (
        funcs is None
        or classes is None
        or (funcs is not None and classes is not None and len(classes) != 2)
    )

    if bug_hit:
        print(
            f"CONFIRMED — Bug reproduced: funcs={funcs!r}, "
            f"classes={classes!r}"
        )
        print(f"  funcs is None: {funcs is None}")
        print(f"  classes is None: {classes is None}")
        if classes is not None:
            print(f"  len(classes): {len(classes)}")
    else:
        class_names = [c['name'] for c in classes]
        print(
            f"NOT CONFIRMED — Class info correctly preserved. "
            f"funcs={funcs!r} (type={type(funcs).__name__}), "
            f"classes={class_names}"
        )
        print(f"  source_lines count: {len(source_lines)}")
```

### Probe Output

```
NOT CONFIRMED — Class info correctly preserved. funcs=[] (type=list), classes=['MyExampleClass', 'AnotherClass']
  source_lines count: 8
```
