# Bug Report: _make_run_copy

**Source file:** `src/entry_reasoning_pipeline.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- proj_dir is never mutated
  - run_dir holds a fresh recursive copy of proj_dir reflecting the state of proj_dir at call time, excluding entries whose names match a fixed, predefined set of skip patterns
  - Directory symlinks present in proj_dir are preserved as symlinks in the copy
  - Any pre-existing data at run_dir (e.g. a leftover directory from an interrupted prior invocation) is fully removed before the new copy is created
  - The copy is atomically installed: no observer can see a partial or intermediate state at run_dir

---

### Actual Behavior

If the function returns normally: run_dir exists as a directory whose recursive contents are an exact copy of proj_dir except that any files or subdirectories matching patterns in _SKIP_DIRS (including '.git') are omitted; proj_dir is unchanged; no run_dir + '.tmp' directory exists. If an exception occurs, the function does not return normally, and the filesystem may be partially modified: old run_dir and/or run_dir.tmp may have been removed, and run_dir.tmp may contain an incomplete copy.

---

## Code Evidence

Line 8: for stale in (run_dir, run_dir + ".tmp"):
Line 9: if os.path.exists(stale):
Line 10: shutil.rmtree(stale)

---

## Trigger Condition

The specification demands atomic installation so that no observer ever sees a partial or intermediate state at `run_dir`.  The code removes the old `run_dir` before the copy phase, creating a window where `run_dir` is absent.  If a failure or kill occurs during that window, the directory is lost entirely, breaking the atomicity guarantee.

---

## How to trigger the bug

The function `_make_run_copy` removes any pre-existing `run_dir` (and `run_dir.tmp`) via `shutil.rmtree` at the start of execution, before `shutil.copytree` populates the temporary copy. During the `copytree` phase, any observer checking `os.path.exists(run_dir)` will see `False` — the directory is absent. The new copy is only atomically installed at the very end via `os.replace`. This creates a window where `run_dir` does not exist, violating the atomic-installation guarantee.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Any directory (e.g. a temp dir with a file) |
| `run_dir` | Any pre-existing directory (creates the worst case, but even a non-existent run_dir exhibits the same gap) |

### Expected (spec-correct) Output

`run_dir` always exists, transitioning atomically from its old contents to the new contents without any observable intermediate state where it is absent.

### Actual (buggy) Output

During `shutil.copytree` (which writes to `run_dir.tmp`), `os.path.exists(run_dir)` returns `False` because the old directory was already removed via `shutil.rmtree`. An observer sees the directory as missing.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile, shutil
from src.entry_reasoning_pipeline import _make_run_copy

src = tempfile.mkdtemp()
dst = tempfile.mkdtemp()
with open(os.path.join(src, 't.txt'), 'w') as f: f.write('x')

gap = [False]
orig = shutil.copytree
def patched(*a, **kw):
    gap[0] = not os.path.exists(dst)
    return orig(*a, **kw)
shutil.copytree = patched

try:
    _make_run_copy(src, dst)
finally:
    shutil.copytree = orig

print('Gap observed:', gap[0])  # Prints True
```

---

## Probe Script

```python
import sys
import os
import tempfile
import shutil

# Ensure the repo root is on sys.path so 'src' package is importable
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.entry_reasoning_pipeline import _make_run_copy
except ImportError as e:
    print(f'ERROR: failed to import _make_run_copy: {e}')
    sys.exit(1)

src_dir = None
dst_dir = None

try:
    src_dir = tempfile.mkdtemp()
    dst_dir = tempfile.mkdtemp()
    with open(os.path.join(src_dir, 'test.txt'), 'w') as f:
        f.write('hello')

    gap_observed = [False]
    original_copytree = shutil.copytree

    def observing_copytree(*args, **kwargs):
        gap_observed[0] = not os.path.exists(dst_dir)
        return original_copytree(*args, **kwargs)

    shutil.copytree = observing_copytree

    try:
        _make_run_copy(src_dir, dst_dir)
    finally:
        shutil.copytree = original_copytree

    if gap_observed[0]:
        print(f'CONFIRMED — atomicity gap: run_dir absent during copy phase '
              f'(os.path.exists returned False while copytree was running)')
    else:
        print('NOT CONFIRMED — no gap observed during copy phase')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    for d in (src_dir, dst_dir):
        if d and os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — atomicity gap: run_dir absent during copy phase (os.path.exists returned False while copytree was running)
```
