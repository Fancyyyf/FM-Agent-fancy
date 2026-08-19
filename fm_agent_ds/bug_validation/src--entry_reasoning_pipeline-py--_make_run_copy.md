# Bug Report: _make_run_copy

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_make_run_copy.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

run_dir exists and contains a complete replica of proj_dir's file tree, excluding version-control metadata directories. If run_dir existed before the call, any prior contents are removed. Symbolic links in proj_dir are preserved as symbolic links in the copy. proj_dir is unmodified.

---

### Actual Behavior

Post-condition (normal termination): The directory `run_dir` exists and is a copy of `proj_dir` (the state of `proj_dir` at the start of the function) with the following properties:
- All files and directories from `proj_dir` are present in `run_dir` except those whose names match any pattern in `_SKIP_DIRS` (e.g., '.git').
- Symbolic links are copied as symbolic links (their targets are not resolved).
- The temporary directory `run_dir + '.tmp'` and any previous `run_dir` (or `run_dir + '.tmp'`) that existed before the call have been removed; hence no `.tmp` directory remains.

Formally (for normal termination):
  let src = proj_dir, dst = run_dir, skip = _SKIP_DIRS.
  (1) is_dir(dst)  is_dir(src)
  (2)  name  listdir(src) : if  matches_any(name, skip) then 
        exists child at dst/name such that:
          - if is_symlink(src/name) then is_symlink(dst/name) and link_target(dst/name) == link_target(src/name)
          - else if is_file(src/name) then is_file(dst/name) and content(dst/name) == content(src/name)
          - else if is_dir(src/name) then is_dir(dst/name) and recursive_copy_holds(src/name, dst/name, skip)
  (3)  name  listdir(dst) : exists corresponding name in src (i.e., no extra files).
  (4)  exists(dst + '.tmp')

If the function raises an exception, the filesystem state is unspecified and may be partially modified.

---

## Code Evidence

Line 12: shutil.copytree(
Line 13:     proj_dir, tmp_dir,
Line 14:     ignore=shutil.ignore_patterns(*_SKIP_DIRS),
Line 15:     symlinks=True,
Line 16: )

---

## Trigger Condition

The specification requires exclusion of version-control metadata directories (e.g., .svn, .hg). The code uses a global _SKIP_DIRS that, per the docstring, only excludes '.git'. Consequently, a project containing a .svn directory would have it copied, violating the specification.

---

## How to trigger the bug

Create a project directory with `.svn` metadata, call `_make_run_copy`, and observe that `.svn` is present in the copy — the spec says it should be excluded but the implementation only skips `.git`.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | A directory containing `.svn/`, `.git/`, `src/main.py`, and `README.md` |
| run_dir | A non-existent output directory path |

### Expected (spec-correct) Output

The `run_dir` contains `src/main.py` and `README.md`, but neither `.svn/` nor `.git/` (all version-control metadata directories are excluded).

### Actual (buggy) Output

The `run_dir` contains `.svn/`, `src/main.py`, and `README.md`. `.git/` is excluded because it happens to be in `_SKIP_DIRS`, but `.svn/` is copied through.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.entry_reasoning_pipeline import _make_run_copy
import tempfile, os

tmpdir = tempfile.mkdtemp()
proj_dir = os.path.join(tmpdir, 'proj')
run_dir = os.path.join(tmpdir, 'run')

# Create a mock project with .svn metadata
os.makedirs(os.path.join(proj_dir, '.svn', 'pristine'))
os.makedirs(os.path.join(proj_dir, '.git', 'objects'))
os.makedirs(os.path.join(proj_dir, 'src'))
with open(os.path.join(proj_dir, 'src', 'main.py'), 'w') as f:
    f.write('print("hello")')

_make_run_copy(proj_dir, run_dir)

# Bug: .svn exists in run_dir
print('.svn copied:', os.path.exists(os.path.join(run_dir, '.svn')))
# actual (buggy) output: .svn copied: True
# expected (correct) output: .svn copied: False
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Ensure the repo root is on sys.path so 'src' can be imported
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.entry_reasoning_pipeline import _make_run_copy
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

tmpdir = tempfile.mkdtemp()
proj_dir = os.path.join(tmpdir, 'mock_proj')
run_dir = os.path.join(tmpdir, 'mock_run')

try:
    # Create a mock project with .svn and .git metadata, plus regular files
    os.makedirs(os.path.join(proj_dir, '.svn', 'pristine'))
    os.makedirs(os.path.join(proj_dir, '.git', 'objects'))
    os.makedirs(os.path.join(proj_dir, 'src'))
    with open(os.path.join(proj_dir, 'src', 'main.py'), 'w') as f:
        f.write('print("hello")')
    with open(os.path.join(proj_dir, 'README.md'), 'w') as f:
        f.write('# Test Project')

    # Call _make_run_copy
    _make_run_copy(proj_dir, run_dir)

    # Per spec, version-control metadata (.svn AND .git) should be excluded.
    # Per implementation, only .git is excluded.
    svn_exists = os.path.exists(os.path.join(run_dir, '.svn'))
    git_exists = os.path.exists(os.path.join(run_dir, '.git'))
    src_exists = os.path.exists(os.path.join(run_dir, 'src', 'main.py'))
    readme_exists = os.path.exists(os.path.join(run_dir, 'README.md'))

    # Bug is CONFIRMED if .svn exists in run_dir (spec says exclude, code does not)
    if svn_exists:
        print(
            'CONFIRMED — .svn was copied (present in run_dir) '
            'but specification requires excluding all version-control metadata directories. '
            f'git_exists={git_exists} svn_exists={svn_exists} '
            f'src_exists={src_exists} readme_exists={readme_exists}'
        )
    else:
        print(
            'NOT CONFIRMED — .svn was NOT copied to run_dir, '
            'which matches the specification. '
            f'git_exists={git_exists} svn_exists={svn_exists} '
            f'src_exists={src_exists} readme_exists={readme_exists}'
        )
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    # Cleanup: remove the temp workspace
    import shutil
    for path in (run_dir, run_dir + '.tmp', proj_dir):
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
    shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — .svn was copied (present in run_dir) but specification requires excluding all version-control metadata directories. git_exists=False svn_exists=True src_exists=True readme_exists=True
```
