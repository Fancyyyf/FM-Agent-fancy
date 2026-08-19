# Bug Report: _iter_project_files

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/erlang-py/_iter_project_files.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a lazy iterator that yields absolute-path strings, one at a time. Each yielded string is the absolute path of a regular file whose file extension, compared case-insensitively, is a member of suffixes, found under the directory tree rooted at proj_dir. Subdirectories whose name, compared case-insensitively, matches any name in a predetermined set of pipeline workspace artifact directory names are pruned from the traversal  no files from within those subdirectories are yielded. Each matching file is yielded exactly once. Directories, symbolic links, and files whose extension is not in suffixes are not yielded. The iteration order depends on the order in which the filesystem enumeration encounters files. When no matching files exist under proj_dir, the iterator is exhausted on the first call to next().

---

### Actual Behavior

The function returns a generator object. When the generator is iterated, it yields the absolute paths (as strings) of all files within the directory tree rooted at `proj_dir` whose file extension (in lowercase) is in `suffixes`. Directories whose lowercased name is in the global set `_SKIP_DIRS` are not traversed, so files inside them are omitted. Yielding occurs in top-down order as determined by `os.walk`. More formally: Let `SKIP = _SKIP_DIRS`. For each yielded path `p`, there exists a root directory `r` and a file name `f` such that `p = os.path.abspath(os.path.join(r, f))`, `r` is reachable from `proj_dir` by a sequence of subdirectories where each subdirectory's lowercase name is not in `SKIP`, and `Path(f).suffix.lower() in suffixes`. Conversely, every such file will eventually be yielded exactly once by the generator.

---

## Code Evidence

Line 5: `if Path(filename).suffix.lower() in suffixes:`

---

## Trigger Condition

The code yields files based only on extension, ignoring the file type. The specification explicitly states that symbolic links are not yielded. A symbolic link with a matching extension will be incorrectly yielded.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | Path to a temporary directory containing one real `.erl` file and one symlink to it (also `.erl`) |
| suffixes | `{".erl"}` |

### Expected (spec-correct) Output

Only the real file should be yielded: `[<abs_path_to_real.erl>]`. The symbolic link must NOT appear in the output.

### Actual (buggy) Output

Both the real file and the symbolic link are yielded: `[<abs_path_to_real.erl>, <abs_path_to_symlink.erl>]`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import sys
import tempfile

sys.path.insert(0, ".")  # ensure src/ is on path
from src.languages.erlang import _iter_project_files

tmpdir = tempfile.mkdtemp(prefix="bug_probe_")
real_path = os.path.join(tmpdir, "real.erl")
with open(real_path, "w") as f:
    f.write("-module(real).\n")

symlink_path = os.path.join(tmpdir, "symlink.erl")
os.symlink(real_path, symlink_path)

yielded = list(_iter_project_files(tmpdir, {".erl"}))
symlink_abs = os.path.abspath(symlink_path)
print(f"Symlink yielded: {symlink_abs in yielded}")  # True (bug)
print(f"All yielded: {yielded}")

# Cleanup
os.unlink(symlink_path); os.unlink(real_path); os.rmdir(tmpdir)
# actual (buggy) output: Symlink yielded: True
# expected (correct) output: Symlink yielded: False
```

---

## Probe Script

```python
"""Probe script for bug: _iter_project_files yields symlinks despite spec forbidding it."""
import os
import sys
import tempfile

# Add the project root to sys.path so `from src.languages.erlang import ...` works
proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, proj_root)

try:
    from src.languages.erlang import _iter_project_files

    # Create a temporary directory for test fixtures
    tmpdir = tempfile.mkdtemp(prefix="bug_probe_")

    # Create a real file with .erl extension
    real_path = os.path.join(tmpdir, "real.erl")
    with open(real_path, "w") as f:
        f.write("-module(real).\n")

    # Create a symlink to that file (also with .erl extension in the link name)
    symlink_path = os.path.join(tmpdir, "symlink.erl")
    os.symlink(real_path, symlink_path)

    # Call _iter_project_files with {".erl"} suffix set
    yielded = list(_iter_project_files(tmpdir, {".erl"}))

    # Resolve to absolute paths for comparison
    symlink_abs = os.path.abspath(symlink_path)
    real_abs = os.path.abspath(real_path)

    # The spec says symlinks should NOT be yielded.
    # If the symlink path appears in the output, the bug is confirmed.
    symlink_yielded = symlink_abs in yielded
    real_yielded = real_abs in yielded

    # Clean up temp dir
    os.unlink(symlink_path)
    os.unlink(real_path)
    os.rmdir(tmpdir)

    expected = "symlink NOT yielded (per spec)"
    actual = f"yielded paths: {yielded}"

    if symlink_yielded:
        print(f"CONFIRMED — symlink was incorrectly yielded: {symlink_abs}")
        print(f"  Real file yielded: {real_yielded}")
        print(f"  Expected: {expected}")
    else:
        print(f"NOT CONFIRMED — symlink not in output (spec-compliant). yielded: {yielded}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — symlink was incorrectly yielded: /tmp/bug_probe_z4apx5cb/symlink.erl
  Real file yielded: True
  Expected: symlink NOT yielded (per spec)
```
