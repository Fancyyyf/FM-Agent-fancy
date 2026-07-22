# Bug Report: run_incremental_pipeline

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/incremental_reasoner-py/run_incremental_pipeline.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If proj_dir has no previous full-run baseline (fm_agent/phases.json absent
    or fm_agent/extracted_functions/ incomplete given submodules), delegates
    the entire pipeline to a full run via run_pipeline() with the same
    arguments and returns None.
  - If intent_file_path does not refer to an existing regular file, or the
    file content is empty after whitespace stripping, logs an error and
    returns None without modifying any project or fm_agent/ file.
  - Before producing any new output, removes all files under
    fm_agent/logic_verification_results/ and fm_agent/bug_validation/, and
    removes incremental scope-selection and spec-update artifacts prefixed
    with "select_relevant_", "relevant_", and "spec_update_" from fm_agent/.
  - Regenerates fm_agent/phases.json from the current working tree.
  - Re-extracts every function from the current code, then restores the
    captured [SPEC] and [INFO] blocks from the prior run onto each function
    whose body is identical between old_commit_id and the current working
    tree.
  - Produces a mapping from each changed source-file path to the sets of
    function names added, modified, or removed since old_commit_id; deletes
    extracted-function files for removed functions.
  - Produces a ranked list of extracted-function relative paths whose
    implementations are judged relevant to the developer intent.
  - For every function that is either changed (added or modified) or appears
    in the relevance-ranked list, re-evaluates whether its [SPEC] and/or
    [INFO] blocks need updating to reflect the current code and intent;
    when a callee's [SPEC] changes, propagates the update to every caller's
    [INFO] block. Writes the set of files whose specs were modified to
    fm_agent/incremental_updated_specs.json.
  - Runs verification on the affected subset: every changed function, every
    function with an updated spec, and every function that calls a callee
    whose spec was updated. Returns a sorted list of extracted-function
    relative paths for which the reasoner reported a spec-to-code mismatch
    (MISMATCH verdict) and bug validation subsequently confirmed the
    violation. Returns an empty list when no such violations are confirmed.
  - Does not modify any file under proj_dir outside of fm_agent/.

---

### Actual Behavior

**Normal termination paths:**
- If `check_last_run_existence(proj_dir, submodules)` returns `False`: the function emits a warning log message ("No previous full run detected..."), invokes `run_pipeline(proj_dir, domain_knowledge_files=..., submodules=..., ...)` (which performs the full pipeline and produces artifacts under `fm_agent/`), and then returns `None` immediately.
- If `check_last_run_existence` returns `True` but the intent file at `intent_file_path` does not exist or is empty after stripping: the function logs an error ("Intent file ... does not exist" or "is empty") and returns `None` immediately.
- Otherwise (last run exists and intent file is valid): the function logs that a previous run was found, logs "[Stage 2/10] Loading developer intent...", reads and binds the nonempty developer intent to `developer_intent`, logs "intent loaded (%d chars)", then removes the stale directories `output_dir` and `<work_dir>/bug_validation` if they exist (logging one line per removed directory). Execution continues normally beyond line 80 with `developer_intent` set and the stale artifacts removed; no value is returned yet.

Additional logging side effects that are **always** performed by the code block (unless an exception prevented reaching them):
- A separator line of 70 `'='` characters is emitted (line 41).
- The message "[Stage 1/10] Checking for a previous full run to compare against..." is emitted.
- In the `True` branch of `check_last_run_existence`: "  -> previous full run found; proceeding with incremental analysis." is emitted.

**Exception paths:**
- If `check_last_run_existence` raises an exception, it propagates to the caller immediately; any log messages emitted up to that point (the separator and the "[Stage 1/10] ..." message) persist.
- If the fileopen or read on the intent file raises an exception, it propagates; the "[Stage 2/10] ..." log and the preceding stage1 logs remain.
- If `run_pipeline` raises an exception, it propagates to the caller.

---

## Code Evidence

Line 77:     for stale_dir in (output_dir, os.path.join(work_dir, "bug_validation")):
Line 78:         if os.path.isdir(stale_dir):
Line 79:             shutil.rmtree(stale_dir, ignore_errors=True)
Line 80:             logging.info("  -> removed stale results dir %s.", stale_dir)

---

## Trigger Condition

The specification demands removal of incremental scope-selection and spec-update artifacts (files prefixed with 'select_relevant_', 'relevant_', and 'spec_update_') before producing new output. The code only removes the two directories, omitting the required prefixbased file deletion, so a valid run where those files exist leaves the system in a state that violates the precondition for the subsequent incremental steps.

---

## How to trigger the bug

The verification incorrectly claims the code omits prefixed-file deletion. In reality, the code immediately following the directory removal (lines 227-245 in the extracted-function file, corresponding to lines 756-774 in `src/incremental_reasoner.py`) contains the required artifact removal using glob patterns that cover all three required prefixes.

### Inputs

| Parameter | Value |
|-----------|-------|
| N/A (static code inspection) | N/A |

### Expected (spec-correct) Output

The function should remove files prefixed with `select_relevant_`, `relevant_`, and `spec_update_` from `fm_agent/`.

### Actual (buggy) Output

N/A — the code does include the required removal. The glob patterns `select_relevant_modules.md`, `select_relevant_files_*.md`, `relevant_modules.json`, `relevant_files_*.json`, `spec_update_*.md`, and `spec_update_*.json` are present at lines 231-234 of the extracted-function file, and the deletion loop at lines 237-243 removes matching files.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import os

probe_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(os.path.dirname(probe_dir))
source_file = os.path.join(repo_root, 'src', 'incremental_reasoner.py')

with open(source_file, 'r') as f:
    source = f.read()

required_globs = [
    'select_relevant_modules.md',
    'select_relevant_files_*.md',
    'relevant_modules.json',
    'relevant_files_*.json',
    'spec_update_*.md',
    'spec_update_*.json',
]

found = [p for p in required_globs if p in source]
# actual (buggy) output: all 6 found — bug NOT confirmed
# expected (correct) output: all 6 found — spec satisfied
```

---

## Probe Script

```python
import sys
import os

try:
    # Locate the actual source file (probe script is at fm_agent/bug_validation/, source is at src/)
    probe_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(probe_dir))
    source_file = os.path.join(repo_root, 'src', 'incremental_reasoner.py')

    with open(source_file, 'r') as f:
        source = f.read()

    # The spec requires removal of files prefixed with 'select_relevant_',
    # 'relevant_', and 'spec_update_'. These glob patterns should exist in the
    # source code indicating the function removes the required artifacts.
    required_globs = [
        'select_relevant_modules.md',
        'select_relevant_files_*.md',
        'relevant_modules.json',
        'relevant_files_*.json',
        'spec_update_*.md',
        'spec_update_*.json',
    ]

    found = [p for p in required_globs if p in source]
    missing = [p for p in required_globs if p not in source]

    if len(found) == len(required_globs):
        print('NOT CONFIRMED — code includes required prefixed-file removal: all %d glob patterns present in source' % len(found))
    else:
        print('CONFIRMED — missing removal patterns: %s' % missing)

except Exception as e:
    print('ERROR: %s' % e)
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — code includes required prefixed-file removal: all 6 glob patterns present in source
```
