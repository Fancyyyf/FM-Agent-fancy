import sys
import os
import tempfile

try:
    from src.incremental_reasoner import _modified_function_targets
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Create a temporary project directory with a fake source file ".hidden"
# in a "src" subdirectory to exercise the dotfile edge case.
tmp = tempfile.mkdtemp(prefix="probe_")
try:
    src_dir = os.path.join(tmp, "src")
    os.makedirs(src_dir)

    # Create a fake .hidden source file and a corresponding extracted-functions dir
    hidden_abs = os.path.join(src_dir, ".hidden")
    with open(hidden_abs, "w") as f:
        f.write("")

    # Also create the expected extracted dir for the -hidden case (spec-correct)
    spec_extracted_dir = os.path.join(tmp, "fm_agent", "extracted_functions", "src", "-hidden")
    os.makedirs(spec_extracted_dir)

    modified_functions = {hidden_abs: {"added": ["myfunc"]}}

    result = _modified_function_targets(tmp, modified_functions)

    # Determine what the spec-correct behavior should be.
    # Spec says: basename contains a dot → final dot replaced by hyphen.
    # ".hidden" has a dot at index 0, so dir_name = "-hidden", ext = "hidden"
    spec_extracted_dir = os.path.join(tmp, "fm_agent", "extracted_functions", "src", "-hidden")
    spec_fname = "myfunc.hidden"
    spec_path = os.path.join(spec_extracted_dir, spec_fname)

    # Determine what the buggy code produced.
    # The buggy code (last_dot > 0 check) treats .hidden as having no dot:
    # dir_name = ".hidden", ext = ""
    bug_extracted_dir = os.path.join(tmp, "fm_agent", "extracted_functions", "src", ".hidden")
    bug_fname = "myfunc"
    bug_path = os.path.join(bug_extracted_dir, bug_fname)

    # Check: does the actual result match the buggy path or the spec-correct path?
    actual_paths = list(result.values())
    actual_fqns = list(result.keys())

    if not actual_fqns:
        print("ERROR: result is empty — no targets returned")
        sys.exit(1)

    actual_path = actual_paths[0]
    actual_fqn = actual_fqns[0]

    # The spec says the FQN should contain "-hidden" as the last component before "::myfunc"
    # For the buggy case (no dot processing), the directory component would be ".hidden"
    # For the spec-correct case, it would be "-hidden"

    # Expected behavior per spec: the file .hidden has a dot, so:
    #   dir_name = "-hidden", ext = "hidden"
    # This means the FQN should have "-hidden" in it, not ".hidden"
    expected_has_dash_hidden = "-hidden::myfunc" in actual_fqn or actual_fqn.endswith("::myfunc")
    # But actually the leaf function name in FQN is "myfunc" (extension stripped by _file_to_fqn)
    # And the directory component should be "-hidden" not ".hidden"

    # Simpler check: spec expects the path dir to be "-hidden" not ".hidden"
    actual_fqn_dir = actual_fqn.rsplit("::", 1)[0]
    fqn_last_component = actual_fqn_dir.split("::")[-1] if "::" in actual_fqn_dir else actual_fqn_dir

    bug_confirmed = ".hidden" in fqn_last_component and "-hidden" not in fqn_last_component
    # The spec-correct behavior should have "-hidden" last component
    spec_correct_last = "-hidden"

    passed = bug_confirmed  # True if the buggy behavior is observed

    if passed:
        print(
            f"CONFIRMED — actual FQN last component: '{fqn_last_component}' "
            f"| expected (spec) last component: '{spec_correct_last}' "
            f"| actual path: {actual_path}"
        )
    else:
        print(
            f"NOT CONFIRMED — actual FQN last component: '{fqn_last_component}' "
            f"| actual path: {actual_path}"
        )

    # Cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
