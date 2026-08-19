# Bug Report: _codegraph_legacy_coverage

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_codegraph_legacy_coverage.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dict whose keys are the normalized relative paths of the files listed in file_languages (paths relativized against proj_dir and case-normalized) and whose values are booleans. For a file whose corresponding disk path under proj_dir does not exist, the value is True. For an existing file, the value is True if and only if the ordered sequence of (func_name, source) tuples produced by the legacy extractor under the file's language key is an ordered subsequence of the CodeGraph entries for that file  where a pair of entries match when they have the same unqualified function name and their source texts are identical after line-ending normalization  and each matched CodeGraph entry appears at a strictly later index than the preceding match. When the ordered-subsequence condition fails  meaning at least one legacy-discovered function lacks a matching CodeGraph entry in the required order  the value is False and a warning identifying the unmatched function name and its file path is emitted via the logging system. The function makes no modifications to the filesystem.

---

### Actual Behavior

The function returns a dictionary `coverage` with one key-value pair for each `rel_path` in the input `file_languages`. For a given `rel_path` with associated language key `lang_key`, let `rel_key = _normalized_relative_path(proj_dir, rel_path)` and `abs_path = os.path.join(proj_dir, rel_path)`. If `os.path.exists(abs_path)` is False, then `coverage[rel_key]` is `True`. Otherwise, let `legacy_funcs` be the list of `(name, source)` tuples returned by `extract_functions_from_file(abs_path, lang_key)`, and let `codegraph_items` be the list of `(identifier, source)` pairs from `codegraph_functions.get(rel_key, {})` in dictionary item order. The value `coverage[rel_key]` is `True` if and only if there exists a strictly increasing integer sequence `j_0 < j_1 < ... < j_{L-1}` (where `L = len(legacy_funcs)`) with each `j_i` a valid index into `codegraph_items` such that for every `i`: `_bare_function_name(codegraph_items[j_i][0]) == _bare_function_name(legacy_funcs[i][0])` and `_normalized_function_source(codegraph_items[j_i][1]) == _normalized_function_source(legacy_funcs[i][1])`. If no such sequence exists, `coverage[rel_key]` is `False`. The iteration order over `file_languages` determines the order of insertion into `coverage`, but no further ordering of the returned dictionary is guaranteed beyond the natural Python dict insertion order (Python 3.7+).

---

## Code Evidence

Line 28:                 _bare_function_name(identifier) == legacy_bare_name

---

## Trigger Condition

The code uses _bare_function_name, which strips trailing dedup suffixes (e.g., '_1'), to compare identifiers. The specification requires that 'unqualified function name' refers to the name without only qualifiers, keeping any dedup suffix added by the legacy extractor. Consequently, a legacy name like 'foo_1' and a CodeGraph name like 'foo()' are considered equal by the code (both become 'foo') but should be considered unequal per the specification, leading to an incorrect True verdict when a False verdict is required.

---

## How to trigger the bug

When the legacy extractor produces a function name with a trailing dedup suffix (e.g., `my_func_1`) and CodeGraph contains a function `my_func` with the same source body, `_bare_function_name` strips the `_1` suffix from both names, causing `_codegraph_legacy_coverage` to return `True` (covered). Per the specification, the dedup suffix is part of the unqualified function name, so these should be treated as different functions and the result should be `False` (not covered).

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Temporary directory containing `test.py` |
| `codegraph_functions` | `{"test.py": {"my_func": "def my_func():\n    pass\n"}}` |
| `file_languages` | `{<abspath to test.py>: "python"}` |
| Mocked legacy extractor output | `[("my_func_1", "def my_func():\n    pass\n")]` |

### Expected (spec-correct) Output

`False` — CodeGraph does not contain `my_func_1`, so the legacy function is not covered.

### Actual (buggy) Output

`True` — `_bare_function_name` strips the `_1` suffix from `my_func_1`, making it incorrectly match `my_func`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os, sys
sys.path.insert(0, ".")
import src.incremental_reasoner as mod

tmpdir = tempfile.mkdtemp()
probe_file = os.path.join(tmpdir, "test.py")
with open(probe_file, "w") as f:
    f.write("def my_func():\n    pass\n")

_orig = mod.extract_functions_from_file
mod.extract_functions_from_file = lambda fp, lk: [("my_func_1", "def my_func():\n    pass\n")]
result = mod._codegraph_legacy_coverage(
    tmpdir,
    {"test.py": {"my_func": "def my_func():\n    pass\n"}},
    {probe_file: "python"}
)
mod.extract_functions_from_file = _orig

key = mod._normalized_relative_path(tmpdir, probe_file)
print(result[key])  # actual (buggy) output: True
# expected (correct) output: False
```

---

## Probe Script

```python
r"""Probe for _codegraph_legacy_coverage: _bare_function_name incorrectly strips dedup suffixes.

Bug: _bare_function_name (src/incremental_reasoner.py:216) uses re.sub(r"_\d+$", "", bare)
which strips trailing dedup suffixes like "_1" from function names. This causes
_codegraph_legacy_coverage to return True (covered) even when the legacy extractor
produces a name like "my_func_1" and CodeGraph only has "my_func" —
they should be treated as different functions per the spec.

Scenario:
- Legacy extractor reports: my_func_1 (with dedup suffix)
- CodeGraph has: my_func (no suffix, identical body)
- _bare_function_name("my_func_1") → "my_func"
- _bare_function_name("my_func") → "my_func"
- Names falsely match → returns True (should be False)
"""
import sys
import os
import tempfile
import shutil

# Ensure repo root is on path so the 'src' package and 'config' module
# are importable when we run from the repo root.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

TMPDIR = tempfile.mkdtemp(prefix="bug_probe_")
PROBE_FILE = os.path.join(TMPDIR, "test.py")

result = None
error_msg = None
confirmed = False

try:
    # Create a real file so os.path.exists() passes.
    with open(PROBE_FILE, "w") as f:
        f.write("def my_func():\n    pass\n")

    # Import the module under test.
    # Importing incremental_reasoner pulls in config and other deps;
    # we assume the dev environment has them available.
    import src.incremental_reasoner as mod

    # Save original extract_functions_from_file for restoration.
    _original_extract = mod.extract_functions_from_file

    # Mock: return a legacy function WITH a dedup suffix that has the
    # same body as the CodeGraph function (so the source comparison
    # would also pass if the name comparison erroneously passes).
    def _mock_extract(filepath, lang_key):
        return [("my_func_1", "def my_func():\n    pass\n")]

    mod.extract_functions_from_file = _mock_extract

    # CodeGraph data: has "my_func" WITHOUT the "_1" suffix.
    codegraph_functions = {
        "test.py": {
            "my_func": "def my_func():\n    pass\n",
        }
    }
    file_languages = {PROBE_FILE: "python"}

    # Call the function under test.
    result = mod._codegraph_legacy_coverage(TMPDIR, codegraph_functions, file_languages)

    # Restore the original.
    mod.extract_functions_from_file = _original_extract

    # Determine the normalized key the function would have used.
    rel_key = mod._normalized_relative_path(TMPDIR, PROBE_FILE)
    actual = result.get(rel_key)

    # Per the spec ("unqualified function name" should NOT strip dedup suffixes),
    # "my_func_1" and "my_func" are different functions, so CodeGraph does NOT
    # cover this legacy function → expected is False.
    expected = False

    # Bug is confirmed if the code returns True (wrong) instead of False.
    confirmed = (actual == True)

    if confirmed:
        print("CONFIRMED — actual: %s | expected: %s (legacy 'my_func_1' should NOT match CodeGraph 'my_func')" % (actual, expected))
    else:
        print("NOT CONFIRMED — actual: %s | expected: %s" % (actual, expected))

except Exception as e:
    error_msg = str(e)
    print("ERROR: %s" % error_msg)
    # Also print a traceback for diagnostic purposes.
    import traceback
    traceback.print_exc()

finally:
    # Clean up temp directory.
    shutil.rmtree(TMPDIR, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — actual: True | expected: False (legacy 'my_func_1' should NOT match CodeGraph 'my_func')
```
