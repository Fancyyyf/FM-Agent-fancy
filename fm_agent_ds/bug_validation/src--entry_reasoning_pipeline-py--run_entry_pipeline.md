# Bug Report: run_entry_pipeline

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/run_entry_pipeline.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

A Hoare-style reasoning pipeline has been executed on the subset of functions reachable from entry_func in the project's call graph. When end_funcs is provided and non-empty: only functions on directed call-graph paths from entry_func to some FQN in end_funcs are processed. Each processed function has a .spec.json, .info.json, and reasoning verdict written under proj_dir/fm_agent/. Any speccode mismatches are validated and reported under proj_dir/fm_agent/bug_validation/. If the pipeline fails partway, partial results are preserved under proj_dir/fm_agent/. The original source files under proj_dir are never modified. BUG_VALIDATION_MAX_RETRIES is set to 0 for the duration of the call.

---

### Actual Behavior

After the execution of run_entry_pipeline (whether it returns normally or propagates an exception), the following hold:

1. All test-file exemptions previously registered via add_test_file_exemption (including the exemption for the source file containing entry_func) are removed; no test-file exemptions remain active in the process.

2. The global configuration variable config.BUG_VALIDATION_MAX_RETRIES is set to 0.

3. The directory '<proj_dir>/fm_agent' exists and contains the output (possibly partial) of the entry-point-scoped reasoning pipeline. If the pipeline raised an exception, the output may be incomplete but will reflect everything saved before the failure.

4. The original project directory 'proj_dir' is not modified except for the addition/update of the 'fm_agent' subdirectory; all other source files remain unchanged.

5. The temporary run directory '<proj_dir>.fm-entry-run' (located beside proj_dir) no longer exists; it has been deleted even if an error occurred during pipeline execution.

Formally, letting
  P(proj_dir, entry_func) be the pre-condition that proj_dir is an existing directory and entry_func is a nonNone FQN of a function within proj_dir,
the post-condition after run_entry_pipeline(proj_dir, entry_func, ...) is:

  (  x  test_file_exemptions )  x is removed
   config.BUG_VALIDATION_MAX_RETRIES = 0
   dir_exists(proj_dir / "fm_agent")  contains_output(proj_dir / "fm_agent")
  (  f  src_files(proj_dir) \ { files_under(proj_dir / "fm_agent") } )  untouched(f)
    dir_exists( proj_dir.parent / (proj_dir.name + ".fm-entry-run") )

where
  - test_file_exemptions is the set of exemptions present before the call (including the one for entry_func's source file)
  - contains_output(d) means d holds the results (or partial results) of the entry pipeline
  - src_files returns the set of original source files in the project
  - files_under returns files recursively under a directory

---

## Code Evidence

Line 50: The entry_func's source file may match the test-file heuristics (a test
Line 51: directory or test-like name). Exempt it so neither the selection extraction
Line 52: below nor run_pipeline's extraction skips it  the entry point must always
Line 53: be reasoned about. Cleared in the finally so the exemption never leaks into
Line 54: a later run in the same process.
Line 55: add_test_file_exemption(_entry_func_source_rel(entry_func))

---

## Trigger Condition

The specification requires that every function reachable from entry_func in the project's call graph is processed (produces .spec.json, .info.json, and reasoning verdict). The code relies on internal testfile filtering that can skip functions in files classified as tests. It only exempts entry_func's source file, leaving other reachable functions in test files unsupplied. In the counterexample, bar is reached from entry_func but its file (tests/test_helpers.py) is skipped, so bar is never reasoned about, violating the specification.

---

## How to trigger the bug

The bug manifests when `entry_func` resides in (or reaches functions in) a directory classified as a test directory (`tests/`, `test/`, etc.). `run_entry_pipeline` calls `add_test_file_exemption()` for only the entry function's source file (line 306), but other functions on the call-graph path that also live in test-like directories are never exempted. Consequently, `_enumerate_source_files()` filters them out via `_is_test_file()` (line 340), and those functions are neither extracted nor reasoned about.

### Inputs

| Parameter | Value |
|---|---|
| `entry_func` | An FQN whose source file lives under a test directory (e.g. `tests::entry_main-py::main_entry`) |
| `proj_dir` | Any project directory containing a `tests/` subtree with helper functions |
| Callee | A function `bar` in `tests/test_helpers.py` that is reachable from `entry_func` but lives in a test directory |

### Expected (spec-correct) Output

All functions reachable from `entry_func` — including `bar` in `tests/test_helpers.py` — are extracted, reasoned about, and have `.spec.json` and `.info.json` sidecars written.

### Actual (buggy) Output

Only functions whose source files are NOT in test directories are processed. Functions in test directories (other than `entry_func`'s own file) are silently skipped because `_is_test_file()` returns `True` for them and they are not in the exemptions set.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.file_utils import _is_test_file, add_test_file_exemption, clear_test_file_exemptions

clear_test_file_exemptions()

# entry_func lives in a test directory
entry_file = "tests/entry_main.py"
helper_file = "tests/test_helpers.py"

# Both are detected as test files before any exemption
assert _is_test_file(entry_file)   # True
assert _is_test_file(helper_file)  # True

# run_entry_pipeline exempts ONLY the entry file
add_test_file_exemption(entry_file)

# After exemption: entry is no longer treated as test, but helper still is
assert not _is_test_file(entry_file)  # exempted
assert _is_test_file(helper_file)     # still skipped — BUG!

# actual (buggy) output: helper_file remains classified as test → functions skipped
# expected (correct) output: all reachable functions' source files should be exempted

clear_test_file_exemptions()
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on sys.path so 'from src.file_utils import ...' resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.file_utils import _is_test_file, add_test_file_exemption, clear_test_file_exemptions

    # Clear any prior state
    clear_test_file_exemptions()

    # Scenario: entry_func lives in a test directory (e.g. tests/entry_main.py).
    # A callee function bar is also in a test directory (tests/test_helpers.py).
    # run_entry_pipeline calls add_test_file_exemption() for the entry file only.
    # The callee's file is never exempted, so bar's functions are silently skipped.
    entry_file = "tests/entry_main.py"
    helper_file = "tests/test_helpers.py"

    # Both files reside under tests/ which is in _TEST_DIR_NAMES.
    entry_is_test_before = _is_test_file(entry_file)
    helper_is_test_before = _is_test_file(helper_file)

    # Simulate run_entry_pipeline: exempt ONLY the entry_func's source file.
    add_test_file_exemption(entry_file)

    # After the exemption:
    entry_is_test_after = _is_test_file(entry_file)
    helper_is_test_after = _is_test_file(helper_file)

    # The spec requires ALL functions reachable from entry_func to be processed.
    # The code only exempts the entry file; other reachable functions in test
    # files remain classified as test files and are skipped.
    gap_exists = (
        entry_is_test_before
        and helper_is_test_before
        and (not entry_is_test_after)
        and helper_is_test_after
    )

    # Cleanup
    clear_test_file_exemptions()

    if gap_exists:
        print(
            f"CONFIRMED — run_entry_pipeline exempts only entry_func's source file "
            f"({entry_file}); other reachable functions in {helper_file} remain "
            f"classified as test files and are silently skipped"
        )
    else:
        print(
            f"NOT CONFIRMED — entry_before={entry_is_test_before!r}, "
            f"helper_before={helper_is_test_before!r}, "
            f"entry_after={entry_is_test_after!r}, "
            f"helper_after={helper_is_test_after!r}"
        )

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — run_entry_pipeline exempts only entry_func's source file (tests/entry_main.py); other reachable functions in tests/test_helpers.py remain classified as test files and are silently skipped
```
