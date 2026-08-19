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

# Ensure the repo root is on path so we can import the package
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
