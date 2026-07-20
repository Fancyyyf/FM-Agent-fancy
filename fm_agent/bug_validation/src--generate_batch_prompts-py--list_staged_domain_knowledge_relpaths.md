# Bug Report: list_staged_domain_knowledge_relpaths

**Source file:** `src/generate_batch_prompts-py/list_staged_domain_knowledge_relpaths.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If the directory <work_dir>/spec_prompts/domain_context/user_knowledge/ does not exist
    or is not a directory, returns an empty list
  - Otherwise, returns a lexicographically sorted list of strings
  - Each returned string has the form "<prefix_without_trailing_slash>/<relative_path>",
    where relative_path is the POSIX-style path of a regular file inside
    <work_dir>/spec_prompts/domain_context/user_knowledge/ (recursively), computed
    relative to work_dir
  - A file is included if and only if all of the following hold:
    a. It is a regular file (not a symlink or directory)
    b. Its filename is not "manifest.json"
    c. Its filename suffix (case-insensitive) is ".md" or ".markdown"
  - Returns an empty list when the directory exists but contains no files matching
    the inclusion criteria
  - The returned paths use "/" separators regardless of the underlying OS

---

### Actual Behavior

The function returns a sorted list of strings, each representing a staged domain knowledge relative path. If the directory `<work_dir>/spec_prompts/domain_context/user_knowledge` does not exist or is not a directory, the result is an empty list. Otherwise, for every regular file encountered by a recursive glob under that directory whose suffix (caseinsensitive) is `.md` or `.markdown` and whose name is not `manifest.json`, a string is formed by appending a `/` followed by the POSIXstyle relative path from `work_dir` to that file, with the prefix `prefix` stripped of any trailing slash. The returned list is sorted lexicographically. Formally, let `K = work_dir / 'spec_prompts' / 'domain_context' / 'user_knowledge'`. Then:
- If `K.is_dir()` is False, `result = []`.
- If `K.is_dir()` is True, let `F = { f | f in rglob(K, '*'), f.is_file(), f.name != 'manifest.json', f.suffix.lower() in {'.md','.markdown'} }`. Then `result = sorted([ f"{prefix.rstrip('/')}/{f.relative_to(work_dir).as_posix()}" for f in F ])`.
No side effects, no exceptions raised.

---

## Code Evidence

Line 7: if not path.is_file() or path.name == "manifest.json":

---

## Trigger Condition

Condition A uses path.is_file() which resolves symbolic links, returning True for a symlink that points to a regular file. Condition B explicitly requires the file to be a regular file and not a symlink, so symlinks must be excluded. The code therefore incorrectly includes symlinks.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| work_dir  | A temporary directory containing `spec_prompts/domain_context/user_knowledge/` with `real.md` (regular file) and `linked.md` (symlink → real.md) |
| prefix    | `fm_agent` (default) |

### Expected (spec-correct) Output

`['fm_agent/spec_prompts/domain_context/user_knowledge/real.md']`

### Actual (buggy) Output

`['fm_agent/spec_prompts/domain_context/user_knowledge/linked.md', 'fm_agent/spec_prompts/domain_context/user_knowledge/real.md']`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
import shutil
from src.domain_knowledge import list_staged_domain_knowledge_relpaths

work_dir = tempfile.mkdtemp()
knowledge_dir = os.path.join(work_dir, "spec_prompts", "domain_context", "user_knowledge")
os.makedirs(knowledge_dir)
with open(os.path.join(knowledge_dir, "real.md"), "w") as f:
    f.write("# real file\n")
os.symlink("real.md", os.path.join(knowledge_dir, "linked.md"))

result = list_staged_domain_knowledge_relpaths(work_dir)
print(result)
# actual (buggy) output: ['fm_agent/spec_prompts/domain_context/user_knowledge/linked.md', 'fm_agent/spec_prompts/domain_context/user_knowledge/real.md']
# expected (correct) output: ['fm_agent/spec_prompts/domain_context/user_knowledge/real.md']

shutil.rmtree(work_dir)
```

---

## Probe Script

```python
import sys
import os
import tempfile
import shutil

# Ensure the repo root (cwd) is on sys.path so 'src' package resolves
sys.path.insert(0, os.getcwd())

try:
    from src.domain_knowledge import list_staged_domain_knowledge_relpaths

    # Create a temporary work_dir with the expected structure
    work_dir = tempfile.mkdtemp(prefix="bug_probe_")
    knowledge_dir = os.path.join(
        work_dir, "spec_prompts", "domain_context", "user_knowledge"
    )
    os.makedirs(knowledge_dir, exist_ok=True)

    # Create a real .md file
    real_md = os.path.join(knowledge_dir, "real.md")
    with open(real_md, "w") as f:
        f.write("# Real markdown file\n")

    # Create a symlink pointing to the real .md file
    # (also .md extension to pass the suffix filter)
    symlink_md = os.path.join(knowledge_dir, "linked.md")
    os.symlink("real.md", symlink_md)

    # Call the function under test
    result = list_staged_domain_knowledge_relpaths(work_dir)
    basenames = [os.path.basename(p) for p in result]

    # Expected (per spec): only real.md — symlinks must be excluded
    # Actual (buggy): both real.md and linked.md (symlink included via is_file)
    spec_includes_symlinks = False  # spec says "regular file (not a symlink)"
    buggy_includes_symlinks = "linked.md" in basenames
    passed = buggy_includes_symlinks  # True = bug reproduced (CONFIRMED)

    spec_expected = ["real.md"]
    actual = sorted(basenames)

    if passed:
        print(
            f"CONFIRMED — actual: {actual!r} | expected (per spec): {spec_expected!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — actual matched expected: {actual!r}"
        )

    # Cleanup
    shutil.rmtree(work_dir, ignore_errors=True)

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: ['linked.md', 'real.md'] | expected (per spec): ['real.md']
```
