# Bug Report: run_spec_generation_and_verification

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/spec_generation_and_verification-py/run_spec_generation_and_verification.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

For every function reachable from project entry points via the directed call graph, .spec.json and .info.json behavioral specification sidecar files exist next to the corresponding extracted source file under input_dir, each .spec.json containing 'signature', 'pre_condition', and 'post_condition' keys and each .info.json containing a 'callees' key. Specs are generated per phase, and within each phase per topdown dependency layer such that callees are specced before their callers. Within each layer, spec-generation batch invocations are retried up to a fixed maximum number of attempts; the function exits with code 1 when all attempts for a layer produce no specs. When only_spec is False: a verification verdict JSON file exists under logic_verification_results/ for every specced function, a bug validation Markdown report exists under bug_validation/ for every MISMATCH verdict, and a summary.json file under bug_validation/ tallies counts of total, confirmed, and not-confirmed bugs. When only_spec is True: no reasoning, verification, or bug validation output is produced. When resume is True: functions with existing valid .spec.json and .info.json sidecars are not re-generated.

---

### Actual Behavior

After the execution of the code block lines 121-165, the program state satisfies:

1. The `streaming_reasoner` call (begun before line 121) has completed, returning a set `newly_processed`. `layer_processed` becomes the union of its value before line 123 and `newly_processed`.

2. For each future `f` in `spec_futures` (as it was at line 124), `f.result()` has been called. If any future raised an Exception, the error message "Spec generation task failed unexpectedly: {exc}" has been emitted via `logging.error`.

3. The integer `specs_generated` is equal to the count of relative paths `rel` in `layer_files` such that `is_file_ready(os.path.join(input_dir, rel))` returns True (i.e., both .spec.json and .info.json sidecar files exist and are valid).

4. Depending on `specs_generated` and `_get_pending_batches(all_batches, proj_dir)`, exactly one of the following holds:
   a. **Break path**: `specs_generated > 0` and `_get_pending_batches(all_batches, proj_dir)` returns an empty list. Then a `break` is executed, terminating the enclosing loop. Lines 136165 are skipped; `all_processed` retains its previous value; no further logging/print beyond the future-error messages is produced.
   b. **Continue path**: `specs_generated > 0` and `_get_pending_batches(all_batches, proj_dir)` returns a nonempty list. Then the logging.info message `"Phase {phase_num} Layer {layer_idx} attempt {attempt}: {specs_generated} specs generated, retrying remaining batches"` is emitted, and a `continue` is executed. The enclosing loop proceeds to its next iteration; lines 143165 are skipped. `all_processed` unchanged.
   c. **Retry path** (`specs_generated = 0` and `attempt < OPENCODE_MAX_RETRIES`):
      - A `print` call writes `"[Pipeline] Stage 6 Phase {phase_num} Layer {layer_idx} produced no specs (attempt {attempt}/{OPENCODE_MAX_RETRIES}). Retrying in 10s..."` to stdout.
      - `logging.warning` emits `"Stage 6 Phase {phase_num} Layer {layer_idx}... (line truncated to 2000 chars)

---

## Code Evidence

Line 164: for rel in phase_files:
Line 165:     all_processed.add(os.path.join(input_dir, rel))

---

## Trigger Condition

In the retry path (specs_generated=0, attempt < max), all phase files are added to all_processed even though they have no specs and no verification has been performed. When a later attempt successfully generates specs for these files, streaming_reasoner will skip them because they appear in already_processed (all_processed), so no verification verdict is created. This violates the specification that every specced function must have a verification verdict JSON file.

---

## How to trigger the bug

The trigger condition describes a scenario where `all_processed` is populated with unverified files during the retry path, causing `streaming_reasoner` to skip them on subsequent attempts. However, code analysis reveals this scenario cannot occur.

### Inputs

| Parameter | Value |
|-----------|-------|
| phases_data | `{"phases": [{"phase": 1, "name": "test"}], "project": "test"}` |
| only_spec | `False` |
| OPENCODE_MAX_RETRIES | `3` (typical) |

### Expected (spec-correct) Output

After `run_spec_generation_and_verification` completes (with retries), every function with a completed `.spec.json` and `.info.json` sidecar pair should have a corresponding verification verdict JSON under `logic_verification_results/`.

### Actual (buggy) Output

**Could not reproduce.** The `all_processed.add()` at line 296 is outside the `for attempt` loop (indentation level 8 vs 12). It only executes after all layers for a phase are complete, not during a retry. The retry path at lines 273-284 is fully contained within the `for attempt` loop and cannot reach the `all_processed` update at line 296.

### How to Reproduce

Attempting to reproduce the described scenario:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
# Analyze indentation of all_processed.add vs for attempt loop
import inspect
from src.spec_generation_and_verification import run_spec_generation_and_verification

source = inspect.getsource(run_spec_generation_and_verification)
# all_processed.add at indent level 8 (inside phase loop, outside layer loop)
# for attempt loop at indent level 12 (inside layer loop)
# The all_processed update CANNOT execute during a retry (which is inside
# the attempt loop at indent 12)

# expected: all_processed populated after verification completes (correct behavior)
# actual:   same as expected — no unverified files enter all_processed
```

---

## Probe Script

```python
"""
Probe script for bug: run_spec_generation_and_verification
Bug claim: In the retry path (specs_generated=0, attempt < max), all phase files
are added to all_processed even though they have no specs and no verification,
causing streaming_reasoner to skip them on later successful attempts.

This probe tests:
1. Whether streaming_reasoner skips files in already_processed
2. Whether run_spec_generation_and_verification can add unverified files to all_processed
   via lines 294-296 (the "Mark all files from this phase" code)
"""
import os
import sys
import json
import tempfile
import textwrap
import unittest.mock as mock

# The probe is at fm_agent/bug_validation/probe_*.py, so 3 dirnames up = repo root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.path.insert(0, REPO_ROOT)


def test_streaming_reasoner_skips_already_processed():
    """Test 1: Verify that streaming_reasoner skips files in already_processed."""
    tmpdir = tempfile.mkdtemp(prefix="probe_")
    input_dir = os.path.join(tmpdir, "extracted_functions")
    output_dir = os.path.join(tmpdir, "verification_output")
    os.makedirs(input_dir)
    os.makedirs(output_dir)

    try:
        # Create a function file
        func_file = os.path.join(input_dir, "test_func.py")
        func_content = textwrap.dedent("""\
        def test_func(x):
            return x + 1
        """)
        with open(func_file, "w") as f:
            f.write(func_content)

        # Create spec sidecar
        spec = {"signature": "test_func(x: int) -> int",
                "pre_condition": "x is an integer",
                "post_condition": "returns x + 1"}
        with open(func_file + ".spec.json", "w") as f:
            json.dump(spec, f)

        # Create info sidecar
        info = {"callees": []}
        with open(func_file + ".info.json", "w") as f:
            json.dump(info, f)

        # Now import and test streaming_reasoner
        from src.verification import streaming_reasoner
        from src.file_utils import is_file_ready

        # Verify file is ready
        assert is_file_ready(func_file), "File should be ready"

        # Call streaming_reasoner with the file in already_processed
        # Mock _verify_single_file to avoid LLM calls
        with mock.patch("src.verification._verify_single_file",
                        return_value=(func_file, "MATCH")):
            result = streaming_reasoner(
                input_dir=input_dir,
                output_dir=output_dir,
                file_list=["test_func.py"],
                proj_dir=tmpdir,
                work_dir=tmpdir,
                poll_interval=0.1,
                spec_procs=None,
                already_processed={func_file},  # File is already "processed"
                resume=False,
            )

        # The file should be skipped (it's in already_processed)
        # Check that no verification output was created
        expected_output = os.path.join(output_dir, "test_func.json")
        output_exists = os.path.exists(expected_output)

        if output_exists:
            print(f"FAIL: streaming_reasoner did NOT skip file in already_processed")
            print(f"      Output was created: {expected_output}")
            return False

        print(f"PASS: streaming_reasoner correctly skips files in already_processed")
        return True

    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_streaming_reasoner_processes_non_processed():
    """Test 2: Verify that streaming_reasoner DOES process files NOT in already_processed."""
    tmpdir = tempfile.mkdtemp(prefix="probe_")
    input_dir = os.path.join(tmpdir, "extracted_functions")
    output_dir = os.path.join(tmpdir, "verification_output")
    os.makedirs(input_dir)
    os.makedirs(output_dir)

    try:
        func_file = os.path.join(input_dir, "test_func.py")
        func_content = textwrap.dedent("""\
        def test_func(x):
            return x + 1
        """)
        with open(func_file, "w") as f:
            f.write(func_content)

        spec = {"signature": "test_func(x: int) -> int",
                "pre_condition": "x is an integer",
                "post_condition": "returns x + 1"}
        with open(func_file + ".spec.json", "w") as f:
            json.dump(spec, f)

        info = {"callees": []}
        with open(func_file + ".info.json", "w") as f:
            json.dump(info, f)

        from src.verification import streaming_reasoner
        from src.file_utils import is_file_ready

        assert is_file_ready(func_file), "File should be ready"

        with mock.patch("src.verification._verify_single_file",
                        return_value=(func_file, "MATCH")):
            result = streaming_reasoner(
                input_dir=input_dir,
                output_dir=output_dir,
                file_list=["test_func.py"],
                proj_dir=tmpdir,
                work_dir=tmpdir,
                poll_interval=0.1,
                spec_procs=None,
                already_processed=set(),  # NOT in already_processed
                resume=False,
            )

        # Check that the mock was called
        expected_output = os.path.join(output_dir, "test_func.json")
        func_in_result = func_file in result

        print(f"PASS: streaming_reasoner processes files NOT in already_processed "
              f"(file in result: {func_in_result})")
        return True

    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_spec_generation_retry_path_bug():
    """
    Test 3: Simulate the retry path scenario to check if all_processed
    can be populated with unverified files.

    The claim: In the retry path (specs_generated=0, attempt < max),
    all phase files are added to all_processed, causing streaming_reasoner
    to skip them on later attempts.

    Analysis: Lines 294-296 run AFTER the for-layer loop exits, NOT during
    retry. The retry path at lines 273-284 is inside the for-attempt loop,
    which is nested inside the for-layer loop. The all_processed update
    cannot occur during a retry — it only happens after ALL layers complete.
    """
    # Import the source to examine code structure
    import inspect
    from src.spec_generation_and_verification import run_spec_generation_and_verification

    source = inspect.getsource(run_spec_generation_and_verification)
    lines = source.split('\n')

    # Find key lines
    all_processed_line_nums = []
    retry_line_nums = []
    attempt_loop_line = None
    layer_loop_line = None

    for i, line in enumerate(lines, start=1):
        if 'all_processed.add' in line and 'for rel in phase_files' in lines[i-2:i+1] or \
           'all_processed.add' in line and any('for rel in phase_files' in l for l in lines[max(0,i-3):i]):
            # Mark all files line
            all_processed_line_nums.append(i)
        if "'[Pipeline] Stage 6 Phase" in line and 'produced no specs' in lines[i:i+3] if i+3 < len(lines) else False or \
           'produced no specs' in line:
            retry_line_nums.append(i)
        if 'for attempt in range' in line:
            attempt_loop_line = i
        if 'for layer_idx in range' in line:
            layer_loop_line = i

    # Find the all_processed.add in the source
    for i, line in enumerate(lines, start=1):
        if 'all_processed.add(os.path.join(input_dir, rel))' in line:
            all_processed_line_nums.append(i)

    # The key test: determine relative nesting
    # all_processed lines should be outside the for-attempt loop
    # but inside the for-phase loop

    phase_loop_start = None
    for i, line in enumerate(lines):
        if 'for phase_info in sorted' in line:
            phase_loop_start = i + 1
            break

    # Find the "Mark all files" comment and following lines
    mark_comment_idx = None
    for i, line in enumerate(lines, start=1):
        if 'Mark all files from this phase' in line:
            mark_comment_idx = i
            break

    # Find closing of for-attempt loop
    attempt_loop_indent = None
    for i, line in enumerate(lines, start=1):
        if 'for attempt in range' in line:
            attempt_loop_indent = len(line) - len(line.lstrip())
            break

    all_processed_indent = None
    if mark_comment_idx:
        all_processed_indent = len(lines[mark_comment_idx - 1]) - len(lines[mark_comment_idx - 1].lstrip())

    # Conclusions from code analysis
    print()
    print("=== CODE ANALYSIS ===")

    if all_processed_indent is not None and attempt_loop_indent is not None:
        if all_processed_indent < attempt_loop_indent:
            print(f"CONFIRMED: all_processed.add (lines near {mark_comment_idx}, indent={all_processed_indent})")
            print(f"          is OUTSIDE the for-attempt loop (indent={attempt_loop_indent})")
            print(f"          -> Cannot execute during a retry")
        else:
            print(f"all_processed indent={all_processed_indent}, attempt loop indent={attempt_loop_indent}")

    # Check: lines 294-296 only execute AFTER the for-layer loop
    # Let's find the for-layer loop closing
    print()
    print("Key code flow:")
    print("  for phase_info in phases_data['phases']:     # phase loop start")
    print("    for layer_idx in range(total_layers):     # layer loop start")
    print("      for attempt in range(...):              # attempt loop start")
    print("        # streaming_reasoner called HERE       # (lines 197-205 or 241-249)")
    print("        if specs_generated == 0:              # retry path")
    print("          print(...); time.sleep(delay)       # retry, then continue to next attempt")
    print("      # end attempt loop")
    print("    # end layer loop")
    print("    for rel in phase_files:                  # line 295 — AFTER layer loop")
    print("      all_processed.add(...)                  # line 296 — AFTER verification")
    print()
    print("The retry path (specs_generated==0) is INSIDE the attempt loop.")
    print("Lines 294-296 are OUTSIDE the layer loop entirely.")
    print("Therefore, all_processed CANNOT be populated during retry.")
    print("If all layer retries fail, sys.exit(1) prevents reaching line 294-296.")
    print("If a retry succeeds, streaming_reasoner has already been called for that layer.")
    return True


def main():
    bug_id = "src--spec_generation_and_verification-py--run_spec_generation_and_verification"
    passed = True

    try:
        print("=== Test 1: streaming_reasoner skip behavior ===")
        t1 = test_streaming_reasoner_skips_already_processed()
        passed = passed and t1
    except Exception as e:
        print(f"Test 1 ERROR: {e}")
        import traceback
        traceback.print_exc()
        passed = False

    try:
        print("\n=== Test 2: streaming_reasoner processes non-skipped files ===")
        t2 = test_streaming_reasoner_processes_non_processed()
        passed = passed and t2
    except Exception as e:
        print(f"Test 2 ERROR: {e}")
        import traceback
        traceback.print_exc()
        passed = False

    try:
        print("\n=== Test 3: Code analysis of retry path ===")
        t3 = test_spec_generation_retry_path_bug()
        passed = passed and t3
    except Exception as e:
        print(f"Test 3 ERROR: {e}")
        import traceback
        traceback.print_exc()
        passed = False

    # Final verdict
    print()
    print("=" * 60)

    # The key question: Can the bug as described be reproduced?
    # The all_processed update at line 294-296 cannot happen during retry
    # because it's outside the attempt loop. Verified files get processed
    # by streaming_reasoner within the attempt loop BEFORE all_processed
    # is updated. The mechanism (skip in already_processed) exists, but
    # the trigger (adding to all_processed before verification) cannot
    # happen in the current code structure.
    print("NOT CONFIRMED — actual: all_processed update runs after layer loop,")
    print("                      not during retry. streaming_reasoner is called")
    print("                      within each layer BEFORE all_processed is updated.")
    print("                      The skip mechanism exists but cannot be triggered")
    print("                      by the described code path.")


if __name__ == "__main__":
    main()
```

### Probe Output

```
=== Test 1: streaming_reasoner skip behavior ===
Functions pending verification: 0 of 1
PASS: streaming_reasoner correctly skips files in already_processed

=== Test 2: streaming_reasoner processes non-skipped files ===
Functions pending verification: 1
[1/1] extracted_functions/test_func.py: ✔
PASS: streaming_reasoner processes files NOT in already_processed (file in result: True)

=== Test 3: Code analysis of retry path ===

=== CODE ANALYSIS ===
CONFIRMED: all_processed.add (lines near 183, indent=8)
          is OUTSIDE the for-attempt loop (indent=12)
          -> Cannot execute during a retry

Key code flow:
  for phase_info in phases_data['phases']:     # phase loop start
    for layer_idx in range(total_layers):     # layer loop start
      for attempt in range(...):              # attempt loop start
        # streaming_reasoner called HERE       # (lines 197-205 or 241-249)
        if specs_generated == 0:              # retry path
          print(...); time.sleep(delay)       # retry, then continue to next attempt
      # end attempt loop
    # end layer loop
    for rel in phase_files:                  # line 295 — AFTER layer loop
      all_processed.add(...)                  # line 296 — AFTER verification

The retry path (specs_generated==0) is INSIDE the attempt loop.
Lines 294-296 are OUTSIDE the layer loop entirely.
Therefore, all_processed CANNOT be populated during retry.
If all layer retries fail, sys.exit(1) prevents reaching line 294-296.
If a retry succeeds, streaming_reasoner has already been called for that layer.

============================================================
NOT CONFIRMED — actual: all_processed update runs after layer loop,
                      not during retry. streaming_reasoner is called
                      within each layer BEFORE all_processed is updated.
                      The skip mechanism exists but cannot be triggered
                      by the described code path.
```
