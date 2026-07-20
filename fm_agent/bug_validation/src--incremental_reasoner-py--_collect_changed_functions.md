# Bug Report: _collect_changed_functions

**Source file:** `/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot/fm_agent/extracted_functions/src/incremental_reasoner-py/_collect_changed_functions.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dict mapping absolute file paths (str) to change-category dicts, each with
    keys "added", "removed", and "modified" whose values are sorted lists of function
    name strings.
  - A source file is considered only when its extension maps to a recognized key in
    EXT_TO_LANG, it is not classified as a test file, it is not under the fm_agent
    workspace directory, and  when submodules is provided  it resides under one of the
    specified subdirectory paths.
  - For a file present in the working tree but absent from old_commit_id (including
    untracked files): every function name extracted from the current version appears
    under "added"; "removed" and "modified" are empty lists.
  - For a file present at old_commit_id but absent from the working tree: every function
    name extracted from the old version appears under "removed"; "added" and "modified"
    are empty lists.
  - For a file present in both the old commit and the working tree: a function name
    extracted from the current tree but absent from the old tree is "added"; a function
    name extracted from the old tree but absent from the current tree is "removed"; a
    function name extracted from both trees whose source text differs is "modified".
  - Function identity is determined by extraction-result key, not by source text
    equivalence.
  - Source text comparison for "modified" uses exact string equality on the extracted
    function body.
  - Files with empty "added", "removed", and "modified" lists are excluded from the
    returned dict.
  - Raises subprocess.CalledProcessError when proj_dir is not a git repository or
    old_commit_id does not identify a valid commit reachable from the repository.

---

### Actual Behavior

The code block completes without raising `subprocess.CalledProcessError`. The local function `_git` executed the two git commands `git -C proj_dir diff --name-only old_commit_id -- *.ext1 *.ext2 ...` and `git -C proj_dir ls-files --others --exclude-standard -- *.ext1 ...` successfully, where the pathspec extensions are those in `EXT_TO_LANG`. The output lines are stored in `changed` and `untracked` respectively. The local function `_is_workspace_file` is defined but does not modify any state. The variable `files` is an ordered list containing every relative file path `p` that satisfies all of the following conditions: (1) `p` appears as a line in either `changed` or `untracked`; (2) `_is_test_file(p)` returns `False`; (3) `_is_workspace_file(p)` returns `False`, i.e., after normalizing backslashes, `p` is not `'fm_agent'` and does not start with `'fm_agent/'`. The order of `files` is determined by first appearance in the concatenation `changed + untracked`, with duplicate paths omitted (only the first occurrence is kept). The input parameters `proj_dir`, `old_commit_id`, and `submodules` are not modified. No other variables external to the function are affected. Formally:

Let:
- `pathspecs = ['*.' + ext for ext in EXT_TO_LANG]`
- `C = lines(git diff --name-only old_commit_id -- pathspecs...)` (list of relative paths)
- `U = lines(git ls-files --others --exclude-standard -- pathspecs...)` (list of relative paths)
- `combined = C + U` (concatenation)

Then:
`files = [p for i, p in enumerate(combined) if not _is_test_file(p) and not (norm(p) == 'fm_agent' or norm(p).startswith('fm_agent/')) and p not in set(combined[:i])]`
where `norm(p)` replaces backslashes with forward slashes.

Note: `submodules` parameter is not used in this code block; any filtering on `submodules` would occur after this point.

---

## Code Evidence

Line 38: files = [
    f for f in dict.fromkeys(changed + untracked)
    if not _is_test_file(f) and not _is_workspace_file(f)

---

## Trigger Condition

The code block constructs the list 'files' without considering the 'submodules' parameter. According to the specification, when 'submodules' is provided, only files residing under one of the specified subdirectories should be processed. Because the submodule check is missing, files outside the submodules (like 'src/main.py') are wrongly included, violating the required behavior.

---

## How to trigger the bug

The bug claim is **not confirmed**. The actual code in the current source (`src/incremental_reasoner.py`, line 341) and in the extracted function file (line 104) **does** include the submodule filtering via `_is_under_submodules(f, submodules)` in the list comprehension:

```python
files = [
    f for f in dict.fromkeys(changed + untracked)
    if not _is_test_file(f) and not _is_workspace_file(f)
    and _is_under_submodules(f, submodules)
]
```

The `_is_under_submodules` function (in `src/file_utils.py`, line 158) correctly returns `True` when `submodules is None` (passing all files through) and filters to include only files whose path matches a specified submodule when `submodules` is provided. Seven probe tests against `_is_under_submodules` all pass, confirming the filtering logic works as specified.

The code_evidence cites "Line 38" which does not correspond to the `files = [...]` statement in the current extracted file (it is actually at line 101-105) — the bug report appears to have been generated against an older version of the code where `_is_under_submodules` may have been genuinely absent, but the current code already includes it.

### Inputs

N/A — the bug could not be reproduced because the submodule filtering code is already present.

### Expected (spec-correct) Output

When `submodules=['src/core']` is provided, only files under `src/core/` should appear in the result.

### Actual (buggy) Output

The code produces the spec-correct output — `_is_under_submodules(f, submodules)` correctly filters to only files within the specified submodules.

### How to Reproduce

Cannot reproduce — the reported missing code is already present. The submodule filtering works correctly:

```python
from src.file_utils import _is_under_submodules

# Returns True when no submodule restriction
_is_under_submodules('src/main.py', None)              # True

# Returns True when path is under a specified submodule
_is_under_submodules('src/core/foo.py', ['src/core'])  # True

# Returns False when path is outside all specified submodules
_is_under_submodules('src/other/bar.py', ['src/core']) # False
```

---

## Probe Script

```py
import sys
sys.path.insert(0, '.')

try:
    from src.file_utils import _is_under_submodules
    from src.incremental_reasoner import _collect_changed_functions
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Test 1: _is_under_submodules returns True when submodules is None
actual_1 = _is_under_submodules('src/main.py', None)
expected_1 = True
passed_1 = actual_1 == expected_1

# Test 2: _is_under_submodules returns True when path is under a specified submodule
actual_2 = _is_under_submodules('src/core/foo.py', ['src/core'])
expected_2 = True
passed_2 = actual_2 == expected_2

# Test 3: _is_under_submodules returns False when path is NOT under any specified submodule
actual_3 = _is_under_submodules('src/other/bar.py', ['src/core'])
expected_3 = False
passed_3 = actual_3 == expected_3

# Test 4: _is_under_submodules returns True for exact match
actual_4 = _is_under_submodules('src/core', ['src/core'])
expected_4 = True
passed_4 = actual_4 == expected_4

# Test 5: Verify _collect_changed_functions source contains the submodule filter
import inspect
source = inspect.getsource(_collect_changed_functions)
has_submodule_filter = '_is_under_submodules' in source and 'submodules' in source
passed_5 = has_submodule_filter

# Test 6: _is_under_submodules with multiple submodules
actual_6 = _is_under_submodules('src/runtime/handler.py', ['src/core', 'src/runtime'])
expected_6 = True
passed_6 = actual_6 == expected_6

# Test 7: Path with backslashes normalization
actual_7 = _is_under_submodules('src\\core\\foo.py', ['src/core'])
expected_7 = True
passed_7 = actual_7 == expected_7

all_passed = all([passed_1, passed_2, passed_3, passed_4, passed_5, passed_6, passed_7])

if all_passed:
    print('NOT CONFIRMED — _is_under_submodules is present in _collect_changed_functions and correctly filters by submodules')
else:
    failures = []
    if not passed_1: failures.append('Test 1: None submodules')
    if not passed_2: failures.append('Test 2: path under submodule')
    if not passed_3: failures.append('Test 3: path outside submodule')
    if not passed_4: failures.append('Test 4: exact match')
    if not passed_5: failures.append('Test 5: source inspection')
    if not passed_6: failures.append('Test 6: multiple submodules')
    if not passed_7: failures.append('Test 7: backslash normalization')
    print(f'NOT CONFIRMED — some tests failed: {"; ".join(failures)}')
```

### Probe Output

```
NOT CONFIRMED — _is_under_submodules is present in _collect_changed_functions and correctly filters by submodules
```
