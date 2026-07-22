# Bug Report: resolve_domain_knowledge_paths

**Source file:** `src/domain_knowledge.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of absolute file path strings, one per distinct valid domain-knowledge markdown file
- Each input entry is expanded for user home directories and flattened from any nesting
- If an expanded entry is absolute, it is used directly; otherwise it is resolved against base_dir
- When fallback_base_dir is not None and the base_dir-resolved path does not exist on the filesystem, the entry is resolved against fallback_base_dir as a secondary base; if the fallback candidate also does not exist, the base_dir candidate is used (and will be checked later)
- For each resolved path (the first existing candidate, or the base_dir candidate if none exist):
  * If the path does not exist on the filesystem, a ValueError is raised with a message indicating the raw input path
  * If the path exists but is not a regular file, a ValueError is raised with a message indicating the raw input path
  * If the path exists but its file extension is not in VALID_DOMAIN_KNOWLEDGE_EXTENSIONS, a ValueError is raised with a message listing allowed extensions and the raw input path
- The returned list contains no duplicate entries; deduplication is performed on the real (canonical) path
- The returned list preserves the relative order of first occurrence among the input entries
- If no paths are provided (or all entries are filtered out by deduplication after processing, but note that invalid entries raise errors, so this only applies when input is empty or contains only duplicates of already-seen valid files), returns an empty list

---

### Actual Behavior

The function returns a list `resolved` of strings, where:
- Every element is an absolute path that exists, is a regular file, and has a lowercase extension in `VALID_DOMAIN_KNOWLEDGE_EXTENSIONS`.
- For each raw path string `raw` produced by `_flatten_paths(paths)`, the function determines a candidate path via: let `e = os.path.expanduser(raw)`, then if `e` is absolute, `candidates = [e]`; otherwise `candidates = [os.path.join(base_dir, e)] + ([os.path.join(fallback_base_dir, e)] if fallback_base_dir is not None else [])`. The candidate actually considered is `c = next((c for c in candidates if os.path.exists(c)), candidates[0])` and the final path is `p = os.path.abspath(c)`. If `p` exists, is a file, has an allowed extension, and `os.path.realpath(p)` has not been previously selected for any other `raw`, then `p` is appended to `resolved`; if any of the existence, file, or extension checks fail, the function raises a `ValueError`.
- The returned list contains exactly those final paths in the order their unique real paths were first encountered. Formally:
  `resolved = [p_i | i <- [0..len(F)-1], let raw_i = F[i], e_i = os.path.expanduser(raw_i), cand_i = (if os.path.isabs(e_i) then [e_i] else [os.path.join(base_dir, e_i)] ++ (if fallback_base_dir is not None then [os.path.join(fallback_base_dir, e_i)] else [])), c_i = the first existing candidate in cand_i (cand_i[0] if none exist), p_i = os.path.abspath(c_i), where os.path.exists(p_i) ∧ os.path.isfile(p_i) ∧ os.path.splitext(p_i)[1].lower() ∈ VALID_DOMAIN_KNOWLEDGE_EXTENSIONS ∧ ∀ j < i, os.path.realpath(p_j) ≠ os.path.realpath(p_i) ]`.

---

## Code Evidence

Line 22: path = os.path.abspath(path)

---

## Trigger Condition

The code calls os.path.abspath on the candidate path before existence validation, performing lexical normalization (e.g., collapsing '..') without considering symlinks. If the original candidate exists but the normalized string does not, the code incorrectly raises a ValueError for a non-existent file, whereas the specification requires using the candidate path directly for all checks.

---

## How to trigger the bug

The bug is triggered when a user-provided domain knowledge path traverses a symbolic link and contains `..` components. The OS kernel resolves the path component-by-component, following symlinks, so `os.path.exists()` on the original candidate returns True. However, `os.path.abspath()` performs purely lexical normalization that does not resolve symlinks, producing a different path that may not exist.

### Inputs

| Parameter | Value |
|-----------|-------|
| `paths` | `["link/../doc.md"]` |
| `base_dir` | `<tmp>/base/` (contains symlink `link → ../real/`) |
| `fallback_base_dir` | `None` |

### Expected (spec-correct) Output

`["<tmp>/base/link/../doc.md"]` — the candidate path resolved against base_dir, which exists on the filesystem as `<tmp>/doc.md`.

### Actual (buggy) Output

`ValueError: domain knowledge file does not exist: link/../doc.md` — `os.path.abspath()` lexically normalizes the path to `<tmp>/base/doc.md`, which does not exist.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile

from src.domain_knowledge import resolve_domain_knowledge_paths

tmpdir = tempfile.mkdtemp()
base_dir = os.path.join(tmpdir, "base")
real_dir = os.path.join(tmpdir, "real")
os.makedirs(base_dir)
os.makedirs(real_dir)

# Create a real markdown file
with open(os.path.join(tmpdir, "doc.md"), "w") as f:
    f.write("# Test\n")

# Create symlink: base/link -> ../real
os.symlink("../real", os.path.join(base_dir, "link"))

# This raises ValueError even though the file exists:
resolve_domain_knowledge_paths(["link/../doc.md"], base_dir=base_dir)
# actual (buggy) output: ValueError: domain knowledge file does not exist: link/../doc.md
# expected (correct) output: ["<tmp>/base/link/../doc.md"]
```

---

## Probe Script

```python
"""Probe script for bug: resolve_domain_knowledge_paths calls os.path.abspath
before existence validation, breaking paths through symlinks with '..'."""

import os
import sys
import tempfile
import shutil

# Ensure the project root is on sys.path so 'src' is importable
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def main():
    # Create a temporary directory structure:
    #
    #   tmp/
    #   ├── doc.md                # /tmp/xxx/doc.md   ← the actual file
    #   ├── real/                  # directory
    #   └── base/
    #       └── link -> ../real/   # symlink
    #
    # Then call resolve_domain_knowledge_paths with:
    #   base_dir = tmp/base/
    #   paths = ["link/../doc.md"]
    #
    # The OS resolves the path through the symlink:
    #   tmp/base/link/../doc.md
    #     → link resolves to ../real (= tmp/real)
    #     → .. goes up to tmp/
    #     → doc.md = tmp/doc.md  (EXISTS)
    #
    # But os.path.abspath() does LEXICAL normalization:
    #   tmp/base/link/../doc.md  →  tmp/base/doc.md  (does NOT exist)
    #
    # The spec says to use the candidate path directly for checks.
    # The code calls os.path.abspath() at line 58 BEFORE the existence check,
    # turning an existing path into a non-existent one → spurious ValueError.

    tmpdir = tempfile.mkdtemp(prefix="fm_probe_")
    try:
        # Setup directory structure
        base_dir = os.path.join(tmpdir, "base")
        real_dir = os.path.join(tmpdir, "real")
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(real_dir, exist_ok=True)

        # Create the actual markdown file at tmp/doc.md
        doc_path = os.path.join(tmpdir, "doc.md")
        with open(doc_path, "w") as f:
            f.write("# Test doc\n")

        # Create symlink: tmp/base/link -> ../real  (relative symlink)
        link_path = os.path.join(base_dir, "link")
        os.symlink("../real", link_path)

        # Load the target function via the package module
        from src.domain_knowledge import resolve_domain_knowledge_paths

        # The input path: "link/../doc.md" relative to base_dir
        # Through the symlink: link → ../real (= tmp/real), .. → tmp/, doc.md → tmp/doc.md (EXISTS)
        # os.path.abspath makes it: tmp/base/doc.md (does NOT exist) ← BUG
        raw_input = "link/../doc.md"

        try:
            result = resolve_domain_knowledge_paths([raw_input], base_dir=base_dir)
            # If no ValueError, the bug is NOT confirmed
            print(f"NOT CONFIRMED — function returned {result!r} unexpectedly")
        except ValueError as e:
            # The bug is confirmed — the function raised ValueError for a path
            # that actually exists on the filesystem
            expected_path = os.path.join(tmpdir, "doc.md")
            actual_exists = os.path.exists(expected_path)
            print(
                f"CONFIRMED — ValueError raised for existing file: {e}\n"
                f"  actual file path: {expected_path}\n"
                f"  actual file exists: {actual_exists}\n"
                f"  abspath'd path: {os.path.abspath(os.path.join(base_dir, raw_input))}"
            )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — ValueError raised for existing file: domain knowledge file does not exist: link/../doc.md
  actual file path: /tmp/fm_probe_0_sv1xj0/doc.md
  actual file exists: True
  abspath'd path: /tmp/fm_probe_0_sv1xj0/base/doc.md
```
