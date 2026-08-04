# Bug Report: stage_domain_knowledge_files

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/domain_knowledge-py/stage_domain_knowledge_files.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When markdown_paths is falsy (None or empty): the contents of the directory spec_prompts/domain_context/user_knowledge/ under work_dir are unchanged. A sorted list of relative path strings (using `/` separator, prefixed with `fm_agent/`) to all markdown files present in that directory is returned. When markdown_paths is truthy: the directory spec_prompts/domain_context/user_knowledge/ under work_dir is atomically cleared and repopulated with exactly one copy of each markdown file resolved from markdown_paths plus a manifest.json. Each staged file is given a name derived from its source basename with special characters replaced by underscores; if the derived name collides with an already-used name in the batch, a numeric suffix is appended to ensure uniqueness. The manifest.json file in that directory records, for every staged file, the original absolute source path (`source_path`) and the staged relative path prefixed with `fm_agent/` (`staged_path`). A sorted list of relative path strings (using `/` separator, prefixed with `fm_agent/`) to all staged markdown files in the directory is returned.

---

### Actual Behavior

If the function terminates normally (no exception is raised):
  - If `markdown_paths` is falsy (None or an empty sequence), the function returns `list_staged_domain_knowledge_relpaths(work_dir)` and leaves the filesystem unmodified.
  - If `markdown_paths` is a nonempty sequence, let `resolved = resolve_domain_knowledge_paths(markdown_paths, base_dir=proj_dir, fallback_base_dir=os.getcwd())`; assume this call succeeds (otherwise an exception would be thrown). Define `target_dir = os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR)` where `USER_KNOWLEDGE_REL_DIR` is the constant path segment `spec_prompts/domain_context/user_knowledge`. After normal execution:
    * `target_dir` exists and contains exactly one file per element of `resolved` and a JSON manifest file named `USER_KNOWLEDGE_MANIFEST`.
    * For each `i = 0,...,len(resolved)-1`, let `name_i = _safe_staged_name(resolved[i], {name_0,...,name_{i-1}})` (with an empty set for `i=0`). Then `target_dir/name_i` is a copy of the source file `resolved[i]` (preserving file metadata via `shutil.copy2`), and all `name_i` are pairwise distinct.
    * The manifest file contains `{"files": entries}` where `entries` is a list of length `len(resolved)`. For each index `i`, the ith entry has `"source_path": resolved[i]` and `"staged_path": "fm_agent/" + rel_path_i` where `rel_path_i` is the path of `target_dir/name_i` relative to `work_dir` with all directory separators replaced by `/`.
    * The replacement is atomic: either the old `target_dir` remains untouched (if a failure occurs before the final `os.replace`) or it is completely replaced by the new content; no partial or mixed state can be observed.
    * The function returns `list_staged_domain_knowledge_relpaths(work_dir)`. According to its specification, this return value is a sorted list of `fm_agent/`prefixed relative paths (using `/` separators, in lexicographic ascending order) to every markdown file present in `target_dir`. Th...

---

## Code Evidence

Line 36: shutil.rmtree(target_dir, ignore_errors=True)
Line 37: os.replace(tmp_dir, target_dir)

---

## Trigger Condition

The specification requires that the directory be 'atomically cleared and repopulated', meaning there should be no observable intermediate state where the directory is empty. The code deletes the target directory on Line 36 before replacing it on Line 37. This creates a window where the directory does not exist, violating the atomicity requirement. Any non-empty markdown_paths input triggers this violation.

---

## How to trigger the bug

The function `stage_domain_knowledge_files` in `src/domain_knowledge.py` first calls `shutil.rmtree(target_dir)` on line 169, then `os.replace(tmp_dir, target_dir)` on line 170. Between these two calls, `target_dir` does not exist on disk. A concurrent reader or observer would see the directory missing, violating the specification's requirement that the directory be "atomically cleared and repopulated" with no observable intermediate state.

The `os.replace` call itself is atomic, but the preceding `shutil.rmtree` is not part of that atomic operation — it is a separate, observable deletion.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Any directory (temp directory used in probe) |
| `work_dir` | A path where `fm_agent/` subdirectory can be created |
| `markdown_paths` | A non-empty list of paths to `.md` files (e.g., `['/tmp/test.md']`) |

### Expected (spec-correct) Output

The target directory `spec_prompts/domain_context/user_knowledge/` under `work_dir` is atomically replaced — at no point between the start and end of the call is the directory missing or in a partial state.

### Actual (buggy) Output

The target directory is deleted by `shutil.rmtree` before `os.replace` renames the temporary directory into place. Between these two operations, the directory does not exist, and any observer sees the directory missing.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
import shutil

from src.domain_knowledge import stage_domain_knowledge_files, USER_KNOWLEDGE_REL_DIR

# Setup
tmpdir = tempfile.mkdtemp()
work_dir = os.path.join(tmpdir, 'fm_agent')
test_md = os.path.join(tmpdir, 'test.md')
with open(test_md, 'w') as f:
    f.write('# Test\n')

# First call: stage the file so target_dir exists
stage_domain_knowledge_files(tmpdir, work_dir, [test_md])

target_dir = os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR)
assert os.path.isdir(target_dir), 'target_dir should exist after first call'

# Monkey-patch to observe the atomicity window
_orig_rmtree = shutil.rmtree
_orig_replace = os.replace
_dir_missing = [False]

def patched_replace(src, dst):
    if os.path.normpath(dst) == os.path.normpath(target_dir):
        if not os.path.exists(dst):
            _dir_missing[0] = True
    return _orig_replace(src, dst)

shutil.rmtree = lambda path, *a, **kw: _orig_rmtree(path, *a, **kw)
os.replace = patched_replace

# Second call: triggers rmtree then replace
stage_domain_knowledge_files(tmpdir, work_dir, [test_md])

print('CONFIRMED' if _dir_missing[0] else 'NOT CONFIRMED')
# actual (buggy) output: CONFIRMED — directory missing between rmtree and replace
# expected (correct) output: NOT CONFIRMED — directory never disappears
```

---

## Probe Script

```python
import os
import sys
import tempfile
import shutil

try:
    from src.domain_knowledge import stage_domain_knowledge_files
    from src.domain_knowledge import USER_KNOWLEDGE_REL_DIR
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# All fixtures in a fresh temp directory (not under fm_agent/)
tmpdir = tempfile.mkdtemp(prefix='bug_probe_')
work_dir = os.path.join(tmpdir, 'fm_agent')

test_md = os.path.join(tmpdir, 'test.md')
with open(test_md, 'w') as f:
    f.write('# Test Knowledge\n\nThis is test content.\n')

# First call: set up the staged directory so target_dir exists on disk
stage_domain_knowledge_files(tmpdir, work_dir, [test_md])

target_dir = os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR)
if not os.path.isdir(target_dir):
    print('ERROR: target_dir not created after first call')
    sys.exit(1)

# Track rmtree calls and atomicity violation
_orig_rmtree = shutil.rmtree
_orig_replace = os.replace
_rmtree_called_for_target = [False]
_dir_missing_before_replace = [False]

def _patched_rmtree(path, *a, **kw):
    r = _orig_rmtree(path, *a, **kw)
    if os.path.normpath(path) == os.path.normpath(target_dir):
        _rmtree_called_for_target[0] = True
    return r

def _patched_replace(src, dst):
    if _rmtree_called_for_target[0] and os.path.normpath(dst) == os.path.normpath(target_dir):
        if not os.path.exists(dst):
            _dir_missing_before_replace[0] = True
    return _orig_replace(src, dst)

shutil.rmtree = _patched_rmtree
os.replace = _patched_replace

# Second call triggers the rmtree+replace code path (target_dir exists from first call)
stage_domain_knowledge_files(tmpdir, work_dir, [test_md])

# Restore original functions
shutil.rmtree = _orig_rmtree
os.replace = _orig_replace

expected = 'atomically cleared and repopulated (no window where directory missing)'
if _dir_missing_before_replace[0]:
    actual = 'directory was missing between rmtree and replace (atomicity violated)'
else:
    actual = 'no observable window detected'

if _dir_missing_before_replace[0]:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual: {actual!r} | expected: {expected!r}')

# Cleanup
shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — actual: 'directory was missing between rmtree and replace (atomicity violated)' | expected: 'atomically cleared and repopulated (no window where directory missing)'
```
