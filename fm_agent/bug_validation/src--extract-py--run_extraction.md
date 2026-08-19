# Bug Report: run_extraction

**Source file:** `/home/fancy/Projects_Vault/FM-Agent_qwen_7d490/fm_agent/extracted_functions/src/extract-py/run_extraction.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

After return, for every source file listed in phases.json that (a) is not a test file, (b) exists under proj_dir, and (c) has a file extension mapped to a supported language, every function extracted from that file exists as a separate file at work_dir/extracted_functions/<relative-source-directory>/<source-basename-with-last-dot-replaced-by-hyphen>/<canonicalized-function-name>.<original-extension>, with class-qualified names preserved in the flat filename. The returned first value equals the number of function files written during this call; the returned second value equals the number of extracted functions skipped because their output file already existed together with valid .spec.json and .info.json sidecars (skipping is disabled when force=True, in which case existing outputs are overwritten). Files whose output already satisfies the readiness condition are never rewritten unless force=True. Test files, missing files, and files with unmapped extensions contribute neither to the written nor the skipped count. If no function is written and none is skipped, the function still returns (0, 0) without raising. FileNotFoundError is raised if and only if the phases.json file does not exist at the resolved location. The function never modifies any source file under proj_dir. After writing, the extraction output directory is checked for conformance to the one-function-per-file invariant, and any violations are reported as warnings without aborting the call or changing the returned counts. The returned counts satisfy written >= 0 and skipped >= 0.

---

### Actual Behavior

The function terminates in one of the following ways:

**Exception paths:**
1. If the file at os.path.join(work_dir or proj_dir, 'phases.json') does not exist, a FileNotFoundError is raised with a message containing 'phases.json not found at'. No files are written and no extraction occurs.
2. If json.load raises (e.g., malformed JSON despite the pre-condition), the corresponding exception propagates. No extraction output is produced.
3. Any I/O or OS-level exception during batch_extract_all, file reading, or file writing propagates to the caller.

**Normal termination:**
Let effective_work_dir = work_dir if work_dir is not None, else proj_dir.

1. The function returns a tuple (written_count, skipped_count) of non-negative integers.
2. written_count equals the number of individual function files successfully written under os.path.join(effective_work_dir, 'extracted_functions').
3. skipped_count equals the number of source-file entries from phases.json that were not processed into output, encompassing: (a) entries for which _is_test_file returned True, (b) entries whose resolved path os.path.join(proj_dir, src_rel) does not exist on disk, and (c) any other entries skipped by logic beyond line 40 (e.g., unsupported language, empty extraction result, or pre-existing output when force is False).
4. The directory os.path.join(effective_work_dir, 'extracted_functions') exists after return.
5. For every source file that was processed (not skipped), each extracted function is written as a separate file whose name is produced by _safe_filename(func_name, ext), preserving '::' separators for class-qualified names. Adjacent sidecar files '<name>.spec.json' and '<name>.info.json' are created for each written function file.
6. The registry returned by batch_extract_all is consumed with keys normalized via os.path.normcase(os.path.normpath(...)); this normalization does not alter the filesystem.
7. _validate_extraction(output_base) is invoked on the extracted_functions directory. Its return value (a list of (path, count) pairs for files not containing exactly one function) is used for validation reporting but does not alter the written files.
8. No source files under proj_dir are modified or deleted.
9. The phases.json file is opened read-only and is not modified.
10. For every source_files entry sf in phases.json: exactly one of the following holds  sf was skipped (counted in skipped_count), sf was processed and contributed zero or more entries to written_count, or an exception was raised before completion.
11. written_count + skipped_count  total number of source_files entries across all phases and modules in phases.json.
12. If verbose is True, informational messages about skipped test files are printed to stdout; if verbose is False, no such messages are printed. Warnings for missing source files are always emitted via logging.warning regardless of verbose.

Formally:
 sf  source_files_list(phases_data):
  (_is_test_file(sf)  exists(proj_dir/sf)  other_skip_condition(sf))  sf contributes to skipped_count
  (_is_test_file(sf)  exists(proj_dir/sf)  other_skip_condition(sf))  sf contributes k  0 entries to written_count
 return_value = (written_count, skipped_count)
 written_count  0  skipped_count  0
 os.path.isdir(effective_work_dir / 'extracted_functions')

---

## Code Evidence

Line 32: if _is_test_file(src_rel):
Line 33:     if verbose:
Line 34:         print(f"  SKIP (test): {src_rel}")
Line 35:     continue

---

## Trigger Condition

Condition A states that skipped_count encompasses '(a) entries for which _is_test_file returned True' and '(b) entries whose resolved path does not exist on disk', meaning test files and missing files are counted in skipped_count. However, Condition B explicitly requires: 'Test files, missing files, and files with unmapped extensions contribute neither to the written nor the skipped count.' Additionally, Condition B defines skipped_count as 'the number of extracted functions skipped because their output file already existed together with valid .spec.json and .info.json sidecars', which is a per-function count of pre-existing outputs, not a per-source-file count of unprocessed entries. In the counterexample, a single test file in phases.json causes Condition A to produce (0,1) while Condition B requires (0,0).

---

## How to trigger the bug

The reported mismatch claims that `run_extraction` counts unprocessed source-file entries (test files, missing files, unmapped extensions) into `skipped_count`, so a `phases.json` listing a single test file would return `(0, 1)` while the specification requires `(0, 0)`.

Three probe attempts exercised `src.extract.run_extraction` — the smallest unit on the extraction path, invoked directly because the FM-Agent self-validation guard forbids starting an FM-Agent workflow (`run_pipeline`, `main.py`, CLI) from the probe — against throwaway fixture projects in fresh temporary directories:

1. **Attempt 1:** `phases.json` lists exactly one test file (`tests/test_foo.py`, present on disk, containing one extractable function). Claimed buggy output `(0, 1)`. Observed: `(0, 0)`.
2. **Attempt 2:** `phases.json` lists exactly one missing file (`src/missing.py`, absent on disk). Claimed buggy output `(0, 1)`. Observed: `(0, 0)`.
3. **Attempt 3 (final):** `phases.json` lists one entry of each uncountable category (test file + missing file + unmapped `.xyz` extension). Claimed buggy output `(0, 3)`. Observed: `(0, 0)`.

Reading the implementation confirms the observation: in `run_extraction`, the `continue` branches for test files, missing files, and unmapped extensions do **not** touch `skipped`; the single `skipped += 1` statement (line 762) is a per-function increment executed only when an output file already exists together with valid `.spec.json`/`.info.json` sidecars and `force` is False. That is exactly the semantics the specification ("Condition B") requires. The `actual_behavior` description recorded in the verification result ("Condition A", a per-source-file count of unprocessed entries) does not match the code under test, so the claimed miscount could not be reproduced within the 3-attempt budget.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | fresh `tempfile.mkdtemp()` fixture directory (probe-owned) |
| `phases.json` | `{"phases": [{"modules": [{"source_files": ["tests/test_foo.py", "src/missing.py", "data/notes.xyz"]}]}]}` |
| `tests/test_foo.py` | exists, contains `def helper(): return 1` |
| `src/missing.py` | listed but not created on disk |
| `data/notes.xyz` | exists, extension maps to no supported language |
| `work_dir` | `None` (defaults to `proj_dir`) |
| `force` | `False` |
| `verbose` | `False` |

### Expected (spec-correct) Output

`(0, 0)`

### Actual (buggy) Output

`(0, 0)` — the code returned exactly the spec-correct value; the claimed buggy outputs (`(0, 1)` / `(0, 3)`) never occurred, so no divergent buggy output exists to report.

### How to Reproduce

Step-by-step instructions (run from the repo root; uses the repo's pinned interpreter `.venv/bin/python` so FM-Agent's dependencies resolve):

1. Navigate to the repo root.
2. Run the following snippet (exercises the smallest public unit of the extraction stage; starting the FM-Agent pipeline itself is forbidden by the self-validation guard):

```py
import json, os, sys, tempfile
sys.path.insert(0, os.getcwd())  # repo root
from src.extract import run_extraction

proj_dir = tempfile.mkdtemp(prefix="fm_probe_run_extraction_")
os.makedirs(os.path.join(proj_dir, "tests"))
with open(os.path.join(proj_dir, "tests", "test_foo.py"), "w") as f:
    f.write("def helper():\n    return 1\n")
with open(os.path.join(proj_dir, "phases.json"), "w") as f:
    json.dump({"phases": [{"modules": [{"source_files": ["tests/test_foo.py"]}]}]}, f)

print(run_extraction(proj_dir))
# actual output: (0, 0)
# expected (correct) output: (0, 0)
# claimed buggy output from the verification result: (0, 1) — NOT observed
```

---

## Probe Script

```py
"""Probe for bug src--extract-py--run_extraction (attempt 3).

Maximal counterexample: phases.json now lists one entry of each category the
specification declares uncountable —
  1. "tests/test_foo.py"  (exists on disk, detected as a test file)
  2. "src/missing.py"     (listed but absent on disk)
  3. "data/notes.xyz"     (exists on disk, extension maps to no language)

The verification result's actual_behavior claim counts every unprocessed
source-file entry into skipped_count, i.e. expected buggy output (0, 3). The
specification requires that test files, missing files, and files with unmapped
extensions contribute neither to the written nor the skipped count, i.e.
spec-correct output (0, 0).

FM-Agent self-validation guard: no FM-Agent workflow is started; the probe
exercises the smallest relevant unit, src.extract.run_extraction, against a
throwaway fixture project in a fresh temporary directory.
"""

import json
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def main():
    from src.extract import run_extraction

    proj_dir = tempfile.mkdtemp(prefix="fm_probe_run_extraction_")

    os.makedirs(os.path.join(proj_dir, "tests"))
    os.makedirs(os.path.join(proj_dir, "data"))
    with open(os.path.join(proj_dir, "tests", "test_foo.py"), "w", encoding="utf-8") as f:
        f.write("def helper():\n    return 1\n")
    with open(os.path.join(proj_dir, "data", "notes.xyz"), "w", encoding="utf-8") as f:
        f.write("no language maps to .xyz\n")
    # src/missing.py deliberately not created.

    phases = {"phases": [{"modules": [{"source_files": [
        "tests/test_foo.py",
        "src/missing.py",
        "data/notes.xyz",
    ]}]}]}
    with open(os.path.join(proj_dir, "phases.json"), "w", encoding="utf-8") as f:
        json.dump(phases, f)

    actual = run_extraction(proj_dir)

    # Spec-correct: none of the three categories counts -> (0, 0).
    # Claimed buggy behavior: each unprocessed entry counted -> (0, 3).
    expected = (0, 0)
    passed = actual != expected  # True -> bug reproduced

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)
```

### Probe Output

```
Extraction complete: 0 written, 0 skipped.
NOT CONFIRMED — actual matched expected: (0, 0)
```

(Exit code 0. On stderr, the run additionally emitted `WARNING:root:Source file not found: <tmp>/src/missing.py`, `WARNING:root:Unsupported file extension '.xyz' for data/notes.xyz, skipping.`, and `ERROR:root:Nothing was extracted — check phases.json source_files paths.` — diagnostic logging that does not affect the returned counts.)
