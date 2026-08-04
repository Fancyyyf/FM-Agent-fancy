# Bug Report: _reconcile_extracted_dir

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_reconcile_extracted_dir.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Identifies the extracted-function directory under extracted_functions/ corresponding to abs_src. When this directory does not exist on disk, returns immediately with no side effects. Otherwise, determines the set of function identifiers currently produced by the extraction backend for abs_src. For every file under the corresponding extracted-function directory whose base filename (with .spec.json or .info.json suffix stripped) does not match any such identifier, removes that file from disk  including orphaned .spec.json and .info.json sidecars. When abs_src does not exist on disk, removes the entire corresponding extracted-function directory and all files within it. When abs_src exists but yields no function identifiers, removes all extracted function files and their sidecars from the corresponding directory. After removal, prunes every empty subdirectory under the extracted-function directory (deepest-first traversal). The extracted-function directory itself is preserved even when emptied. Does not modify or create any source file at abs_src. The set of function identifiers is computed using the same backend (codegraph or regex) that produced the original extracted-function files, ensuring identifier naming is consistent.

---

### Actual Behavior

After the function executes, if it returns normally (no exception), the state of the directory tree rooted at func_dir (derived from proj_dir and abs_src) is updated as follows.

Let D, ext = _src_rel_to_func_dir(proj_dir, abs_src).
If D is not a directory, the function returns immediately and the file system is unchanged.

Otherwise, let VALID be computed as:
   lang_key = EXT_TO_LANG.get(ext)
   if lang_key is not None and os.path.isfile(abs_src) in the initial state:
        spans = _function_spans(abs_src, lang_key, proj_dir)[0]
        For each (ident, _, _) in spans:
            function_path = os.path.abspath(os.path.join(D, ident) + ('.' + ext if ext else ''))
            VALID = {function_path, function_path+'.spec.json', function_path+'.info.json'} for all spans, unioned.
   else:
        VALID = empty set.

Then the function walks D recursively and deletes every regular file whose absolute path is not in VALID. After that, it walks D bottom-up and removes any subdirectory of D (excluding D itself) that is empty (i.e., os.listdir returns empty).

Upon normal termination, the final file system state F satisfies:
  For all absolute paths p under D:
    * If p was a regular file in the initial state: p exists in F iff p  VALID.
    * If p was a directory in the initial state: p exists in F iff p = D or p contains at least one regular file or subdirectory that exists in F.

If an exception (e.g., OSError, PermissionError) is raised during deletion or pruning, the function terminates prematurely; in that case the file system may be partially modified (some files/directories deleted, others not) and the exception propagates.

---

## Code Evidence

Line 25-33: The deletion and pruning logic removes files and empty subdirectories but never removes func_dir itself when abs_src does not exist.

---

## Trigger Condition

The specification explicitly states: 'When abs_src does not exist on disk, removes the entire corresponding extracted-function directory and all files within it.' The code only empties the directory, leaving an empty directory behind, which violates this requirement.

---

## How to trigger the bug

When a source file has been deleted (abs_src no longer exists on disk), `_reconcile_extracted_dir` is supposed to remove the entire corresponding extracted-function directory under `fm_agent/extracted_functions/`. However, the function only cleans up the files and subdirectories within `func_dir` but never removes `func_dir` itself. The directory pruning loop at line 36 explicitly skips `func_dir` (`if root != func_dir`), leaving an empty orphaned directory behind. This contradicts the specification which requires complete removal of the extracted-function directory (including func_dir itself) when the source file no longer exists.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Path to a mock project root containing `fm_agent/extracted_functions/src/foo-py/` |
| `abs_src` | Path to `src/foo.py` under `proj_dir` (file does NOT exist on disk) |

### Expected (spec-correct) Output

`func_dir` (the extracted-function directory) is removed from disk — `os.path.isdir(func_dir)` returns `False`.

### Actual (buggy) Output

`func_dir` remains on disk as an empty directory — `os.path.isdir(func_dir)` returns `True`. All files and subdirectories within it were removed, but the top-level `func_dir` itself was preserved.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile, shutil, sys
sys.path.insert(0, ".")
from src.incremental_reasoner import _reconcile_extracted_dir

tmpdir = tempfile.mkdtemp()
proj_dir = os.path.join(tmpdir, "proj")
func_dir = os.path.join(proj_dir, "fm_agent", "extracted_functions", "src", "foo-py")
os.makedirs(func_dir)
with open(os.path.join(func_dir, "bar.py"), "w") as f:
    f.write("dummy")
with open(os.path.join(func_dir, "bar.py.spec.json"), "w") as f:
    f.write("{}")

abs_src = os.path.join(proj_dir, "src", "foo.py")  # does not exist

_reconcile_extracted_dir(proj_dir, abs_src)

print("func_dir exists:", os.path.isdir(func_dir))
# actual (buggy) output: True
# expected (correct) output: False
```

---

## Probe Script

```python
"""Probe: _reconcile_extracted_dir does not remove func_dir when abs_src is deleted.

Spec claim: "When abs_src does not exist on disk, removes the entire corresponding
extracted-function directory and all files within it."

Actual behavior: The function empties func_dir (removes files and prunes subdirs)
but leaves func_dir itself on disk.

This probe creates a temp workspace with a populated extracted-functions directory,
calls _reconcile_extracted_dir with a non-existent abs_src, and verifies that
func_dir is NOT removed (confirming the bug).
"""

import os
import sys
import tempfile
import shutil

# Ensure repo root is on sys.path so 'src' is importable
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, repo_root)

try:
    from src.incremental_reasoner import _reconcile_extracted_dir
except Exception as e:
    print(f"ERROR: Failed to import _reconcile_extracted_dir: {e}")
    sys.exit(1)

def main():
    # Create a fresh temp directory as the probe workspace (per FM-Agent self-validation guard)
    tmp = tempfile.mkdtemp(prefix="probe_reconcile_")
    proj_dir = os.path.join(tmp, "mock_proj")

    # Create the extracted-functions directory structure for a source file "src/foo.py"
    func_dir = os.path.join(proj_dir, "fm_agent", "extracted_functions", "src", "foo-py")
    sub_dir = os.path.join(func_dir, "nested")

    os.makedirs(sub_dir, exist_ok=True)

    # Create some dummy extracted files to be cleaned up
    with open(os.path.join(func_dir, "bar.py"), "w") as f:
        f.write("# extracted function bar")
    with open(os.path.join(func_dir, "bar.py.spec.json"), "w") as f:
        f.write('{"spec": "bar"}')
    with open(os.path.join(func_dir, "bar.py.info.json"), "w") as f:
        f.write('{"info": "bar"}')
    with open(os.path.join(sub_dir, "baz.py"), "w") as f:
        f.write("# extracted function baz")
    with open(os.path.join(sub_dir, "baz.py.spec.json"), "w") as f:
        f.write('{"spec": "baz"}')

    # abs_src points to a source file that does NOT exist (simulating deletion)
    abs_src = os.path.join(proj_dir, "src", "foo.py")  # deliberately not created

    try:
        _reconcile_extracted_dir(proj_dir, abs_src)
    except Exception as e:
        print(f"ERROR: _reconcile_extracted_dir raised: {e}")
        shutil.rmtree(tmp, ignore_errors=True)
        sys.exit(1)

    # Now check: per the spec, func_dir SHOULD be removed (and therefore not exist).
    # The bug is that the code does NOT remove func_dir.
    func_dir_exists = os.path.isdir(func_dir)

    # Cleanup
    shutil.rmtree(tmp, ignore_errors=True)

    if func_dir_exists:
        print("CONFIRMED — func_dir still exists after reconcile (spec requires removal)")
    else:
        print("NOT CONFIRMED — func_dir was removed as expected by spec")

if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — func_dir still exists after reconcile (spec requires removal)
```
