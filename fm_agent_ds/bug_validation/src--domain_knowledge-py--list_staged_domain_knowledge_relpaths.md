# Bug Report: list_staged_domain_knowledge_relpaths

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/domain_knowledge-py/list_staged_domain_knowledge_relpaths.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of strings sorted in lexicographic ascending order. Each entry is a path formed by concatenating prefix (with any trailing `/` removed), a `/` separator, and the path of a staged markdown file relative to work_dir with all path separators normalized to `/`. Only files whose lowercase extension matches a valid domain-knowledge extension are included; the manifest metadata file tracked in the same staging subdirectory is excluded regardless of its extension. If the staging subdirectory under work_dir does not exist, or contains no files matching the inclusion criteria, returns an empty list. File discovery is depth-first within the staging subdirectory and its descendants.

---

### Actual Behavior

After execution, the function either has raised an OSError due to filesystem operations (e.g., permission errors during os.walk) or has returned a list of strings. If an exception was raised, no return value is produced. Otherwise (normal termination), let knowledge_dir = os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR). If knowledge_dir is not an existing directory, the returned list is empty ([]). If knowledge_dir exists as a directory, the returned list is a sorted list of strings, each constructed as: p = prefix.rstrip('/') + '/' + rp, where rp = os.path.relpath(os.path.join(root, fname), work_dir).replace(os.sep, '/') for every file fname encountered during a walk of the knowledge_dir tree such that fname != USER_KNOWLEDGE_MANIFEST and os.path.splitext(fname)[1].lower() is an element of VALID_DOMAIN_KNOWLEDGE_EXTENSIONS. The sorting order is the standard lexicographic ascending order of Python's sorted() function. The filesystem state is not modified. Formally: let K = os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR). Then ( e : OSError, execution terminated with e raised)  (os.path.isdir(K)  result = [])  (os.path.isdir(K)  result = sort({ (prefix.rstrip('/') + '/' + os.path.relpath(os.path.join(d, f), work_dir).replace(os.sep, '/')) | (d, _, fs)  os.walk(K)  f  fs  f  USER_KNOWLEDGE_MANIFEST  os.path.splitext(f)[1].lower()  VALID_DOMAIN_KNOWLEDGE_EXTENSIONS })).

---

## Code Evidence

Line 7: for root, _dirs, files in os.walk(knowledge_dir):

---

## Trigger Condition

The specification requires the function to always return a (possibly empty) sorted list of path strings; it never permits an exception. The implementation can raise OSError (e.g., PermissionError) when `os.walk` encounters an unreadable subdirectory, which violates the postcondition that a list must be returned. A concrete example is a staging directory with a permissionrestricted subdirectory.

---

## How to trigger the bug

Three test scenarios were attempted to trigger an OSError from `os.walk` with an unreadable/permission-restricted subdirectory in the staging tree. In all cases, Python 3.12's `os.walk` implementation silently absorbed the error — see the CPython source at `/usr/lib/python3.12/os.py` lines 362–380, where `OSError` from `scandir()` is caught and `continue`-d without raising, when `onerror` is None (the default). The function always returned a list, never raising.

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | A temporary directory containing `spec_prompts/domain_context/user_knowledge/` with a valid `.md` file and a permission-restricted subdirectory |
| `prefix` | `"fm_agent"` (default) |

### Expected (spec-correct) Output

A sorted list of strings (e.g., `['fm_agent/spec_prompts/domain_context/user_knowledge/test.md']`).

### Actual (buggy) Output

The function returned a sorted list of strings in all tested scenarios. No `OSError` was raised.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile, stat, sys
sys.path.insert(0, '.')
from src.domain_knowledge import list_staged_domain_knowledge_relpaths

td = tempfile.mkdtemp()
kn_dir = os.path.join(td, 'spec_prompts', 'domain_context', 'user_knowledge')
os.makedirs(kn_dir)
with open(os.path.join(kn_dir, 'test.md'), 'w') as f:
    f.write('# Test')

# Create an unreadable subdirectory
restricted = os.path.join(kn_dir, 'restricted')
os.makedirs(restricted)
with open(os.path.join(restricted, 'hidden.md'), 'w') as f:
    f.write('# Hidden')
os.chmod(restricted, 0o000)

try:
    result = list_staged_domain_knowledge_relpaths(td)
    print(f'Returned: {result}')  # No OSError raised
except OSError as e:
    print(f'OSError: {e}')         # Bug: spec requires a list, not an exception
finally:
    os.chmod(restricted, stat.S_IRWXU)
    import shutil; shutil.rmtree(td, ignore_errors=True)
// actual (buggy) output: Returned: ['fm_agent/spec_prompts/domain_context/user_knowledge/test.md']
// expected (correct) output: Should be a list; OSError would violate the spec.
```

---

## Probe Script

```python
"""Probe script for bug: list_staged_domain_knowledge_relpaths OSError handling.

Bug claim: The function can raise OSError (e.g., PermissionError) when os.walk
encounters an unreadable subdirectory, violating the spec that it must always
return a (possibly empty) list.

Test: Create a staging directory with a permission-restricted subdirectory and
call the function through the public entry point.
"""
import os
import stat
import sys
import tempfile
import shutil

# Add repo root to sys.path so "from src.domain_knowledge import ..." works
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from src.domain_knowledge import list_staged_domain_knowledge_relpaths


def test_unreadable_subdir_chmod_zero():
    """Attempt 1: chmod 0o000 on a subdirectory within the staging dir."""
    td = tempfile.mkdtemp()
    try:
        kn_dir = os.path.join(td, "spec_prompts", "domain_context", "user_knowledge")
        os.makedirs(kn_dir)
        # Add a valid markdown file
        with open(os.path.join(kn_dir, "test.md"), "w") as f:
            f.write("# Test\n")
        # Create an unreadable subdirectory
        restricted = os.path.join(kn_dir, "restricted")
        os.makedirs(restricted)
        with open(os.path.join(restricted, "hidden.md"), "w") as f:
            f.write("# Hidden\n")
        os.chmod(restricted, 0o000)

        try:
            result = list_staged_domain_knowledge_relpaths(td)
            return False, f"Returned normally: {result}"
        except OSError as e:
            return True, f"OSError raised: {type(e).__name__}: {e}"
        finally:
            os.chmod(restricted, stat.S_IRWXU)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_unreadable_subdir_no_execute():
    """Attempt 2: chmod 0o444 (read-only, no execute) on a subdirectory."""
    td = tempfile.mkdtemp()
    try:
        kn_dir = os.path.join(td, "spec_prompts", "domain_context", "user_knowledge")
        os.makedirs(kn_dir)
        with open(os.path.join(kn_dir, "test.md"), "w") as f:
            f.write("# Test\n")
        restricted = os.path.join(kn_dir, "restricted")
        os.makedirs(restricted)
        with open(os.path.join(restricted, "hidden.md"), "w") as f:
            f.write("# Hidden\n")
        os.chmod(restricted, 0o444)

        try:
            result = list_staged_domain_knowledge_relpaths(td)
            return False, f"Returned normally: {result}"
        except OSError as e:
            return True, f"OSError raised: {type(e).__name__}: {e}"
        finally:
            os.chmod(restricted, stat.S_IRWXU)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_unlistable_parent():
    """Attempt 3: Remove execute from parent directory to break path resolution."""
    td = tempfile.mkdtemp()
    try:
        kn_dir = os.path.join(td, "spec_prompts", "domain_context", "user_knowledge")
        os.makedirs(kn_dir)
        with open(os.path.join(kn_dir, "test.md"), "w") as f:
            f.write("# Test\n")

        # Remove execute from parent of user_knowledge
        dc_dir = os.path.join(td, "spec_prompts", "domain_context")
        os.chmod(dc_dir, 0o666)

        try:
            result = list_staged_domain_knowledge_relpaths(td)
            return False, f"Returned normally: {result}"
        except OSError as e:
            return True, f"OSError raised: {type(e).__name__}: {e}"
        finally:
            os.chmod(dc_dir, stat.S_IRWXU)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main():
    bug_id = "src--domain_knowledge-py--list_staged_domain_knowledge_relpaths"
    confirmed = False
    last_result = ""

    tests = [
        ("chmod 0o000 subdir", test_unreadable_subdir_chmod_zero),
        ("chmod 0o444 subdir (no execute)", test_unreadable_subdir_no_execute),
        ("remove execute from parent dir", test_unlistable_parent),
    ]

    for name, test_fn in tests:
        try:
            is_bug, msg = test_fn()
            last_result = msg
            if is_bug:
                confirmed = True
                print(f"CONFIRMED — {name}: {msg}")
                break
            else:
                print(f"  [{name}]: NOT CONFIRMED — {msg}")
        except Exception as e:
            print(f"  [{name}]: ERROR — {type(e).__name__}: {e}")
            last_result = f"ERROR: {type(e).__name__}: {e}"

    if not confirmed:
        print(f"NOT CONFIRMED — All attempts failed to reproduce the bug.")
        print(f"  Last result: {last_result}")


if __name__ == "__main__":
    main()
```

### Probe Output

```
  [chmod 0o000 subdir]: NOT CONFIRMED — Returned normally: ['fm_agent/spec_prompts/domain_context/user_knowledge/test.md']
  [chmod 0o444 subdir (no execute)]: NOT CONFIRMED — Returned normally: ['fm_agent/spec_prompts/domain_context/user_knowledge/restricted/hidden.md', 'fm_agent/spec_prompts/domain_context/user_knowledge/test.md']
  [remove execute from parent dir]: NOT CONFIRMED — Returned normally: []
NOT CONFIRMED — All attempts failed to reproduce the bug.
  Last result: Returned normally: []
```
