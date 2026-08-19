# Bug Report: _project_fingerprint

**Source file:** `src/languages/erlang-py/_project_fingerprint.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a tuple that deterministically and uniquely identifies the current state of the Erlang project located at proj_dir. Two calls to _project_fingerprint with the same proj_dir return equal tuples if and only if no file relevant to Erlang analysis under proj_dir has changed between the two calls. A file change is any modification to the file's content, size in bytes, or last-modification timestamp. The returned tuple does not depend on filesystem enumeration order or other non-deterministic factors.

---

### Actual Behavior

If the function terminates normally, the return value is a tuple (backend, records) such that:
- backend = _elp_argv(), identifying the current ELP backend version and configuration.
- records = tuple(sorted(set( (os.path.relpath(p, root), os.stat(p).st_size, os.stat(p).st_mtime_ns) for p in paths )))
  where root = os.path.abspath(proj_dir),
  paths = [p for p in _iter_project_files(root, {'.erl', '.hrl'})] + [os.path.join(root, name) for name in _PROJECT_CONFIG_FILES if os.path.isfile(os.path.join(root, name))],
  and sorted() orders by absolute path lexicographically.
Each record is a 3-tuple (rel_path, size, mtime_ns). The records are sorted, distinct, and include every .erl/.hrl source file recursively under root and every existing project configuration file named in _PROJECT_CONFIG_FILES located directly in root (non-recursive). The file metadata (size, modification time) reflects the state at the moment os.stat() is called. Under the given precondition, records is nonempty.
If any os.stat(), os.path.isfile(), filesystem iteration, or os.path.abspath() call raises an OSError (e.g., FileNotFoundError, PermissionError), the exception propagates and the function produces no return value; all local state is discarded.

---

## Code Evidence

Line 12

---

## Trigger Condition

The fingerprint is built only from file size and modification timestamp, ignoring file content. Thus a content modification that preserves size and mtime_ns goes undetected, violating the requirement that the fingerprint must change whenever any file's content changes (a file change is defined as any modification to content, size, or mtime).

---

## How to trigger the bug

Create an Erlang source file, compute its fingerprint, then modify the file content
while keeping the exact same byte count and restoring the original modification
timestamp. The second fingerprint is identical to the first despite the content
having changed.

### Inputs

| Parameter | Value |
|---|---|
| `proj_dir` | A temporary directory containing an `.erl` file |

### Expected (spec-correct) Output

The fingerprint should change (i.e., `fp1 != fp2`) because the file's content was modified.

### Actual (buggy) Output

The fingerprint remains unchanged (`fp1 == fp2`) because only `st_size` and `st_mtime_ns` contribute, and both were preserved.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile
from src.languages.erlang import _project_fingerprint

with tempfile.TemporaryDirectory() as tmpdir:
    src = os.path.join(tmpdir, "module.erl")
    with open(src, "w") as f:
        f.write("-module(module).\n-export([f/1]).\n\nf(X) -> X + 1.\n")
    fp1 = _project_fingerprint(tmpdir)

    # Modify content, preserve size and mtime_ns
    stat = os.stat(src)
    with open(src, "w") as f:
        f.write("-module(module).\n-export([f/1]).\n\nf(X) -> X * 1.\n")
    os.utime(src, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    fp2 = _project_fingerprint(tmpdir)

    print(fp1 == fp2)  # True — fingerprint did NOT detect the content change
```

---

## Probe Script

```python
"""Probe script for _project_fingerprint content-blindness bug.

Bug: _project_fingerprint uses only (size, mtime_ns) to detect file changes.
A content modification that preserves file size and mtime_ns escapes detection.
"""
import os
import sys
import tempfile

# Import the module via its public entry point.
# Must add repo root to sys.path so that 'src.languages.erlang' resolves.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from src.languages.erlang import _project_fingerprint

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an Erlang source file inside temp dir
        src_file = os.path.join(tmpdir, "module.erl")
        content_a = "-module(module).\n-export([f/1]).\n\nf(X) -> X + 1.\n"
        with open(src_file, "w") as f:
            f.write(content_a)

        # Record first fingerprint
        fp1 = _project_fingerprint(tmpdir)
        records1 = fp1[1]  # tuple of (rel_path, size, mtime_ns)

        # Capture original mtime_ns before modification
        stat1 = os.stat(src_file)

        # Modify file content but keep exact same byte length
        content_b = "-module(module).\n-export([f/1]).\n\nf(X) -> X * 1.\n"
        # Ensure same length
        assert len(content_a.encode("utf-8")) == len(content_b.encode("utf-8")), \
            f"Content lengths differ: {len(content_a)} vs {len(content_b)}"

        with open(src_file, "w") as f:
            f.write(content_b)

        # Restore original mtime_ns so that size + mtime match the first call
        os.utime(src_file, ns=(stat1.st_atime_ns, stat1.st_mtime_ns))

        # Record second fingerprint
        fp2 = _project_fingerprint(tmpdir)
        records2 = fp2[1]

        # Check if fingerprint is identical despite different content
        if fp1 == fp2:
            print(
                f"CONFIRMED — fingerprints equal despite content change: "
                f"fp1==fp2, size={stat1.st_size}=={stat2.st_size}, "
                f"mtime_ns={stat1.st_mtime_ns}=={stat2.st_mtime_ns}, "
                f"but content differs"
            )
        else:
            print(
                f"NOT CONFIRMED — fingerprints differ after content change: "
                f"fp1 != fp2"
            )

except AssertionError as e:
    print(f"NOT CONFIRMED — probe assertion failed: {e}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — fingerprints equal despite content change: fp1==fp2, size=49==49, mtime_ns=1785172396729580385==1785172396729580385, but content differs
```
