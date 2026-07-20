# Bug Report: generate_topdown_layers

**Source file:** `src/generate_topdown_layers.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- For every phase in phases.json whose phase number matches the phase_numbers filter (or for all phases if phase_numbers is None), writes one file fm_agent/spec_prompts/phase_NN_topdown_layers.json where NN is the zero-padded phase number
  - Each output JSON contains the phase number, phase name, total number of functions within the phase (total_functions), total number of topological layers (total_layers), and a "layers" list of layer objects sorted by ascending layer index
  - Each layer object has a "layer" key (0-indexed integer); if the layer resolves a strongly connected component (mutual recursion), it also contains "cycle_resolution": true
  - Within each layer, "functions" is a list of entries, each with: "name" (FQN), "file" (relative path from proj_dir to the extracted function), "unit" (module name), phaseN_callers (FQNs of in-phase callers), phaseN_callees (FQNs of in-phase callees), and all_callees (FQNs of callees across all phases, including cross-phase edges)
  - Callers appear in strictly higher-numbered layers than their callees, except when both belong to the same SCC (cycle-resolution layer)
  - If edge_aliases_map contains supplemental names for a callee's entry from a particular caller, the function entry includes a phaseN_callee_info_names_by_caller map of caller FQN to sorted list of info names
  - If extra_call_edges is provided, the resulting call graph includes those edges in addition to edges derived from static analysis
  - Returns a list of absolute paths to the written JSON files, in the order the phases appear in phases.json; a phase with no extracted functions is skipped with a log warning and does not appear in the output

---

### Actual Behavior

The function terminates by returning the list `output_files`. This list contains exactly one element: `out_path` = os.path.join(output_dir, f"phase_{phase_num:02d}_topdown_layers.json"). The file at `out_path` exists and contains a valid JSON object, which was written with json.dump using indent=2 and ensure_ascii=False. The JSON object has the following structure and values:

- "phase": the integer phase_num (equal to phase_info['phase']).
- "phase_name": the string phase_name (equal to phase_info['name']).
- "total_functions": len(phase_fqns), where phase_fqns = set(file_map.keys()) from the 6-tuple returned by _build_call_graph for this phase.
- "total_layers": len(layers), where layers is the result of _compute_layers(phase_fqns, callees_map, callers_map).
- "layers": a list of dicts, each representing a topological layer computed by _compute_layers. The list is in ascending order of layer index. For each layer_dict:
    - "layer": the integer layer index (0based).
    - Optionally "cycle_resolution": true if and only if that layer originated from a strongly connected component (i.e., the corresponding layer_info from _compute_layers had "cycle_resolution" set to true).
    - "functions": a list of dicts, one per FQN that belongs to that layer. Each function dict contains:
        - "name": the fully qualified name fqn.
        - "file": the relative path from proj_dir to the extracted function file, i.e., os.path.relpath(file_map[fqn], proj_dir).
        - "unit": the module name from module_map.get(fqn, "") (an empty string if absent).
        - f"phase{phase_num}_callers": a sorted list of strings, the intersection of callers_map.get(fqn, set()) with phase_fqns, sorted lexicographically.
        - f"phase{phase_num}_callees": a sorted list of strings, the intersection of callees_map.get(fqn, set()) with phase_fqns, sorted lexicographically.
        - "all_callees": a sorted list of all c...

---

## Code Evidence

Line 98: return output_files

---

## Trigger Condition

The code block terminates after processing a single phase, returning a list containing exactly one output file path. The specification requires processing all phases that match the phase_numbers filter, writing a JSON file for each, and returning a list of all written file paths in the order the phases appear in phases.json. The missing iteration over phases and the immediate return violate the specification.

---

## How to trigger the bug

**The bug could NOT be reproduced.** The `return output_files` statement (line 756 in `src/generate_topdown_layers.py`) is positioned **outside** the `for phase_info in phases_data["phases"]:` loop (which spans lines 664-754). The function correctly iterates over all matching phases, appending each output file path to `output_files`, and only returns after the loop completes.

The probe script invoked `generate_topdown_layers` on the existing `fm_agent/` workspace, which contains `phases.json` with 6 phases and extracted functions for all phases. The function returned **6 output file paths**, one per phase, proving that all phases are processed.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `<repo_root>/fm_agent/` |

### Expected (spec-correct) Output

A list of 6 absolute file paths, one per phase in `phases.json`, in the order phases appear.

### Actual (buggy) Output

The function returned 6 file paths — exactly matching the specification. The claimed bug (returning only 1 file after the first phase) does not exist.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.generate_topdown_layers import generate_topdown_layers
proj_dir = "fm_agent"
result = generate_topdown_layers(proj_dir)
print(len(result))  # prints 6, not 1
```

---

## Probe Script

```python
import sys
import os

# Add repo root to path so we can import src.generate_topdown_layers
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.generate_topdown_layers import generate_topdown_layers

    # Use the fm_agent/ directory as proj_dir (it contains phases.json and extracted_functions/)
    proj_dir = os.path.join(repo_root, "fm_agent")

    result = generate_topdown_layers(proj_dir)

    num_files = len(result)
    # Bug claim: function returns after processing a single phase (only 1 output file)
    # Spec claim: function returns files for all phases that match the filter
    # If num_files > 1, the bug is NOT CONFIRMED (function processes all phases)
    # If num_files == 1, the bug is CONFIRMED
    buggy = num_files == 1

    if buggy:
        print(f"CONFIRMED — returned {num_files} file(s): {result}")
    else:
        print(f"NOT CONFIRMED — returned {num_files} file(s), proving the loop processes all phases. Files: {result}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
[TopdownLayers] Phase 1 (Environment & Pipeline Setup): 148 functions, 8 layers -> spec_prompts/phase_01_topdown_layers.json
[TopdownLayers] Phase 2 (Function Extraction & Call Graph Construction): 113 functions, 9 layers -> spec_prompts/phase_02_topdown_layers.json
[TopdownLayers] Phase 3 (Scope Analysis & Layer Organization): 48 functions, 4 layers -> spec_prompts/phase_03_topdown_layers.json
[TopdownLayers] Phase 4 (Specification Generation & Code Reasoning): 13 functions, 4 layers -> spec_prompts/phase_04_topdown_layers.json
[TopdownLayers] Phase 5 (Bug Diagnosis & Verification): 6 functions, 2 layers -> spec_prompts/phase_05_topdown_layers.json
[TopdownLayers] Phase 6 (Alternative Pipeline Entry Points): 52 functions, 5 layers -> spec_prompts/phase_06_topdown_layers.json
NOT CONFIRMED — returned 6 file(s), proving the loop processes all phases. Files: ['.../fm_agent/spec_prompts/phase_01_topdown_layers.json', '.../fm_agent/spec_prompts/phase_02_topdown_layers.json', '.../fm_agent/spec_prompts/phase_03_topdown_layers.json', '.../fm_agent/spec_prompts/phase_04_topdown_layers.json', '.../fm_agent/spec_prompts/phase_05_topdown_layers.json', '.../fm_agent/spec_prompts/phase_06_topdown_layers.json']
```
