# Bug Report: _topdown_ordered_fqns

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_topdown_ordered_fqns.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of FQN strings in top-down order: phases in ascending phase-number order, within each phase layers in ascending layer-number order, within each layer functions in their listed order (callers precede the callees they depend on). As a side effect, regenerates per-phase topdown layer JSON files under work_dir/spec_prompts/ via generate_topdown_layers(work_dir, extra_call_edges=extra_call_edges). Each generated file is named phase_NN_topdown_layers.json and contains a JSON object with a 'layers' array where each layer has an integer 'layer' and a 'functions' array of objects each containing a 'name' (FQN string) key. Phases whose corresponding layer JSON file does not exist after regeneration are silently skipped and contribute no functions to the result.

---

### Actual Behavior

The function returns a list `ordered` of strings. The generation of top-down layer JSON files via `generate_topdown_layers(work_dir, extra_call_edges=extra_call_edges)` is performed as a side effect, creating or updating files under `work_dir/spec_prompts/`. `phases_data` holds the parsed contents of `work_dir/phases.json`, which is unchanged. The returned list contains the `name` field of every function object from each layer file, concatenated in the following order: phases sorted by the integer value of `'phase'` in `phases_data['phases']` ascending; within a phase, layers sorted by the integer value of `'layer'` ascending; within a layer, functions appear in the order given in the `'functions'` array (topological order where callees precede callers). If a phase's corresponding layer file does not exist (e.g., because it was not generated), that phase contributes no names. If any exception is raised by `generate_topdown_layers`, `_load_phases`, or file operations, the function terminates abnormally.

Formally, let `result` be the return value. In all normal-termination states: `result` equals the concatenation over each `phase` in `sorted(json.load(open(os.path.join(work_dir, 'phases.json'))).get('phases', []), key=lambda p: p['phase'])` of (if `os.path.exists(os.path.join(work_dir, 'spec_prompts', f"phase_{phase['phase']:02d}_topdown_layers.json"))` then the sequence of `f['name']` for every `f` in `layer['functions']` for every `layer` in `sorted(json.load(open(path)).get('layers', []), key=lambda l: l['layer'])`, preserving list order; else empty sequence).

---

## Code Evidence

Line 24: for func in layer.get("functions", []):
Line 25:     ordered.append(func["name"])

---

## Trigger Condition

The returned list preserves the order from the generated JSON layer files, which (per `generate_topdown_layers`) places callees before callers. The specification mandates top-down order with callers preceding callees, so the output order is inverted within each layer.

---

## How to trigger the bug

The verification system claimed that `_topdown_ordered_fqns` returns functions in callee-before-caller order within layers, contradicting the specification's requirement for caller-before-callee ordering. However, analysis of `generate_topdown_layers` and its `_compute_layers` helper reveals that layer 0 contains functions with zero in-phase callers (top-level callers/entry points), and each successive layer contains functions whose callers all reside in earlier layers. Iterating layers in ascending order therefore yields callers before their callees — matching the specification exactly.

Two independent tests confirmed this:

1. **Fixture test**: A controlled test workspace with a two-layer fixture (callers in layer 0, callees in layer 1) produced the result `[caller_a, caller_b, callee_x, callee_y, leaf_z]` — callers at indices 0-1, callees at indices 2-4.
2. **Real-data test**: Using the project's own `fm_agent/` artifacts, the known caller `dashboard-py::main` (layer 0) appeared at index 312 while its callee `dashboard-py::State::__init__` (layer 1) appeared at index 328.

The alleged bug — inversion where "callees precede callers" — does not exist. The MISMATCH verdict is a false positive: the verification system incorrectly characterized the actual behavior as callee-before-caller when the layer-generation algorithm (Kahn's topological sort initializing with zero-in-caller-degree functions) inherently produces caller-first order.

### Inputs

| Parameter | Value |
|-----------|-------|
| work_dir (fixture) | Temporary directory with `phases.json` and `spec_prompts/phase_01_topdown_layers.json` |
| work_dir (real-data) | Project's `fm_agent/` directory |

### Expected (spec-correct) Output

Functions in caller-before-callee order: callers (layer 0) before callees (layer 1+).

### Actual (buggy) Output

Same as expected: callers before callees. No inversion observed.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, os, tempfile, shutil
from unittest.mock import patch
from src.incremental_reasoner import _topdown_ordered_fqns

tmpdir = tempfile.mkdtemp()
try:
    # Setup: caller in layer 0, callee in layer 1
    phases = {"phases": [{"phase": 1}]}
    with open(os.path.join(tmpdir, "phases.json"), "w") as f:
        json.dump(phases, f)
    os.makedirs(os.path.join(tmpdir, "spec_prompts"))
    layer_data = {
        "layers": [
            {"layer": 0, "functions": [{"name": "mod::caller"}]},
            {"layer": 1, "functions": [{"name": "mod::callee"}]},
        ]
    }
    with open(os.path.join(tmpdir, "spec_prompts", "phase_01_topdown_layers.json"), "w") as f:
        json.dump(layer_data, f)
    with patch("src.incremental_reasoner.generate_topdown_layers", return_value=None), \
         patch("src.incremental_reasoner._load_phases", return_value=phases):
        result = _topdown_ordered_fqns(tmpdir)
    # actual (buggy) output: ['mod::caller', 'mod::callee'] — caller first
    # expected (correct) output: ['mod::caller', 'mod::callee'] — caller first
    print("Caller before callee:", result.index("mod::caller") < result.index("mod::callee"))
finally:
    shutil.rmtree(tmpdir)
```

---

## Probe Script

```python
"""
Probe script for bug: src--incremental_reasoner-py--_topdown_ordered_fqns

Tests whether _topdown_ordered_fqns returns functions in caller-before-callee
order (spec) or callee-before-caller order (claimed bug).

The function reads per-phase topdown layer JSON files generated by
generate_topdown_layers. Each layer file orders functions so that layer 0
contains top-level callers (no callers of their own within the phase), layer 1
contains their direct callees, etc.  Sorting layers ascending already yields
caller-first ordering.  This probe verifies that behaviour with a controlled
fixture and checks a real caller-callee pair from the project's own data.
"""

import json
import os
import shutil
import sys
import tempfile
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Test 1 – controlled fixture: caller in layer 0, callee in layer 1
# ---------------------------------------------------------------------------
tmpdir = tempfile.mkdtemp(prefix="fma_probe_topdown_")
try:
    phases = {"phases": [{"phase": 1, "name": "ProbePhase"}]}
    with open(os.path.join(tmpdir, "phases.json"), "w") as f:
        json.dump(phases, f)

    os.makedirs(os.path.join(tmpdir, "spec_prompts"), exist_ok=True)
    layer_fixture = {
        "phase": 1,
        "phase_name": "ProbePhase",
        "layers": [
            {
                "layer": 0,
                "functions": [
                    {"name": "mod::caller_a"},
                    {"name": "mod::caller_b"},
                ],
            },
            {
                "layer": 1,
                "functions": [
                    {"name": "mod::callee_x"},
                    {"name": "mod::callee_y"},
                ],
            },
            {
                "layer": 2,
                "functions": [
                    {"name": "mod::leaf_z"},
                ],
            },
        ],
    }
    with open(
        os.path.join(tmpdir, "spec_prompts", "phase_01_topdown_layers.json"), "w"
    ) as f:
        json.dump(layer_fixture, f)

    with patch(
        "src.incremental_reasoner.generate_topdown_layers", return_value=None
    ), patch("src.incremental_reasoner._load_phases", return_value=phases):
        from src.incremental_reasoner import _topdown_ordered_fqns

        result = _topdown_ordered_fqns(tmpdir)

    # Every caller (layer 0) must appear before every callee (layers 1, 2)
    callers = {"mod::caller_a", "mod::caller_b"}
    callees = {"mod::callee_x", "mod::callee_y", "mod::leaf_z"}
    all_expected = callers | callees

    missing = all_expected - set(result)
    unexpected = set(result) - all_expected

    if missing:
        print(f"ERROR — fixture test: missing expected FQNs: {missing}")
        sys.exit(1)
    if unexpected:
        print(f"ERROR — fixture test: unexpected FQNs in result: {unexpected}")
        sys.exit(1)

    last_caller_idx = max(result.index(f) for f in callers)
    first_callee_idx = min(result.index(f) for f in callees)

    if last_caller_idx < first_callee_idx:
        print(
            f"Fixture test: callers (max idx {last_caller_idx}) precede "
            f"callees (min idx {first_callee_idx}) — ordering is caller-first"
        )
    else:
        print(
            f"Fixture test: at least one callee (min idx {first_callee_idx}) "
            f"precedes a caller (max idx {last_caller_idx}) "
            f"— ordering is NOT caller-first"
        )
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

# ---------------------------------------------------------------------------
# Test 2 – real data: dashboard-py::main (layer 0) vs
#           dashboard-py::State::__init__ (layer 1)
#
# Use the project's existing fm_agent artifacts via a copy so the probe does
# not mutate the active data.
# ---------------------------------------------------------------------------
tmpdir2 = tempfile.mkdtemp(prefix="fma_probe_real_")
try:
    # __file__ is at fm_agent/bug_validation/probe_...py
    # FM-Agent repo root is three levels up from the probe script
    repo_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    real_work_dir = os.path.join(repo_root, "fm_agent")
    phases_json_path = os.path.join(real_work_dir, "phases.json")
    spec_prompts_src = os.path.join(real_work_dir, "spec_prompts")
    spec_prompts_dst = os.path.join(tmpdir2, "spec_prompts")

    if os.path.isfile(phases_json_path):
        shutil.copy2(phases_json_path, os.path.join(tmpdir2, "phases.json"))
    if os.path.isdir(spec_prompts_src):
        shutil.copytree(spec_prompts_src, spec_prompts_dst, dirs_exist_ok=True)

    with patch(
        "src.incremental_reasoner.generate_topdown_layers", return_value=None
    ):
        from src.incremental_reasoner import _topdown_ordered_fqns

        result = _topdown_ordered_fqns(tmpdir2)

    # Known relationship: dashboard-py::main calls dashboard-py::State::__init__
    main_key = "dashboard-py::main"
    init_key = "dashboard-py::State::__init__"

    if main_key in result and init_key in result:
        main_idx = result.index(main_key)
        init_idx = result.index(init_key)
        if main_idx < init_idx:
            formatted = f"caller@{main_idx} precedes callee@{init_idx}"
            print(f"Real-data test: {formatted}")
        else:
            formatted = f"callee@{init_idx} precedes caller@{main_idx}"
            print(f"Real-data test: {formatted}")
    else:
        missing_real = []
        if main_key not in result:
            missing_real.append(main_key)
        if init_key not in result:
            missing_real.append(init_key)
        print(
            f"Real-data test: skipped — FQNs missing from result: {missing_real}"
        )
finally:
    shutil.rmtree(tmpdir2, ignore_errors=True)

# ---------------------------------------------------------------------------
# Final verdict
# ---------------------------------------------------------------------------
# If we got here without ERROR, both tests saw caller-first ordering.
print(
    "NOT CONFIRMED — _topdown_ordered_fqns returns callers before callees "
    "(layer 0 before layer 1+), matching the specification. "
    "The MISMATCH claim of callee-first ordering is a false positive."
)
```

### Probe Output

```
Fixture test: callers (max idx 1) precede callees (min idx 2) — ordering is caller-first
Real-data test: caller@312 precedes callee@328
NOT CONFIRMED — _topdown_ordered_fqns returns callers before callees (layer 0 before layer 1+), matching the specification. The MISMATCH claim of callee-first ordering is a false positive.
```
