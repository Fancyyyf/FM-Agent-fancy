# Bug Report: _reapply_existing_specs

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- For each (rel_path, entry) in specs where entry["spec"] is truthy:
       If the file at fm_agent/extracted_functions/<rel_path> does not
        exist as a regular file, the entry is skipped (the function was
        removed or renamed since specs was captured)
       If the file already contains the substring "[SPEC]" in its first
        line, the file is left unchanged (idempotent  the spec header
        already present)
       Otherwise, the file is overwritten with, in order: the spec_block
        string with trailing whitespace stripped; a single blank line; the
        info_block string with leading/trailing whitespace stripped
        (appended only when the entry contains an "info" key whose value
        is not None); a single blank line; and the original file content
        with leading newlines removed
  - The resulting file content begins with a comment-prefixed [SPEC] marker
    on the first line; when an [INFO] block exists, it appears after the
    [SPEC] block, separated by exactly one blank line; the source code
    follows after exactly one blank line
  - Returns the count of files for which the spec header was written
    (i.e., the number of files modified by this call)
  - Does not read, write, or modify any file outside
    fm_agent/extracted_functions/
  - The original source code content in each modified file is preserved
    byte-for-byte (only the leading spec header is prepended)

---

### Actual Behavior

After execution of the code block, the function `_reapply_existing_specs` is defined, no explicit return value is produced (the callable returns `None` when invoked). The file system is modified as follows: for each pair `(rel_path, entry)` in the `specs` dictionary where `entry['spec']` is a nonempty string and the file at `os.path.join(proj_dir, 'fm_agent', 'extracted_functions', rel_path)` exists and is a regular file immediately before the modification attempt, and whose first line (if any) does not contain the substring `'[SPEC]'`, the content of that file is overwritten with `header + "\n\n" + original.lstrip("\n")`, where `header = entry['spec'].rstrip("\n")` and if `entry` contains the key `'info'` then `header` is extended by `"\n\n" + entry['info'].strip("\n")`, and `original` is the content that the file had when it was opened for reading. All other files (those without a matching entry, with a falsy spec, whose path does not exist, or whose first line already contains `'[SPEC]'`) remain exactly as they were before. The variables `proj_dir` and `specs` are not mutated by the block. Formally, let `Pre` be the file system state before the block and `Post` the state after. Let `base = os.path.join(proj_dir, 'fm_agent', 'extracted_functions')`. For every `(rel_path, entry)  specs` such that `entry.get('spec')` is truthy and `f = os.path.join(base, rel_path)` is a regular file in `Pre` and the first line `l` of `Pre(f)` (or the empty string if the file is empty) satisfies `'[SPEC]'  l`, we have `Post(f) = h + "\n\n" + lstrip_nl(Pre(f))` where `h = rstrip_nl(entry['spec'])` and if `'info'  entry` then `h = h + "\n\n" + strip_nl(entry['info'])`. All other file paths `p` retain `Post(p) = Pre(p)`. The execution leaves `proj_dir` and `specs` unchanged and returns no value (the callable ultimately returns `None`).

---

## Code Evidence

Line 17: for rel_path, entry in specs.items(): ... Line 39: f.write(header + "\n\n" + source.lstrip("\n")) (the function never accumulates a count of modified files and has no return statement, so it returns None)

---

## Trigger Condition

The specification explicitly states that the function returns the count of files for which the spec header was written. The code never initializes a counter, never increments it when a file is modified, and implicitly returns None at the end of the loop, violating the required behavior for any valid input where files are modified.

---

## How to trigger the bug

The function processes specs entries and writes spec headers to files, but never tracks how many files were modified and returns None instead of the count.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Path to a directory containing `fm_agent/extracted_functions/` with test files |
| `specs` | Dict with 5 entries: 2 with valid specs for existing files, 1 for a file already containing `[SPEC]`, 1 for a missing file, 1 with falsy spec |

### Expected (spec-correct) Output

`2` (file_a and file_b were modified)

### Actual (buggy) Output

`None`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, tempfile
sys.path.insert(0, os.getcwd())
from src.incremental_reasoner import _reapply_existing_specs

proj_dir = tempfile.mkdtemp()
extracted_dir = os.path.join(proj_dir, "fm_agent", "extracted_functions")
os.makedirs(extracted_dir)

with open(os.path.join(extracted_dir, "a.py"), "w") as f:
    f.write("def foo(): pass\n")
with open(os.path.join(extracted_dir, "b.py"), "w") as f:
    f.write("def bar(): pass\n")

specs = {
    "a.py": {"spec": "# [SPEC]\n# a\n# [SPEC]"},
    "b.py": {"spec": "# [SPEC]\n# b\n# [SPEC]"},
}

result = _reapply_existing_specs(proj_dir, specs)
# actual (buggy) output: None
# expected (correct) output: 2
```

---

## Probe Script

```python
"""Probe script for bug: _reapply_existing_specs returns None instead of count."""
import os
import sys
import tempfile
import shutil

# Probe is at: snapshot/fm_agent/bug_validation/probe_*.py
# Go up 3 levels to reach snapshot (repo root)
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.incremental_reasoner import _reapply_existing_specs
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Create a temporary project directory structure to test against
proj_dir = tempfile.mkdtemp(prefix="probe_reapply_")
extracted_dir = os.path.join(proj_dir, "fm_agent", "extracted_functions")
os.makedirs(extracted_dir, exist_ok=True)

# Create test files
# file_a: exists, no [SPEC] header → should be modified
file_a_path = os.path.join(extracted_dir, "file_a.py")
with open(file_a_path, "w") as f:
    f.write("def foo():\n    return 42\n")

# file_b: exists, no [SPEC] header → should be modified
file_b_path = os.path.join(extracted_dir, "file_b.py")
with open(file_b_path, "w") as f:
    f.write("def bar():\n    return 'hello'\n")

# file_c: exists, HAS [SPEC] in first line → should be SKIPPED (idempotent)
file_c_path = os.path.join(extracted_dir, "file_c.py")
with open(file_c_path, "w") as f:
    f.write("# [SPEC]\n# pre-existing header\n# [SPEC]\ndef baz():\n    pass\n")

# file_d: does NOT exist as a file → directory to test missing path
os.makedirs(os.path.join(extracted_dir, "file_d.py"), exist_ok=True)

# Build the specs dict matching what extract_existing_specs would return
specs = {
    "file_a.py": {"spec": "# [SPEC]\n# spec for file_a\n# [SPEC]"},
    "file_b.py": {"spec": "# [SPEC]\n# spec for file_b\n# [SPEC]", "info": "# [INFO]\n# info for file_b\n# [INFO]"},
    "file_c.py": {"spec": "# [SPEC]\n# new spec for file_c (should NOT be applied)\n# [SPEC]"},
    "file_d.py": {"spec": "# [SPEC]\n# spec for file_d (should be skipped, no file)\n# [SPEC]"},
    "file_e.py": {"spec": ""},  # falsy spec → skip
}

actual = None
passed = False

try:
    actual = _reapply_existing_specs(proj_dir, specs)
    # The spec says it should return the count of modified files (2: file_a, file_b).
    # The bug is that it returns None instead.
    expected = 2
    passed = actual != expected  # True → bug reproduced (returned None, not 2)
except Exception as e:
    print(f'ERROR: {e}')
    shutil.rmtree(proj_dir, ignore_errors=True)
    sys.exit(1)

# Cleanup
shutil.rmtree(proj_dir, ignore_errors=True)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: None | expected: 2
```
