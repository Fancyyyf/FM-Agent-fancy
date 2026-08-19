# Bug Report: _normalized_relative_path

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_normalized_relative_path.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a normalized relative path derived from path relative to proj_dir. If path is not an absolute path, it is first resolved to an absolute path by joining it with proj_dir. The absolute path is then converted to a path relative to proj_dir. The resulting relative path is further normalized: single-dot (.) segments are eliminated, parent-directory (..) segments are resolved against their ancestor components, consecutive path separators are collapsed to a single forward slash, and case normalization appropriate to the filesystem is applied (lowercased on case-insensitive filesystems, unchanged on case-sensitive filesystems). The returned string contains no leading path separator, no leading dot segments, and no redundant separators.

---

### Actual Behavior

Returns a case-normalized, normalized project-relative path string that addresses the file specified by `path` relative to `proj_dir`. If `path` is absolute, it directly identifies the target file; if relative, the target is the concatenation of `proj_dir` and `path` using the platform's path separator. The returned string is the relative path from `proj_dir` to that target, with all redundant separators, '.' components, and '..' components collapsed by path normalization, followed by case normalization (lowercasing on case-insensitive filesystems, unchanged on case-sensitive ones). No side effects and no exceptions for valid inputs. Formally: result = normcase(normpath(relpath(if isabs(path) then path else join(proj_dir, path), proj_dir))).

---

## Code Evidence

Line 3: absolute_path = path if os.path.isabs(path) else os.path.join(proj_dir, path)
Line 4: relative_path = os.path.relpath(absolute_path, proj_dir)
Line 5: return os.path.normcase(os.path.normpath(relative_path))

---

## Trigger Condition

The specification requires the returned path to contain no leading dot segments. When path is an absolute path not under proj_dir (e.g., '/home/user' with proj_dir='/home/user/project'), the result is '../user', which starts with '..', a leading dot segment.

---

## How to trigger the bug

The function `_normalized_relative_path` calls `os.path.relpath(absolute_path, proj_dir)`. When `absolute_path` is outside `proj_dir`, `os.path.relpath` returns a path containing `..` components to represent the parent-directory traversal needed to reach the file. These `..` segments are preserved through `os.path.normpath()` because they are semantically meaningful (they point to parent directories). The spec, however, claims the result contains "no leading dot segments" — but `..` is a dot segment and it appears at the start of the returned path.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `/tmp/<tmpdir>/project` |
| `path` (absolute) | `/tmp/<tmpdir>/outside_file` |

### Expected (spec-correct) Output

A normalized relative path with no leading dot segments. (The spec does not prescribe an exact output for this case, but requires "no leading dot segments.")

### Actual (buggy) Output

`'../outside_file'` — starts with `..`, which is a leading dot segment.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
from src.incremental_reasoner import _normalized_relative_path

with tempfile.TemporaryDirectory(prefix="fm_agent_probe_") as tmpdir:
    proj_dir = os.path.join(tmpdir, "project")
    os.makedirs(proj_dir)
    outside_path = os.path.join(tmpdir, "outside_file")
    result = _normalized_relative_path(proj_dir, outside_path)
    print(repr(result))  # actual (buggy) output: '../outside_file'
    # expected (correct) output: a path with no leading dot segments
```

---

## Probe Script

```python
"""
Probe script for bug: _normalized_relative_path produces leading dot segments.

The spec claims the returned path contains no leading dot segments.
When given an absolute path outside proj_dir, os.path.relpath returns
a path starting with '..', violating the spec.
"""
import sys
import os
import tempfile

# Add project root to path so we can import the project modules
# __file__ is fm_agent/bug_validation/probe_*.py, so go up 3 levels
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from src.incremental_reasoner import _normalized_relative_path

    # Create a temp workspace for test fixtures (per FM-Agent self-validation guard)
    with tempfile.TemporaryDirectory(prefix="fm_agent_probe_") as tmpdir:
        proj_dir = os.path.join(tmpdir, "project")
        os.makedirs(proj_dir)

        outside_path = os.path.join(tmpdir, "outside_file")

        # Call the function with an absolute path outside proj_dir
        actual = _normalized_relative_path(proj_dir, outside_path)

        # Spec claim: "no leading dot segments"
        # Buggy behavior: result starts with '..' when path is outside proj_dir
        has_leading_dots = actual.startswith("..")

        if has_leading_dots:
            print(f"CONFIRMED — actual: {actual!r} starts with '..' (leading dot segment), "
                  f"violating spec claim 'no leading dot segments'")
        else:
            print(f"NOT CONFIRMED — actual: {actual!r} does not start with leading dot segments")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: '../outside_file' starts with '..' (leading dot segment), violating spec claim 'no leading dot segments'
```
