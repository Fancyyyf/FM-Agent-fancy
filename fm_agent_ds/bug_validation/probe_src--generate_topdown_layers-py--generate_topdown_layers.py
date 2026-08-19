import sys
import os
import json
import tempfile

# Ensure the repo root is on sys.path for the public import
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.generate_topdown_layers import generate_topdown_layers
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Build a minimal project directory for testing
tmpdir = tempfile.mkdtemp(prefix="bug_probe_")

# Minimal phases.json — one phase
phases = {
    "phases": [
        {
            "phase": 1,
            "name": "Test Phase",
            "modules": [
                {
                    "name": "test_module",
                    "source_files": ["src/dummy.py"]
                }
            ]
        }
    ]
}
with open(os.path.join(tmpdir, "phases.json"), "w") as f:
    json.dump(phases, f)

# Create minimal extracted function file
func_dir = os.path.join(tmpdir, "extracted_functions", "src", "dummy-py")
os.makedirs(func_dir, exist_ok=True)
dummy_func_path = os.path.join(func_dir, "simple_func.py")
with open(dummy_func_path, "w") as f:
    f.write("def simple_func():\n    pass\n")

# Run the function under test
try:
    output_files = generate_topdown_layers(tmpdir)

    # The spec claims: files must be written under proj_dir/spec_prompts/
    # Check: does any output file path contain "spec_prompts"?
    spec_prompts_dir = os.path.join(tmpdir, "spec_prompts")
    expected_path = os.path.join(spec_prompts_dir, "phase_01_topdown_layers.json")

    # The trigger_condition says code writes to output_dir which is "not constrained",
    # but the code actually sets output_dir = os.path.join(proj_dir, "spec_prompts")
    # So the correct behavior IS to write under spec_prompts/
    actual_wrote_to_spec_prompts = os.path.isfile(expected_path)

    if actual_wrote_to_spec_prompts:
        # The spec says output files go under proj_dir/spec_prompts/
        # The code does write there — spec satisfied, NOT a bug
        print("NOT CONFIRMED — output file created at expected path:", expected_path)
        print("Code correctly writes to proj_dir/spec_prompts/ as specified.")
    else:
        # This would be a real bug — output went somewhere else
        print("CONFIRMED — output file NOT found at:", expected_path)
        print("Output files:", output_files)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # Cleanup
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
