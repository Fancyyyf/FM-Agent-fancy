# Bug Report: run_incremental_pipeline

**Source file:** `src/incremental_reasoner.py` (function `run_incremental_pipeline`)
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
   function with an updated spec, and every function that calls a callee whose spec was updated.

---

### Actual Behavior

Natural language: After execution of this code block (assuming no exceptions), one of the following holds: (1) If check_last_run_existence(proj_dir, submodules) returns False, the full pipeline run_pipeline is executed with the given arguments, and the enclosing function returns None; no further incremental processing occurs. (2) If a prior full run exists but intent_file_path does not point to a regular file, an error is logged and the function returns None; no directory cleanup is performed. (3) If a prior run exists and intent_file_path is a file but its trimmed content is empty, an error is logged and the function returns None; no directory cleanup is performed. (4) If a prior run exists and intent_file_path contains nonwhitespace text, developer_intent is set to that text, the directories output_dir (logic_verification_results) and bug_validation under fm_agent/ are removed if they existed, and execution continues to subsequent incremental stages. If any exception is raised during the block (e.g., from shutil.rmtree or I/O), these postconditions may not hold and the system state may be partially modified.

Formal logic:
Let has_last_run = check_last_run_existence(proj_dir, submodules).
Let intent_is_file = os.path.isfile(intent_file_path).
Let intent_content = (open(intent_file_path).read().strip() if intent_is_file else "").
Let work_dir = join(proj_dir, 'fm_agent') (assumed already defined).
Let output_dir = join(work_dir, 'logic_verification_results') (assumed already defined).
Let returned denote whether the enclosing function has executed a return statement.
Let result denote the function's return value.

On normal execution (no exceptions):
(¬has_last_run) ⇒ (run_pipeline(proj_dir, domain_knowledge_files, submodules, one_phase, extra_call_edges_path) was called) ∧ returned ∧ (result = None)
(has_last_run ∧ ¬intent_is_file) ⇒ returned ∧ (result = None) ∧ (logging.error called) ∧ ¬(∃ d ∈ {output_dir, join(work_dir, 'bug_validation')} : os.path.isdir(d) ∧ d was removed)
(has_last_run ∧ intent_is_file ∧ intent_content = "") ⇒ returned ∧ (result = None) ∧ (logging.error called) ∧ ¬(∃ d ∈ {output_dir, join(work_dir, 'bug_validation')} : os.path.isdir(d) ∧ d was removed)
(has_last_run ∧ intent_is_file ∧ intent_content ≠ "") ⇒ (∀ d ∈ {output_dir, join(work_dir, 'bug_validation')} : os.path.isdir(d) ⇒ d was removed) ∧ (developer_intent = intent_content)

---

## Code Evidence

Line 77: for stale_dir in (output_dir, os.path.join(work_dir, "bug_validation")):

---

## Trigger Condition

The cleanup loop on lines 77-79 removes only the logic_verification_results and bug_validation directories. The specification additionally mandates removal of incremental scope-selection and spec-update artifacts with prefixes "select_relevant_", "relevant_", and "spec_update_" inside fm_agent/. The code never deletes those files, leaving stale incremental artifacts that violate the requirement to clear all such data before producing new output. A concrete input with a non-empty intent file and existing prefixed artifacts demonstrates this violation.

---

## How to trigger the bug

The claimed bug is a **false positive**: the source code at `src/incremental_reasoner.py` lines 662–680 contains a second cleanup block immediately after the directory removal loop that explicitly deletes all stale scope-selection and spec-update artifacts with the required prefixes.

The `stale_artifact_globs` tuple (lines 666–670) defines patterns covering all three mandated prefixes:

```
stale_artifact_globs = (
    "select_relevant_modules.md", "relevant_modules.json",
    "select_relevant_files_*.md", "relevant_files_*.json",
    "spec_update_*.md", "spec_update_*.json",
)
```

The subsequent loop (lines 672–678) iterates these glob patterns against `fm_agent/` and removes matching files via `os.remove()`. A successful-removal counter and log message confirm the operation.

The verification model appears to have stopped reading at the directory-removal loop (lines 657–660) and did not observe the artifact-cleanup block that follows immediately (lines 666–678).

### Inputs

N/A — the bug is a false positive. The cleanup code already satisfies the specification.

### Expected (spec-correct) Output

Prefixed artifacts (`select_relevant_*`, `relevant_*`, `spec_update_*`) under `fm_agent/` are deleted before new output is produced.

### Actual (buggy) Output

The code already deletes all prefixed artifacts matching those patterns. No bug exists.

### How to Reproduce

1. Navigate to the repo root.
2. Inspect the source code at `src/incremental_reasoner.py`, lines 662–680.
3. Observe that the second cleanup block (`stale_artifact_globs` + deletion loop) covers all three required prefixes.

```python
# The relevant code block at src/incremental_reasoner.py lines 665–680:
stale_artifact_globs = (
    "select_relevant_modules.md", "relevant_modules.json",
    "select_relevant_files_*.md", "relevant_files_*.json",
    "spec_update_*.md", "spec_update_*.json",
)
removed_artifacts = 0
for pattern in stale_artifact_globs:
    for stale_file in glob.glob(os.path.join(work_dir, pattern)):
        try:
            os.remove(stale_file)
            removed_artifacts += 1
        except OSError:
            pass
if removed_artifacts:
    logging.info("  -> removed %d stale scope-selection artifact(s) from %s.", removed_artifacts, work_dir)
# actual output: all three prefixes (select_relevant_, relevant_, spec_update_) are covered
# expected output: all three prefixes are covered — spec satisfied
```

---

## Probe Script

```python
"""Probe for bug: src--incremental_reasoner-py--run_incremental_pipeline

Verifies whether run_incremental_pipeline's cleanup code removes prefixed artifacts
(select_relevant_*, relevant_*, spec_update_*) as required by the specification.

Uses static analysis of the source code, per the FM-Agent self-validation guard
(no pipeline invocation allowed).
"""
import ast
import sys
import os


def find_stale_artifact_globs(source_path):
    """Parse the source and extract the stale_artifact_globs tuple definition."""
    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)

    class GlobsVisitor(ast.NodeVisitor):
        def __init__(self):
            self.found = None

        def visit_Assign(self, node):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "stale_artifact_globs":
                    if isinstance(node.value, ast.Tuple):
                        self.found = [
                            elt.value if isinstance(elt, ast.Constant) else None
                            for elt in node.value.elts
                        ]
                    return

    visitor = GlobsVisitor()
    visitor.visit(tree)
    return visitor.found


def check_prefix_coverage(globs, required_prefixes):
    """Check that each required prefix has at least one glob pattern covering it."""
    missing = []
    for prefix in required_prefixes:
        covered = any(g.startswith(prefix) for g in globs if g)
        if not covered:
            missing.append(prefix)
    return missing


def main():
    # The actual source file (not the extracted function copy)
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    source_file = os.path.join(repo_root, "src", "incremental_reasoner.py")

    try:
        globs = find_stale_artifact_globs(source_file)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    expected_globs = [
        "select_relevant_modules.md",
        "relevant_modules.json",
        "select_relevant_files_*.md",
        "relevant_files_*.json",
        "spec_update_*.md",
        "spec_update_*.json",
    ]

    required_prefixes = ["select_relevant_", "relevant_", "spec_update_"]

    if globs is None:
        print(
            "CONFIRMED — stale_artifact_globs not found in source; "
            "prefixed artifacts are not cleaned."
        )
        return

    missing = check_prefix_coverage(globs, required_prefixes)

    if missing:
        print(
            f"CONFIRMED — stale_artifact_globs found ({globs}) "
            f"but missing prefix(es): {missing}. "
            f"Spec requires cleanup of prefixes: {required_prefixes}"
        )
    elif globs != expected_globs:
        # Coverage is good but globs don't match exactly
        print(
            f"NOT CONFIRMED — stale_artifact_globs ({globs}) "
            f"covers all required prefixes {required_prefixes}. "
            f"Spec-compliant (exact patterns may differ)."
        )
    else:
        print(
            f"NOT CONFIRMED — stale_artifact_globs ({globs}) "
            f"covers all required prefixes {required_prefixes}. "
            f"Spec-compliant and patterns match expected."
        )


if __name__ == "__main__":
    main()
```

### Probe Output

```
NOT CONFIRMED — stale_artifact_globs (['select_relevant_modules.md', 'relevant_modules.json', 'select_relevant_files_*.md', 'relevant_files_*.json', 'spec_update_*.md', 'spec_update_*.json']) covers all required prefixes ['select_relevant_', 'relevant_', 'spec_update_']. Spec-compliant and patterns match expected.
```
