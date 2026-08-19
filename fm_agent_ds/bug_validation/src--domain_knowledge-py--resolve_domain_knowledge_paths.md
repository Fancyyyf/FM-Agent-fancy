# Bug Report: resolve_domain_knowledge_paths

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/domain_knowledge-py/resolve_domain_knowledge_paths.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of absolute file paths as strings, with each distinct real filesystem path (after symlink resolution) appearing at most once. For each string leaf obtained by recursively flattening paths: if the leaf is an absolute path it is used directly; otherwise it is first resolved against base_dir, and if that resolved path does not exist and fallback_base_dir is provided, resolved against fallback_base_dir. The resolved path must exist as a regular file whose extension (case-insensitive) belongs to the set of recognized markdown file extensions  if the resolved path does not exist, is not a regular file, or has an unrecognized extension, a ValueError is raised before any result is returned. The returned list preserves the order of first appearance after deduplication.

---

### Actual Behavior

If the function raises a ValueError, then there exists at least one flattened raw path from `paths` that fails to resolve to an existing file whose extension (case-insensitive) belongs to VALID_DOMAIN_KNOWLEDGE_EXTENSIONS; the error message identifies the offending raw path. If the function returns normally, it returns a list `resolved` of strings such that:

1. `resolved` contains a sequence of unique absolute paths derived from the flattened contents of `paths` in the order of their first successful resolution.
2. For every element `p` in `resolved`, `os.path.exists(p)` and `os.path.isfile(p)` are true, and the lowercased file extension of `p` is in VALID_DOMAIN_KNOWLEDGE_EXTENSIONS.
3. The elements of `resolved` have distinct `os.path.realpath` values (no file is duplicated).
4. Each raw path from the flattened input that produced an element in `resolved` satisfies the following resolution rule:
   - If `os.path.expanduser(raw)` is absolute, the candidate is that absolute path.
   - Otherwise, the candidate list is `[os.path.join(base_dir, expanded)]` followed by `[os.path.join(fallback_base_dir, expanded)]` if `fallback_base_dir` is not None.
   - The chosen candidate is the first that exists, or the first candidate if none exist.
   - The final path `p` is `os.path.abspath(chosen)`.

---

## Code Evidence

Line 10: expanded = os.path.expanduser(raw_path); Line 12: if os.path.isabs(expanded):

---

## Trigger Condition

The code applies os.path.expanduser, treating paths like '~/doc.md' as absolute after expansion, and thus bypasses base_dir resolution; according to the specification, such a leaf is not absolute and should be resolved against base_dir first.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `paths` | `['~/doc.md']` |
| `base_dir` | `<tempdir>` (containing subdirectory `~/` with file `doc.md`) |
| `fallback_base_dir` | `None` |

### Expected (spec-correct) Output

`['<tempdir>/~/doc.md']` — the raw leaf `~/doc.md` is not an absolute path, so it is resolved against `base_dir` first, producing `<tempdir>/~/doc.md` which exists.

### Actual (buggy) Output

`ValueError: domain knowledge file does not exist: ~/doc.md` — the code applies `os.path.expanduser('~/doc.md')` first, yielding `/home/<user>/doc.md`, which is absolute and used directly, but does not exist.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
import sys
sys.path.insert(0, '.')
from src.domain_knowledge import resolve_domain_knowledge_paths

base_dir = tempfile.mkdtemp()
tilde_dir = os.path.join(base_dir, '~')
os.makedirs(tilde_dir)
test_file = os.path.join(tilde_dir, 'doc.md')
with open(test_file, 'w') as f:
    f.write('test content')

try:
    result = resolve_domain_knowledge_paths(['~/doc.md'], base_dir)
    # actual (buggy) output: ValueError: domain knowledge file does not exist: ~/doc.md
    # expected (correct) output: [<tempdir>/~/doc.md]
except ValueError as e:
    print(f'Bug confirmed: {e}')
```

---

## Probe Script

```python
import os
import sys
import tempfile
import shutil

sys.path.insert(0, '.')
from src.domain_knowledge import resolve_domain_knowledge_paths

base_dir = tempfile.mkdtemp()
try:
    tilde_dir = os.path.join(base_dir, '~')
    os.makedirs(tilde_dir)
    test_file = os.path.join(tilde_dir, 'doc.md')
    with open(test_file, 'w') as f:
        f.write('test content')

    expected = [os.path.abspath(test_file)]
    actual = None

    try:
        actual = resolve_domain_knowledge_paths(['~/doc.md'], base_dir)
        passed = actual != expected
        if passed:
            print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
        else:
            print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
    except ValueError as e:
        passed = True
        print(f'CONFIRMED — ValueError raised: {e} | expected: {expected!r}')
finally:
    shutil.rmtree(base_dir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — ValueError raised: domain knowledge file does not exist: ~/doc.md | expected: ['/tmp/tmpdz370sy9/~/doc.md']
```
