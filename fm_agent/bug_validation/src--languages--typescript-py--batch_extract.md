# Bug Report: batch_extract

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/typescript-py/batch_extract.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If codegraph is available: returns a dict whose keys are absolute file
    paths to TypeScript source files within proj_dir, and whose values are
    lists of (function_name, function_body) tuples for every top-level
    function declared in the corresponding file.
  - Each function_name is the identifier of the function declaration.
  - Each function_body is the full source text of the function definition.
  - If proj_dir contains no TypeScript files with top-level functions:
    returns an empty dict.
  - If codegraph is unavailable: returns an empty dict {}.

---

### Actual Behavior

Returns a dictionary. If cg = CodeGraphExtractor.from_proj_dir(proj_dir) is not None, the result is cg.get_functions_by_file('typescript', proj_dir), i.e., a dict mapping absolute file paths (str) of TypeScript source files under proj_dir to lists of (function_name: str, function_body: str) tuples. Otherwise, returns an empty dict {}.

---

## Code Evidence

Line 4: return cg.get_functions_by_file('typescript', proj_dir) if cg else {}

---

## Trigger Condition

The specification requires the output to contain only top-level functions, but the code unconditionally returns the result of get_functions_by_file, which includes all function declarations (including nested/non-top-level functions) found in TypeScript files. A project containing a nested function results in an output that violates the specification by including that function.

---

## How to trigger the bug

The `batch_extract` function delegates entirely to `CodeGraphExtractor.get_functions_by_file`, which queries codegraph's SQLite database for all nodes where `kind IN ('function', 'method')`. Codegraph stores nested functions (e.g., `function nestedInner()` declared inside `function outer()`) with `kind='function'`, identical to top-level functions. Since `batch_extract` performs no filtering, nested functions are returned alongside top-level ones, violating the spec.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A directory containing a TypeScript file with nested function declarations, indexed by codegraph |

### Expected (spec-correct) Output

`{"/path/to/index.ts": [("topLevel", "function topLevel..."), ("outer", "function outer..."), ("arrowTop", "const arrowTop = ...")]}` — only top-level functions.

### Actual (buggy) Output

`{"/path/to/index.ts": [("topLevel", ...), ("outer", ...), ("nestedInner", ...), ("arrowTop", ...)]}` — includes the nested `nestedInner` function.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.typescript import batch_extract

# Create a temp TypeScript project with a nested function
import tempfile, os, subprocess
tmpdir = tempfile.mkdtemp()
with open(os.path.join(tmpdir, "index.ts"), "w") as f:
    f.write("function topLevel() {}\n"
            "function outer() {\n"
            "  function nestedInner() {}\n"
            "  nestedInner();\n"
            "}\n")
subprocess.run(["codegraph", "init"], cwd=tmpdir, check=True)
result = batch_extract(tmpdir)
for filepath, funcs in result.items():
    for name, _body in funcs:
        print(f"  {name}")
# actual (buggy) output: topLevel, outer, nestedInner
# expected (correct) output: topLevel, outer
```

---

## Probe Script

```python
import sys
import os
import tempfile
import subprocess
import shutil

BUG_ID = "src--languages--typescript-py--batch_extract"

def main():
    # Add the repo root to sys.path so we can import from src.languages.typescript
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Create a temp TypeScript project with a nested function
    tmpdir = tempfile.mkdtemp(prefix="bug_probe_")
    try:
        # Write a TypeScript file with both top-level and nested functions
        ts_content = """\
function topLevel(): void {
  console.log("top level");
}

function outer(): void {
  function nestedInner(): void {
    console.log("nested");
  }
  nestedInner();
}

const arrowTop = (): void => {
  console.log("arrow top");
};
"""
        ts_path = os.path.join(tmpdir, "index.ts")
        with open(ts_path, "w") as f:
            f.write(ts_content)

        # Run codegraph init to index the project
        result = subprocess.run(
            ["codegraph", "init"], cwd=tmpdir, capture_output=True, text=True
        )
        if result.returncode != 0:
            print("ERROR: codegraph init failed:", result.stderr[:300])
            sys.exit(1)

        # Check that codegraph.db was created
        db_path = os.path.join(tmpdir, ".codegraph", "codegraph.db")
        if not os.path.exists(db_path):
            print("ERROR: codegraph did not produce codegraph.db")
            sys.exit(1)

        # Import batch_extract from the public API
        from src.languages.typescript import batch_extract

        # Call batch_extract on the temp project
        result = batch_extract(tmpdir)

        # Find all function names extracted
        all_func_names = []
        for filepath, funcs in result.items():
            for name, body in funcs:
                all_func_names.append(name)

        # Spec says: only TOP-LEVEL functions should be returned
        # "nestedInner" is a nested function and should NOT appear
        # "topLevel", "outer", "arrowTop" are top-level and SHOULD appear

        top_level_expected = {"topLevel", "outer", "arrowTop"}
        nested_names = set(all_func_names) - top_level_expected

        if nested_names:
            # Bug confirmed: nested functions were included
            print(f"CONFIRMED — actual includes nested function(s): {sorted(nested_names)!r} "
                  f"| expected only top-level: {sorted(top_level_expected)!r}")
            print(f"  full output: {sorted(all_func_names)}")
        else:
            print(f"NOT CONFIRMED — actual matched expected (only top-level): {sorted(all_func_names)}")

    except ImportError as e:
        print(f"ERROR: Import failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        shutil.rmtree(tmpdir, ignore_errors=True)

if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — actual includes nested function(s): ['nestedInner'] | expected only top-level: ['arrowTop', 'outer', 'topLevel']
  full output: arrowTop, nestedInner, outer, topLevel
  expected:     topLevel, outer, arrowTop (top-level only)
```
