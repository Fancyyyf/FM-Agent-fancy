# Bug Report: batch_extract

**Source file:** `src/languages/javascript-py/batch_extract.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If the codegraph backend is available, returns a dictionary mapping each absolute
    file path (string) to a list of (func_name, func_body) tuples, where func_name is
    a string and func_body is the source text of the function, for every JavaScript
    function definition found across all project files.
  - If the codegraph backend is unavailable, returns an empty dictionary.
  - Each key in the returned dictionary is an absolute filesystem path; each value is
    a non-empty list of tuples.

---

### Actual Behavior

If a CodeGraphExtractor instance cg is successfully created from proj_dir (i.e., cg is not None), the function returns the result of cg.get_functions_by_file("javascript", proj_dir), which is a dictionary mapping each absolute file path (string) of a JavaScript (.js/.jsx) file within proj_dir that contains any function definition to a list of (func_name: str, func_body: str) tuples for all function definitions found in that file. If cg is None (backend initialization fails), the function returns an empty dictionary {}. The returned dictionary maps exactly the JavaScript files that have function definitions; files with no functions are omitted. No other program state is modified.

---

## Code Evidence

Line 4: return cg.get_functions_by_file("javascript", proj_dir) if cg else {}

---

## Trigger Condition

The specification requires all JavaScript function definitions across all project files to be returned. However, the code only extracts functions from .js and .jsx files, ignoring other valid JavaScript source files such as .mjs, .cjs, etc. In the provided counterexample, script.mjs contains a function foo but is not included in the returned dictionary, violating the specification.

---

## How to trigger the bug

The probe attempted to reproduce the bug by creating a test project containing `.js`, `.mjs`, and `.cjs` files, each with a function definition. The `batch_extract` function was called on the project directory to check whether `.mjs` and `.cjs` files were included in the result.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `/tmp/bug_test_js_mjs` (containing `script.js`, `script.mjs`, `script.cjs`) |

### Expected (spec-correct) Output

All three files (`script.js`, `script.mjs`, `script.cjs`) should be included in the returned dictionary, each mapping to a list of their function definitions.

### Actual (buggy) Output

All three files were correctly included. Codegraph v1.4.1 assigns `.mjs` and `.cjs` files the same `'javascript'` language tag as `.js` files, and the `_CG_LANG` mapping `"javascript": ["javascript", "jsx"]` in `src/languages/codegraph.py` correctly covers them. The bug does not manifest with this version of codegraph.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.javascript import batch_extract

proj_dir = "/tmp/bug_test_js_mjs"
result = batch_extract(proj_dir)
# Files found: ['script.cjs', 'script.js', 'script.mjs']
# All three file types are correctly included.
```

---

## Probe Script

```py
import sys
import os

# Ensure snapshot root is on sys.path for `from src.languages.javascript import batch_extract`
ROOT = "/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot"
sys.path.insert(0, ROOT)

try:
    from src.languages.javascript import batch_extract

    proj_dir = "/tmp/bug_test_js_mjs"
    result = batch_extract(proj_dir)

    # Extract just the filenames from result keys
    files_found = sorted([os.path.basename(k) for k in result.keys()])

    # Check whether .mjs or .cjs are missing
    js_extensions_found = set(os.path.splitext(f)[1] for f in files_found)
    missing = [ext for ext in [".mjs", ".cjs"] if ext not in js_extensions_found]

    if missing:
        print(f"CONFIRMED — missing extensions: {missing}. Files found: {files_found}")
    else:
        print(f"NOT CONFIRMED — all JavaScript extensions present. Files found: {files_found}")
        for path, funcs in sorted(result.items()):
            print(f"  {os.path.basename(path)}: {[f[0] for f in funcs]}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — all JavaScript extensions present. Files found: ['script.cjs', 'script.js', 'script.mjs']
  script.cjs: ['bar']
  script.js: ['hello']
  script.mjs: ['foo']
```
