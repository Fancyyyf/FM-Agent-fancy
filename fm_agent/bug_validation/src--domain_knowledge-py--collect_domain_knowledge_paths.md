# Bug Report: collect_domain_knowledge_paths

**Source file:** `src/domain_knowledge.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of resolved absolute file path strings, one per distinct domain-knowledge markdown file
  - The returned list includes paths sourced from two origins: the FM_AGENT_DOMAIN_KNOWLEDGE environment variable (split on os.pathsep) and the flattened cli_paths
  - An empty or unset FM_AGENT_DOMAIN_KNOWLEDGE environment variable contributes no paths
  - cli_paths entries that are None or empty contribute no paths
  - Each path in the returned list is absolute; if a source path is relative, it is resolved against base_dir, and if that resolution does not yield an existing file, it is resolved against fallback_base_dir as a secondary base
  - The returned list contains no duplicate entries
  - The returned list is empty if no valid domain-knowledge paths are found

---

### Actual Behavior

The function returns a list of absolute canonical file paths (strings). It first constructs a list `paths` by concatenating: (a) the result of splitting the environment variable `settings.runtime.domain_knowledge_paths` on `os.pathsep` if it is a non-empty string, else an empty list; and (b) the flattened list of path strings obtained from `cli_paths` after removing nesting, `None`, and empty values, preserving order. Then it calls `resolve_domain_knowledge_paths(paths, base_dir, fallback_base_dir)`, which for each path: expands `~` to the user home directory, resolves relative paths against `base_dir` (if the path is relative and not resolved via `base_dir`, fallback to `fallback_base_dir`), checks that the resolved path exists as a regular file and has a recognized domain-knowledge markdown extension; if any path fails these checks, a `ValueError` is raised. If no error occurs, the function returns a list of the resolved absolute canonical paths with duplicates removed (keeping the first occurrence according to the constructed order). If the list `paths` is empty, the function returns an empty list. Base_dir and fallback_base_dir (if not None) are pre-existing directories.

Formally: Let E = (settings.runtime.domain_knowledge_paths is not None and str(settings.runtime.domain_knowledge_paths).strip() != '') ? split(str(settings.runtime.domain_knowledge_paths), os.pathsep) : []; let C = _flatten_paths(cli_paths); let P = E + C. Then the return value R = resolve_domain_knowledge_paths(P, base_dir, fallback_base_dir). R satisfies: for each p in P, if resolve(p) fails, a ValueError is raised; otherwise, R = distinct_canonical([resolve(p) for p in P]) preserving order, where resolve(p) expands user home and uses base_dir or fallback_base_dir for relative paths, and requires p to be an existing regular file with a valid markdown extension; if P is empty, R = [].

---

## Code Evidence

Line 6-10: return resolve_domain_knowledge_paths(
        paths,
        base_dir=base_dir,
        fallback_base_dir=fallback_base_dir,
    )

---

## Trigger Condition

The code raises a ValueError when any source path cannot be resolved to a valid domain-knowledge markdown file, but the specification requires invalid paths to be silently ignored and only valid domain-knowledge paths to appear in the returned list (or an empty list if none are found). This is a concrete mismatch in error-handling behavior.

---

## How to trigger the bug

Pass a mix of valid and invalid (nonexistent) file paths via `cli_paths`. The specification states that invalid paths should be silently ignored and only valid paths should appear in the returned list (or an empty list if none are found). Instead, `resolve_domain_knowledge_paths` raises a `ValueError` on any path that does not exist, is not a file, or lacks a valid markdown extension.

### Inputs

| Parameter | Value |
|-----------|-------|
| `cli_paths` | `['<valid_md_path>', '/nonexistent_xyz_file_that_does_not_exist.md']` |
| `base_dir` | A temporary directory containing the valid markdown file |
| `fallback_base_dir` | `None` |

### Expected (spec-correct) Output

`['<absolute path to valid.md>']` — a list containing only the resolved absolute path of the valid markdown file, with the nonexistent path silently excluded.

### Actual (buggy) Output

`ValueError: domain knowledge file does not exist: /nonexistent_xyz_file_that_does_not_exist.md`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.domain_knowledge import collect_domain_knowledge_paths
import tempfile, os

tmpdir = tempfile.mkdtemp()
with open(os.path.join(tmpdir, 'valid.md'), 'w') as f:
    f.write('# test')

# This raises ValueError — spec says nonexistent paths should be silently ignored
collect_domain_knowledge_paths(
    cli_paths=[os.path.join(tmpdir, 'valid.md'), '/nonexistent/file.md'],
    base_dir=tmpdir,
)
# actual (buggy) output: ValueError: domain knowledge file does not exist: /nonexistent/file.md
# expected (correct) output: [<absolute path to valid.md>]
```

---

## Probe Script

```python
import sys
import os
import tempfile

sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot')

try:
    from src.domain_knowledge import collect_domain_knowledge_paths
except Exception as e:
    print(f'ERROR: Failed to import collect_domain_knowledge_paths: {e}')
    sys.exit(1)

# Create a temp directory for test fixtures
probe_tmp = tempfile.mkdtemp(prefix='bug_probe_')
print(f'[DEBUG] probe workspace: {probe_tmp}', file=sys.stderr)

# Create a single valid markdown file in the probe workspace
valid_md = os.path.join(probe_tmp, 'valid.md')
with open(valid_md, 'w') as f:
    f.write('# Valid domain knowledge\n')

# Test case: pass one valid path and one nonexistent path via cli_paths.
# The spec says: nonexistent/invalid paths should be silently ignored,
# only valid resolved paths should appear in the result.
# The bug: resolve_domain_knowledge_paths raises ValueError on invalid paths.

cli_paths = [valid_md, '/nonexistent_xyz_file_that_does_not_exist.md']

try:
    actual = collect_domain_knowledge_paths(
        cli_paths=cli_paths,
        base_dir=probe_tmp,
        fallback_base_dir=None,
    )
    # If we reach here, no ValueError was raised.
    # Check: the invalid path should have been skipped.
    # The valid path should be in the result.
    expected_abs = os.path.abspath(valid_md)
    actual_abs = [os.path.abspath(p) for p in actual] if actual else []

    if expected_abs in actual_abs and '/nonexistent_xyz_file' not in str(actual):
        print(f'NOT CONFIRMED — invalid path was silently skipped as expected per spec. '
              f'Returned only valid path: {actual!r}')
    else:
        print(f'NOT CONFIRMED — no ValueError raised, but unexpected result: '
              f'actual={actual!r}, expected to contain {expected_abs!r} and skip invalid paths')
except ValueError as e:
    # This confirms the bug: the spec says ignore, but code raises ValueError
    print(f'CONFIRMED — ValueError raised on invalid path (spec requires silent skip): {e}')
except Exception as e:
    print(f'ERROR: Unexpected exception: {e}')
    sys.exit(1)
finally:
    # Cleanup probe workspace
    import shutil
    shutil.rmtree(probe_tmp, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — ValueError raised on invalid path (spec requires silent skip): domain knowledge file does not exist: /nonexistent_xyz_file_that_does_not_exist.md
```
