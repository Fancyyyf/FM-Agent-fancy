# Bug Report: _extracted_files_by_method

**Source file:** `/home/fancy/Projects_Vault/FM-Agent_qwen_7d490/fm_agent/extracted_functions/src/incremental_reasoner-py/_extracted_files_by_method.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a fresh mapping from function-name keys to lists of absolute paths of extracted-function files found under func_dir at any depth. Metadata sidecar files are excluded entirely: they appear neither as keys nor among the value lists. Every indexed file is registered under its full identifier stem, preserving any class qualifier; a file whose identifier carries a class qualifier is additionally registered under its bare trailing name after the last qualifier separator, so a lookup by either the qualified name or the bare name resolves to the same file paths, and a bare name shared by members of several classes maps to all of their files. A file without a class qualifier is registered under that single identifier only. Every value list contains only absolute paths of files that exist under func_dir at the time of the call. Returns an empty mapping when func_dir does not exist or is not a directory. No file is created, modified, or deleted.

---

### Actual Behavior

The function returns a `defaultdict(list)` mapping string keys to lists of absolute-path strings, constructed as follows.

**Path 1  `func_dir` is not an existing directory on disk (Line 1213):** The returned `defaultdict(list)` is empty (contains no keys). No filesystem walk is performed.

**Path 2  `func_dir` is an existing directory (Lines 1429):** `os.walk(func_dir)` is used to recursively enumerate every file entry. For each entry with base name `fn` located under directory `root`:

   If `_is_metadata_sidecar(fn)` returns True, the file is skipped entirely and contributes no entry to the index.

   Otherwise, let `abs_path = os.path.join(root, fn)`. Let `stem = fn[:fn.rfind('.')]` if `'.' in fn`, else `stem = fn` (i.e., the filename minus its final dot-extension, or the whole filename if it has no dot). Then:
     `abs_path` is appended to `index[stem]`.
     Let `bare = stem.split('::')[-1]` (the substring after the last `'::'`, or `stem` itself if no `'::'` is present).
     If `bare != stem` (i.e., the stem carried a `'::'`-separated class qualifier), `abs_path` is also appended to `index[bare]`.
     If `bare == stem` (a free function with no class qualifier), the file is registered under the single key `stem` only.

**Completeness and exclusivity:** The index contains exactly the entries described above and no others. Every non-sidecar file discovered at any depth under `func_dir` appears in the index; every metadata sidecar file is excluded. Each file's absolute path appears at most once per key (since `os.walk` visits each directory entry exactly once). A class-qualified extracted-function file (e.g., `LocalStorage::Flush.py`) is registered under both its full identifier (`LocalStorage::Flush`) and its bare tail (`Flush`). A free function file (e.g., `foo.py`) is registered under its single stem (`foo`).

**Formal specification:**
Let `W = {(root, fn) | os.walk(func_dir) yields fn in the files list of root}`.
Let `S = {(root, fn)  W | _is_metadata_sidecar(fn)}`.
For each `(root, fn)  S`, define:
  `p = os.path.join(root, fn)`
  `stem(fn) = fn[:fn.rfind('.')]` if `'.' in fn` else `fn`
  `bare(fn) = stem(fn).split('::')[-1]`
Then the returned mapping `index` satisfies:
  k, v: (k, v)  index.items()  (root,fn)S: k = stem(fn)  p  v, OR (root,fn)S: bare(fn)  stem(fn)  k = bare(fn)  p  v.
  For each key k, the list `index[k]` contains exactly the absolute paths of all non-sidecar files whose stem or bare name equals k, in `os.walk` traversal order.
  If `func_dir` is not a directory: k: k  index (index is empty).

No exceptions are raised by this function beyond those propagated by `os.walk` or `os.path.isdir` for OS-level errors; `_is_metadata_sidecar` is assumed total on any filename string.

---

## Code Evidence

Line 18: abs_path = os.path.join(root, fn)

(In `src/incremental_reasoner.py` this is line 542: `abs_path = os.path.join(root, fn)` inside the `os.walk(func_dir)` loop. The variable is named `abs_path`, but no `os.path.abspath()` / `os.path.realpath()` call is ever applied; the value is whatever `os.path.join(root, fn)` produces, which inherits the relativity/absoluteness of the caller-supplied `func_dir`.)

---

## Trigger Condition

The specification (Condition B) states: 'Every value list contains only absolute paths of files that exist under func_dir at the time of the call.' However, the code computes the path as os.path.join(root, fn) where root comes from os.walk(func_dir). When func_dir is a relative path (e.g., 'extracted_funcs'), os.walk yields relative root strings, and os.path.join produces a relative path. The code never calls os.path.abspath() or os.path.realpath() to ensure absoluteness. Thus, for any valid relative func_dir that exists as a directory, the returned lists contain relative paths, violating the specification's absolute-path requirement.

---

## How to trigger the bug

The probe builds a fresh temporary directory (never the active repo or its `fm_agent/` tree) containing a fixture extracted-functions directory with three files: a free-function file (`do_thing.py`), a class-qualified file (`LocalStorage::Flush.py`), and a metadata sidecar (`do_thing.info.json`). It `chdir`s into the temp directory and calls `_extracted_files_by_method` through the repository package entry point (`src.incremental_reasoner`) with the **relative** directory name `extracted_funcs/src--incremental_reasoner-py`. The function walks the relative path and joins relative `root` strings with filenames, so every value-list entry is a relative path such as `extracted_funcs/src--incremental_reasoner-py/do_thing.py` — none of them is absolute. The specification requires every value list to contain only **absolute** paths, regardless of how `func_dir` was supplied.

### Inputs

| Parameter | Value |
|-----------|-------|
| `func_dir` | `extracted_funcs/src--incremental_reasoner-py` (relative to a temp cwd containing `extracted_funcs/src--incremental_reasoner-py/{do_thing.py, LocalStorage::Flush.py, do_thing.info.json}`) |

### Expected (spec-correct) Output

```
{'do_thing': ['/tmp/<probe_dir>/extracted_funcs/src--incremental_reasoner-py/do_thing.py'],
 'LocalStorage::Flush': ['/tmp/<probe_dir>/extracted_funcs/src--incremental_reasoner-py/LocalStorage::Flush.py'],
 'Flush': ['/tmp/<probe_dir>/extracted_funcs/src--incremental_reasoner-py/LocalStorage::Flush.py']}
```

(every value-list entry is an absolute path; the sidecar appears nowhere)

### Actual (buggy) Output

```
{'do_thing': ['extracted_funcs/src--incremental_reasoner-py/do_thing.py'],
 'LocalStorage::Flush': ['extracted_funcs/src--incremental_reasoner-py/LocalStorage::Flush.py'],
 'Flush': ['extracted_funcs/src--incremental_reasoner-py/LocalStorage::Flush.py']}
```

(all value-list entries are relative — `os.path.isabs(p)` is `False` for every returned path)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile
from src.incremental_reasoner import _extracted_files_by_method

tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, "extracted_funcs", "src--incremental_reasoner-py"))
open(os.path.join(tmp, "extracted_funcs", "src--incremental_reasoner-py", "do_thing.py"), "w").close()
os.chdir(tmp)
index = _extracted_files_by_method(os.path.join("extracted_funcs", "src--incremental_reasoner-py"))
print(index["do_thing"])
# actual (buggy) output: ['extracted_funcs/src--incremental_reasoner-py/do_thing.py']
# expected (correct) output: ['/tmp/<tmpdir>/extracted_funcs/src--incremental_reasoner-py/do_thing.py']
```

---

## Probe Script

```py
"""Probe for bug src--incremental_reasoner-py--_extracted_files_by_method.

Spec claim (Condition B): "Every value list contains only absolute paths of
files that exist under func_dir at the time of the call."

Reported gap: the code computes ``abs_path = os.path.join(root, fn)`` where
``root`` comes from ``os.walk(func_dir)`` and never calls ``os.path.abspath``
/ ``os.path.realpath``. When ``func_dir`` itself is a RELATIVE path,
``os.walk`` yields relative roots and the produced "absolute" paths are in
fact relative, violating the specification.

Entry-point note: this is FM-Agent self-validation. Per the mandatory guard,
no FM-Agent workflow is started (no run_pipeline / run_incremental_pipeline /
main.py / CLI / OpenCode). The function under test is a private helper whose
only callers are internal incremental-pipeline helpers, so the probe imports
the repository package ``src`` (the package's public entry point module tree)
and exercises the helper directly with a temp-dir fixture. All runtime files
live under a fresh probe-owned temporary directory; the active repo and its
``fm_agent/`` directory are never used as the probe workspace.
"""

import os
import shutil
import sys
import tempfile

BUG_ID = "src--incremental_reasoner-py--_extracted_files_by_method"

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir)
)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def main():
    try:
        from src.incremental_reasoner import _extracted_files_by_method
    except Exception as e:
        print(f"ERROR: failed to import package entry point 'src': {e}")
        return 1

    workdir = tempfile.mkdtemp(prefix="fm_probe_extracted_files_")
    old_cwd = os.getcwd()
    try:
        # Fixture: an extracted-functions dir under the probe-owned temp dir.
        func_dir_rel = os.path.join("extracted_funcs", "src--incremental_reasoner-py")
        fixture_dir = os.path.join(workdir, func_dir_rel)
        os.makedirs(fixture_dir)

        free_file = os.path.join(fixture_dir, "do_thing.py")  # free function
        qualified_file = os.path.join(fixture_dir, "LocalStorage::Flush.py")  # class-qualified
        sidecar_file = os.path.join(fixture_dir, "do_thing.info.json")  # metadata sidecar
        for path in (free_file, qualified_file, sidecar_file):
            with open(path, "w") as f:
                f.write("")

        # Run from inside the temp workspace so the RELATIVE func_dir resolves
        # under the probe-owned directory (never under the active repo).
        os.chdir(workdir)
        try:
            index = _extracted_files_by_method(func_dir_rel)
        finally:
            os.chdir(old_cwd)

        keys = sorted(index.keys())
        all_paths = [p for paths in index.values() for p in paths]

        print(f"DEBUG func_dir (relative input): {func_dir_rel}")
        print(f"DEBUG returned keys: {keys}")
        for p in all_paths:
            print(f"DEBUG path: {p} | os.path.isabs: {os.path.isabs(p)}")

        # Sanity gate: the fixture must actually be indexed, the sidecar must
        # be excluded, and both lookup keys must exist. Otherwise the result
        # would be meaningless and this run must be classified as an error.
        if not index or not all_paths:
            print("ERROR: fixture was not indexed at all (empty mapping returned)")
            return 1
        if any(k.endswith((".spec.json", ".info.json")) or "do_thing.info" in k for k in keys):
            print("ERROR: metadata sidecar leaked into the index; fixture broken")
            return 1
        if "do_thing" not in index or "LocalStorage::Flush" not in index or "Flush" not in index:
            print(f"ERROR: expected keys missing from index: {keys}")
            return 1

        # Oracle: the specification (Condition B) requires EVERY value-list
        # entry to be an absolute path. The buggy implementation returns
        # relative paths whenever func_dir is relative.
        expected = "all returned paths are absolute (os.path.isabs == True)"
        non_abs = [p for p in all_paths if not os.path.isabs(p)]
        bug_reproduced = len(non_abs) == len(all_paths) and len(all_paths) > 0

        if bug_reproduced:
            print(
                f"CONFIRMED — all {len(all_paths)} returned path(s) are RELATIVE "
                f"(e.g. {all_paths[0]!r}) although spec requires absolute paths | "
                f"expected: {expected}"
            )
            return 0
        if non_abs:
            print(
                f"CONFIRMED — {len(non_abs)}/{len(all_paths)} returned path(s) are RELATIVE "
                f"(e.g. {non_abs[0]!r}) although spec requires absolute paths | "
                f"expected: {expected}"
            )
            return 0
        print(
            f"NOT CONFIRMED — all {len(all_paths)} returned path(s) were absolute as the "
            f"spec requires; actual matched expected for relative func_dir input"
        )
        return 0
    except Exception as e:
        print(f"ERROR: probe crashed: {type(e).__name__}: {e}")
        return 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
```

### Probe Output

```
DEBUG func_dir (relative input): extracted_funcs/src--incremental_reasoner-py
DEBUG returned keys: ['Flush', 'LocalStorage::Flush', 'do_thing']
DEBUG path: extracted_funcs/src--incremental_reasoner-py/do_thing.py | os.path.isabs: False
DEBUG path: extracted_funcs/src--incremental_reasoner-py/LocalStorage::Flush.py | os.path.isabs: False
DEBUG path: extracted_funcs/src--incremental_reasoner-py/LocalStorage::Flush.py | os.path.isabs: False
CONFIRMED — all 3 returned path(s) are RELATIVE (e.g. 'extracted_funcs/src--incremental_reasoner-py/do_thing.py') although spec requires absolute paths | expected: all returned paths are absolute (os.path.isabs == True)
```
