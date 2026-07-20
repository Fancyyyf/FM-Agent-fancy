# Bug Report: resolve_domain_knowledge_paths

**Source file:** `src/domain_knowledge-py/resolve_domain_knowledge_paths.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of absolute file path strings, one per distinct valid domain-knowledge markdown file
  - Each input entry is expanded for user home directories and flattened from any nesting
  - If an expanded entry is absolute, it is used directly; otherwise it is resolved against base_dir
  - When fallback_base_dir is not None and the base_dir-resolved path does not exist on the filesystem, the entry is resolved against fallback_base_dir as a secondary base
  - An entry whose resolved path does not exist on the filesystem is excluded from the returned list
  - An entry whose resolved path is not a regular file is excluded from the returned list
  - An entry whose resolved path has a file extension not in the set of recognized markdown extensions is excluded from the returned list
  - The returned list contains no duplicate entries; deduplication is performed on the real (canonical) path
  - The returned list preserves the relative order of first occurrence among the input entries
  - Returns an empty list when no entry resolves to a valid domain-knowledge file

---

### Actual Behavior

If the function returns normally, it returns a list `resolved` of strings satisfying: (1) each element `p`  `resolved` is the absolute path (via `os.path.abspath`) of an existing regular file whose extension (lowercase) belongs to the set `VALID_DOMAIN_KNOWLEDGE_EXTENSIONS`; (2) the canonical paths `os.path.realpath(p)` are all distinct, i.e., ij, `os.path.realpath(resolved[i])`  `os.path.realpath(resolved[j])`; (3) `resolved` preserves the order of first occurrence of each unique canonical file as they appear in the flattened input sequence `_flatten_paths(paths)`; (4) for every `raw_path` in `_flatten_paths(paths)`, either its resolved absolute path (after expansion, candidate selection, and abspath) appears in `resolved` (if it passes all checks and its canonical path was not seen before) or a `ValueError` was raised during its processing (if the path did not exist after `os.path.abspath`, was not a regular file, or had an invalid extension). If a `ValueError` is raised, no list is returned and the exception message indicates one of those three failures together with the original `raw_path`. The candidate selection for a raw path works as follows: expand `~`, if the result is absolute use it directly, otherwise join it with `base_dir` (always) and, if `fallback_base_dir` is not None, also join with `fallback_base_dir`; among these candidates, the first that exists is selected (if none exist, the first candidate from `base_dir` is used); `os.path.abspath` is then applied. No other side effects occur.

---

## Code Evidence

Line 23-24, Line 25-26, Line 28-32: The function raises ValueError for missing files, non-regular files, or invalid extensions, while the specification requires these entries to be excluded from the returned list without raising an error.

---

## Trigger Condition

The specification states that entries whose resolved path does not exist, is not a regular file, or has an invalid extension should be excluded from the returned list. The code raises ValueError for each such entry, causing a mismatch for any input containing an invalid entry.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| paths | `["nonexistent_markdown_file.md"]` |
| base_dir | `<current working directory>` |
| fallback_base_dir | `None` (default) |

### Expected (spec-correct) Output

`[]` (empty list — invalid entries should be silently excluded)

### Actual (buggy) Output

`ValueError("domain knowledge file does not exist: nonexistent_markdown_file.md")` — the function raises an exception instead of excluding the invalid entry.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.domain_knowledge import resolve_domain_knowledge_paths

result = resolve_domain_knowledge_paths(
    ["nonexistent_markdown_file.md"],
    base_dir=".",
)
# actual (buggy) output: ValueError("domain knowledge file does not exist: nonexistent_markdown_file.md")
# expected (correct) output: [] (empty list)
```

---

## Probe Script

```python
import sys
import os

# Ensure repo root is on sys.path for the src package import
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))
sys.path.insert(0, _repo_root)

try:
    from src.domain_knowledge import resolve_domain_knowledge_paths

    base_dir = os.getcwd()
    # Non-existent file — spec says it should be silently excluded,
    # but the code raises ValueError (the bug)
    paths = ["nonexistent_markdown_file.md"]

    actual = resolve_domain_knowledge_paths(paths, base_dir)
    expected = []  # spec: invalid entries excluded → empty result

    if actual != expected:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
except ValueError as e:
    # The ValueError itself confirms the bug — spec requires silent exclusion
    print(f"CONFIRMED — ValueError raised instead of excluding invalid entry: {e}")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — ValueError raised instead of excluding invalid entry: domain knowledge file does not exist: nonexistent_markdown_file.md
```
