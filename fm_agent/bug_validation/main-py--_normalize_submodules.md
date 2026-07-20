# Bug Report: _normalize_submodules

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/main-py/_normalize_submodules.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of project-relative directory paths using "/" as the path separator, regardless of platform
- Each returned path is a valid existing subdirectory strictly inside proj_dir (not proj_dir itself)
- No returned path is a descendant of any other returned path: the result is a minimal covering set of the input submodules
- The list contains no duplicate entries
- The list is ordered by increasing path depth (number of "/" characters), with paths of equal depth ordered lexicographically
- If submodules is None or contains only empty/whitespace-only strings, returns an empty list
- Raises ValueError if any input path resolves outside proj_dir
- Raises ValueError if any input path resolves to proj_dir itself
- Raises ValueError if any input path does not correspond to an existing directory

---

### Actual Behavior

If submodules is falsy (None or empty), the function returns an empty list without raising exceptions. Otherwise, for each nonempty string `raw` in submodules: if its absolute path resides under proj_dir (not equal to proj_dir) and names an existing directory, its relative path with forward slashes is collected; otherwise a ValueError is raised (message indicates invalid submodule). If os.path.isdir raises OSError, that OSError propagates. After processing all entries, the collected relative paths are sorted primarily by increasing directory depth (number of '/') and secondarily lexicographically. From the sorted list, any path whose directory hierarchy has a prefix already in the result is omitted. The final sorted list of minimal, distinct relative paths (using '/') is returned. The arguments proj_dir and submodules are not mutated. Formal: proj_dir is a string and submodules is None, empty, or an iterable of strings (submodules falsy result = []) (submodules truthy raw submodules, raw.strip() '' [(inside_project candidate proj_dir isdir(candidate) rel normalized) (otherwise termination via ValueError or OSError)]) (normal execution finishes result = collapsed, where collapsed is the filter of sorted normalized by prefix containment).

---

## Code Evidence

Line 15: inside_project = os.path.commonpath([proj_dir, candidate]) == proj_dir

---

## Trigger Condition

The code uses a purely lexical (case-sensitive) comparison to determine whether candidate resides under proj_dir, via os.path.commonpath. On case-insensitive file systems, two paths differing only in case can refer to the same directory. The specification requires checking whether the input path *resolves* to a location outside proj_dir, which should respect the file system's case-insensitivity. As a result, a valid existing subdirectory with a differently cased prefix is incorrectly rejected, violating the expected behavior.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `/tmp/fm_probe_linkp_xxx/project_link` (a symlink to a real project directory) |
| submodules | `["/tmp/fm_probe_real_xxx/src"]` (a real path that resolves inside proj_dir) |

### Expected (spec-correct) Output

`["src"]` — the submodule resolves to a path inside proj_dir, so it should be accepted and normalized.

### Actual (buggy) Output

`ValueError` — `os.path.commonpath` performs a purely lexical (string-based) comparison of path prefixes. Since the symlink path (`/tmp/fm_probe_linkp_xxx/project_link`) and the real path (`/tmp/fm_probe_real_xxx/src`) diverge after `/tmp`, `os.path.commonpath` returns `/tmp` which does not equal `proj_dir`, causing an incorrect rejection.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, tempfile, shutil
sys.path.insert(0, '.')
from main import _normalize_submodules

# Create a real project dir with a submodule
real_proj = tempfile.mkdtemp(prefix="real_")
os.makedirs(os.path.join(real_proj, "src"))

# Create a symlink to it (used as proj_dir)
link_proj = os.path.join(tempfile.mkdtemp(prefix="linkp_"), "proj")
os.symlink(real_proj, link_proj)

# Use real path for submodule — different lexical prefix from proj_dir
_nomalize_submodules(link_proj, [os.path.join(real_proj, "src")])
# Raises ValueError: "--submodule must name subdirectories inside proj_dir"
# actual (buggy) output: ValueError
# expected (correct) output: ["src"]
```

---

## Probe Script

```python
"""Probe script for bug _normalize_submodules: os.path.commonpath lexical comparison rejects valid submodules when path prefixes differ (e.g. symlinks, case-insensitive filesystems)."""
import sys
import os
import tempfile
import shutil

# Add repo root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from main import _normalize_submodules

# Create a temp "real" project directory
real_proj = tempfile.mkdtemp(prefix="fm_probe_real_")
# Create a submodule directory inside it
src_dir = os.path.join(real_proj, "src")
os.makedirs(src_dir)

# Create a symlink pointing to the real project dir
# This will be used as proj_dir
link_parent = tempfile.mkdtemp(prefix="fm_probe_linkp_")
link_proj = os.path.join(link_parent, "project_link")
os.symlink(real_proj, link_proj)

try:
    # Call _normalize_submodules with symlink path as proj_dir,
    # but submodule path via the real (non-symlink) path.
    # os.path.commonpath sees different prefixes ("/tmp/fm_probe_linkp_/project_link"
    # vs "/tmp/fm_probe_real_") and returns "/tmp" instead of proj_dir,
    # incorrectly determining the submodule is outside.
    result = _normalize_submodules(link_proj, [src_dir])

    # If we reach here, no ValueError was raised
    print(f"NOT CONFIRMED — no ValueError raised, result: {result!r}")
    print("The function correctly identified the submodule as inside proj_dir")

except ValueError as e:
    # ValueError raised → the submodule was incorrectly rejected
    # os.path.commonpath did lexical comparison instead of resolving paths
    realpath_candidate = os.path.realpath(src_dir)
    realpath_proj = os.path.realpath(link_proj)
    # The candidate resolves inside proj_dir, so the ValueError is incorrect
    print(f"CONFIRMED — ValueError raised when submodule resolves inside proj_dir")
    print(f"  proj_dir (lexical):  {link_proj!r}")
    print(f"  proj_dir (realpath): {realpath_proj!r}")
    print(f"  candidate (lexical): {src_dir!r}")
    print(f"  candidate (realpath): {realpath_candidate!r}")
    print(f"  Error message: {e}")
    print(f"  The submodule resolves inside proj_dir, but was rejected because")
    print(f"  os.path.commonpath uses lexical (case-sensitive / non-resolving) comparison.")

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

finally:
    # Cleanup
    shutil.rmtree(real_proj, ignore_errors=True)
    shutil.rmtree(link_parent, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — ValueError raised when submodule resolves inside proj_dir
  proj_dir (lexical):  '/tmp/fm_probe_linkp_w8ohudvf/project_link'
  proj_dir (realpath): '/tmp/fm_probe_real_c_z8d0uw'
  candidate (lexical): '/tmp/fm_probe_real_c_z8d0uw/src'
  candidate (realpath): '/tmp/fm_probe_real_c_z8d0uw/src'
  Error message: --submodule must name subdirectories inside proj_dir, got: /tmp/fm_probe_real_c_z8d0uw/src
  The submodule resolves inside proj_dir, but was rejected because
  os.path.commonpath uses lexical (case-sensitive / non-resolving) comparison.
```
