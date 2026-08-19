# Bug Report: generate_topdown_layers

**Source file:** `src/generate_topdown_layers.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

For every phase in phases.json whose phase number is included in phase_numbers (or for every phase when phase_numbers is not provided or empty), a file named phase_NN_topdown_layers.json is written under proj_dir/spec_prompts/ where NN is the zero-padded two-digit phase number. Each file contains a JSON object with keys: 'phase' (the integer phase number), 'phase_name' (string), 'total_functions' (non-negative integer equal to the count of unique function FQNs across all layers), 'total_layers' (non-negative integer equal to the layer count), and 'layers' (a list of layer objects). Each layer object has: 'layer' (an integer layer index) and 'functions' (a list of function-entry objects, each containing at minimum 'name' (FQN string), 'file' (a string path relative to proj_dir), and 'all_callees' (a list of callee FQN strings)). Functions within a layer are ordered such that every callee of a function in layer L belongs to a layer with integer index strictly less than L or is a function not present in any phase. A phase whose definition maps to zero extracted function files produces a warning via the logging system and yields no output file. Already-existing files at the output paths are silently overwritten. Returns a list of absolute file-path strings for every JSON file written; returns an empty list when all phases are skipped.

---

### Actual Behavior

Let out_path = os.path.join(output_dir, f"phase_{phase_num:02d}_topdown_layers.json") and let output_files_0 be the list output_files before this block.

Normal execution (no exception):
- The function returns R = output_files_0 ++ [out_path].
- A file at absolute path out_path now exists and contains a valid JSON object O as encoded by json.dump with indent=2 and ensure_ascii=False.
- O satisfies:
    O.phase = phase_num
    O.phase_name = phase_name
    O.total_functions = |phase_fqns|
    O.total_layers = len(layers)
    O.layers is a list whose i-th element corresponds to layers[i] from the call _compute_layers(phase_fqns, callees_map, callers_map).
    For each layer_info in layers:
        - The layer dict L in O.layers has L.layer = layer_info['layer'].
        - If layer_info['cycle_resolution'] is truthy, L.cycle_resolution = true; otherwise this key is absent.
        - L.functions is a list of entry dicts, one per fqn in layer_info['functions'], preserving the order from layer_info['functions'].
        - Each entry E for fqn satisfies:
            E.name = fqn
            E.file = relpath(file_map[fqn], proj_dir)   (relative path from proj_dir to the file containing the function)
            E.unit = module_map.get(fqn, "")
            E["phase<phase_num>_callers"] = sorted(callers_map.get(fqn, {})  phase_fqns)
            E["phase<phase_num>_callees"] = sorted(callees_map.get(fqn, {})  phase_fqns)
            E.all_callees = sorted(all_callees_map.get(fqn, {}))
            If edge_aliases_map contains any caller->info_names mapping for fqn with caller in phase_fqns and non-empty info_names, then E["phase<phase_num>_callee_info_names_by_caller"] = { caller: sorted(info_names) for caller, info_names in edge_aliases_map[fqn].items() if caller in phase_fqns and info_names };
            otherwise this key is absent.
- No other file system object under proj_dir is created, modified, or deleted by this... (line truncated to 2000 chars)

---

## Code Evidence

Line 93: out_path = os.path.join(output_dir, f"phase_{phase_num:02d}_topdown_layers.json")

---

## Trigger Condition

The specification requires output files to be written under proj_dir/spec_prompts/, but the code writes to output_dir, which is not constrained to that location. For the given valid input, the code creates /tmp/output/phase_01_topdown_layers.json instead of /home/user/project/spec_prompts/phase_01_topdown_layers.json.

---

## How to trigger the bug

The specified bug cannot be triggered. The actual source code at `src/generate_topdown_layers.py` line 657 explicitly sets `output_dir = os.path.join(proj_dir, "spec_prompts")`, which constrains the output directory to `proj_dir/spec_prompts/` — exactly matching the specification requirement. The gap detection appears to have only considered the `os.path.join(output_dir, ...)` expression on line 755 without noticing that `output_dir` was already bound to the spec-compliant path on line 657.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `/tmp/bug_probe_wkfbuddf` (temporary directory) |
| `phase_numbers` | `None` (all phases) |
| `extra_call_edges` | `None` |

### Expected (spec-correct) Output

Output file written to `<proj_dir>/spec_prompts/phase_01_topdown_layers.json`

### Actual (buggy) Output

Output file written to `<proj_dir>/spec_prompts/phase_01_topdown_layers.json` — matches expected

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.generate_topdown_layers import generate_topdown_layers

# Setup: create a minimal proj_dir with phases.json and an extracted function
# The function writes to proj_dir/spec_prompts/phase_01_topdown_layers.json
output_files = generate_topdown_layers(proj_dir)
# actual (buggy) output: /tmp/.../spec_prompts/phase_01_topdown_layers.json
# expected (correct) output: /tmp/.../spec_prompts/phase_01_topdown_layers.json
# → outputs match, bug NOT CONFIRMED
```

---

## Probe Script

```python
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
```

### Probe Output

```
[TopdownLayers] Phase 1 (Test Phase): 1 functions, 1 layers -> spec_prompts/phase_01_topdown_layers.json
NOT CONFIRMED — output file created at expected path: /tmp/bug_probe_wkfbuddf/spec_prompts/phase_01_topdown_layers.json
Code correctly writes to proj_dir/spec_prompts/ as specified.
```
