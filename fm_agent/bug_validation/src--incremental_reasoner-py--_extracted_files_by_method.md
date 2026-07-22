# Bug Report: _extracted_files_by_method

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a mutable dict-like mapping from string keys (function names) to lists of
    absolute filesystem paths, each list containing one or more entries
  - When func_dir is not an existing directory, returns an empty mapping (no keys present)
  - When func_dir is an existing directory, every regular file reachable from func_dir
    by recursive descent is indexed under one or two keys, using the file's basename
    with its final dot-separated extension removed as the base identifier (the "stem"):
    - The absolute path of the file is always appended to the list for the key equal to
      the full stem
    - Additionally, when the stem contains at least one "::" delimiter, the substring
      after the last "::" (the bare method name) is used as a second key, and the same
      absolute path is appended to the list for that key as well
    - When the stem contains no "::" delimiter, only the stem itself is used as a key
  - The order of absolute paths within each key's list reflects the order in which the
    corresponding files were encountered during traversal
  - Accessing a key not present in the mapping returns an empty list (rather than raising
    an error), and mutating the returned list does not affect the mapping

---

### Actual Behavior

If func_dir is not an existing directory, the function returns an empty defaultdict(list) (len(result) == 0 or equivalently for all keys k, result[k] == []). If func_dir is an existing directory and no filesystem errors occur during os.walk, the function returns a defaultdict(list) result where keys are stems or bare names extracted from the file names found, and for each file fn in the recursive walk, its absolute path p is appended to result[stem] and, if stem contains '::', also to result[bare] (where bare = stem.split('::')[-1] and bare != stem). Formally, let F be the multiset of (absolute_path, stem, bare) tuples obtained from os.walk(func_dir) where stem = fn[:fn.rfind('.')] if '.' in fn else fn, and bare = stem.split('::')[-1] if '::' in stem else None. Then result is a defaultdict(list) such that: (1) for all (p, s, b) in F, p is an element of result[s] and, if b is not None and b != s, p is an element of result[b]; (2) for any key k, result[k] contains only such paths and in the order they were added by the walk; (3) result[k] == [] for all keys k not appearing in any (stem, bare) from F. If os.walk raises an exception (e.g., OSError, PermissionError), that exception is propagated and the function does not return normally.

---

## Code Evidence

Line 11: index = defaultdict(list)
Line 27: return index

---

## Trigger Condition

The function returns a collections.defaultdict(list), which automatically stores a new list for any missing key when __getitem__ is called. This means that if a caller accesses a missing key and mutates the returned list (e.g., appends an element), the mapping is permanently modified with that new key and element, contradicting the requirement "mutating the returned list does not affect the mapping". To satisfy the specification, the mapping would need to return a copy or a readonly view for missing keys, or avoid using a sideeffecting default factory.

---

## How to trigger the bug

The bug manifests whenever a caller accesses a key not present in the mapping returned by `_extracted_files_by_method` and then mutates the returned list. The `defaultdict(list)` automatically creates a new empty list entry for any missing key on access, so the mutation persists in the mapping — violating the specification that "mutating the returned list does not affect the mapping."

### Inputs

| Parameter | Value |
|-----------|-------|
| `func_dir` (Test 1) | A path to a non-existent directory |
| `func_dir` (Test 2) | A temporary directory containing two Python files: `Foo.py` and `subdir/Bar.py` |

### Expected (spec-correct) Output

After accessing a missing key and mutating the returned list, the mapping should remain unchanged — the missing key should NOT appear in the mapping's keys.

### Actual (buggy) Output

After accessing a missing key and mutating the returned list, the missing key IS added to the mapping with the mutated list as its value. The `defaultdict(list)` factory auto-creates the entry on access.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
from collections import defaultdict

def _extracted_files_by_method(func_dir):
    index = defaultdict(list)
    if not os.path.isdir(func_dir):
        return index
    for root, _dirs, fnames in os.walk(func_dir):
        for fn in fnames:
            abs_path = os.path.join(root, fn)
            stem = fn[: fn.rfind(".")] if "." in fn else fn
            index[stem].append(abs_path)
            bare = stem.split("::")[-1]
            if bare != stem:
                index[bare].append(abs_path)
    return index

# Bug: defaultdict auto-creates keys on access
with tempfile.TemporaryDirectory() as tmp:
    result = _extracted_files_by_method(os.path.join(tmp, "nonexistent"))
    initial_count = len(result)  # 0
    lst = result["missing_key"]   # defaultdict creates the key here!
    lst.append("/fake")           # mutation persists
    final_count = len(result)     # 1 — mapping was mutated!
    print(f"Initial: {initial_count}, Final: {final_count}")
    # actual (buggy) output: Initial: 0, Final: 1
    # expected (correct) output: Initial: 0, Final: 0
```

---

## Probe Script

```python
"""Probe script for bug: _extracted_files_by_method returns defaultdict(list),
which mutates the mapping when a caller accesses a missing key and modifies
the returned list. The spec requires that mutating the returned list does NOT
affect the mapping."""

import os
import sys
import tempfile
from collections import defaultdict


# The function under test — exact copy from src/incremental_reasoner.py lines 423-451.
# It only depends on os and defaultdict (both stdlib), so a direct copy is safe.
def _extracted_files_by_method(func_dir):
    """``{key: [abs_path, ...]}`` for every extracted-function file under
    ``func_dir``, walked recursively. Each file is registered under BOTH keys so a
    caller can look it up whichever kind of name it holds:

      - its bare stem (``Flush``) — the regex change detector reports names
        without a class, so a bare name matches every same-named member;
      - its class-qualified identifier (``LocalStorage::Flush``) — scope ranking
        gets qualified names from codegraph spans, so this gives an exact match.

    A free function (``func_dir/foo.ext``) has identical stem and identifier, so it
    is registered once."""
    index = defaultdict(list)
    if not os.path.isdir(func_dir):
        return index
    for root, _dirs, fnames in os.walk(func_dir):
        for fn in fnames:
            abs_path = os.path.join(root, fn)
            stem = fn[: fn.rfind(".")] if "." in fn else fn
            index[stem].append(abs_path)
            bare = stem.split("::")[-1]
            if bare != stem:
                index[bare].append(abs_path)
    return index


def main():
    errors = []

    # Test 1: non-existent directory — returns empty mapping.
    # Per spec, accessing missing key should return empty list WITHOUT mutating mapping.
    with tempfile.TemporaryDirectory() as tmpdir:
        nonexistent = os.path.join(tmpdir, "does_not_exist")
        result = _extracted_files_by_method(nonexistent)

        # Capture initial length of the mapping
        initial_keys = set(result.keys())

        # Access a missing key — this triggers defaultdict's factory, creating the key
        returned_list = result["nonexistent_key"]

        # Mutate the returned list
        returned_list.append("/fake/path")

        # Check if the mapping was mutated (BUG: defaultdict adds the key)
        final_keys = set(result.keys())

        if "nonexistent_key" in final_keys:
            errors.append(
                "BUG CONFIRMED (Test 1): accessing missing key 'nonexistent_key' and "
                "mutating returned list modified the mapping. "
                f"Initial key count: {len(initial_keys)}, "
                f"Final key count: {len(final_keys)}. "
                "Spec requires: mutating returned list does NOT affect the mapping."
            )
        else:
            errors.append(
                "Test 1 passed: mapping was not mutated by accessing missing key."
            )

    # Test 2: directory with files — access a key NOT present in the mapping.
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some files so the mapping has legitimate entries
        os.makedirs(os.path.join(tmpdir, "subdir"))
        with open(os.path.join(tmpdir, "Foo.py"), "w") as f:
            f.write("")
        with open(os.path.join(tmpdir, "subdir", "Bar.py"), "w") as f:
            f.write("")

        result = _extracted_files_by_method(tmpdir)

        # These keys SHOULD be present (from the files we created)
        existing_keys_before = set(result.keys())
        assert "Foo" in existing_keys_before, f"Expected 'Foo' in keys, got {existing_keys_before}"
        assert "Bar" in existing_keys_before, f"Expected 'Bar' in keys, got {existing_keys_before}"

        # Access a key NOT in the mapping (a function name that doesn't exist)
        missing_key = "NonExistentFunction"
        assert missing_key not in existing_keys_before, f"{missing_key} should not be in mapping"

        returned_list_2 = result[missing_key]
        returned_list_2.append("/another/fake/path")

        keys_after = set(result.keys())
        if missing_key in keys_after:
            errors.append(
                "BUG CONFIRMED (Test 2): accessing missing key 'NonExistentFunction' "
                "and mutating returned list modified the mapping with existing files. "
                f"Keys before: {sorted(existing_keys_before)}, "
                f"Keys after: {sorted(keys_after)}. "
                "Spec requires: mutating returned list does NOT affect the mapping."
            )
        else:
            errors.append(
                "Test 2 passed: mapping was not mutated by accessing missing key "
                "when mapping already has entries."
            )

    # Report
    if errors:
        # Print bug reports first, then the verdict
        for err in errors:
            print(err)
        print("CONFIRMED")
    else:
        print("NOT CONFIRMED — all tests passed; mapping was not mutated")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
```

### Probe Output

```
BUG CONFIRMED (Test 1): accessing missing key 'nonexistent_key' and mutating returned list modified the mapping. Initial key count: 0, Final key count: 1. Spec requires: mutating returned list does NOT affect the mapping.
BUG CONFIRMED (Test 2): accessing missing key 'NonExistentFunction' and mutating returned list modified the mapping with existing files. Keys before: ['Bar', 'Foo'], Keys after: ['Bar', 'Foo', 'NonExistentFunction']. Spec requires: mutating returned list does NOT affect the mapping.
CONFIRMED
```
