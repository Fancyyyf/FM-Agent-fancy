import sys
import os
import json
import tempfile
import shutil
from collections import defaultdict

# ── Attempt 3: directly test _build_call_graph with empty phase_files ─────
# and also test the full _project_call_graph path with various empty scenarios

try:
    from src.generate_topdown_layers import _build_call_graph
    from src.incremental_reasoner import _project_call_graph
except ImportError as e:
    print(f"ERROR: import failed: {e}")
    sys.exit(1)

probe_tmp = tempfile.mkdtemp(prefix="fm_agent_probe_empty3_")
try:
    # ── Test 1: _build_call_graph directly with empty list ─────────────────
    try:
        result = _build_call_graph([], probe_tmp, global_stem_to_fqns=None, extra_call_edges=None)
    except Exception as e:
        print(
            f"CONFIRMED -- _build_call_graph([], ...) raised exception:"
            f" {type(e).__name__}: {e}"
            f" | _project_call_graph passes empty all_files here without guard"
        )
        sys.exit(0)

    # Check the return type
    if not isinstance(result, tuple) or len(result) != 6:
        print(
            f"CONFIRMED -- _build_call_graph([], ...) returned invalid result:"
            f" {type(result).__name__}"
            f" | expected: 6-tuple"
        )
        sys.exit(0)

    callees_map, callers_map, all_callees, file_map, module_map, edge_aliases_map = result

    # All six maps should be dict-like and empty
    map_checks = {
        "callees_map": (callees_map, len(callees_map) if isinstance(callees_map, dict) else -1),
        "callers_map": (callers_map, len(callers_map) if isinstance(callers_map, dict) else -1),
        "file_map": (file_map, len(file_map) if isinstance(file_map, dict) else -1),
        "module_map": (module_map, len(module_map) if isinstance(module_map, dict) else -1),
        "edge_aliases_map": (edge_aliases_map, len(edge_aliases_map) if isinstance(edge_aliases_map, dict) else -1),
    }

    unexpected = []
    for name, (val, length) in map_checks.items():
        if length < 0:
            unexpected.append(f"{name} is {type(val).__name__} not dict")
        elif length > 0:
            unexpected.append(f"{name} has {length} entries (expected 0)")

    if unexpected:
        print(f"CONFIRMED -- _build_call_graph([], ...) behaved unexpectedly: {'; '.join(unexpected)}")
        sys.exit(0)

    # ── Test 2: _project_call_graph with empty phases (already tested, re-confirm) ──
    work_dir = os.path.join(probe_tmp, "fm_agent")
    os.makedirs(os.path.join(work_dir, "extracted_functions"), exist_ok=True)
    os.makedirs(os.path.join(work_dir, "spec_prompts"), exist_ok=True)
    with open(os.path.join(work_dir, "phases.json"), "w") as f:
        json.dump({"phases": []}, f)

    try:
        callees_map, callers_map, file_map, edge_aliases_map = _project_call_graph(
            work_dir, extra_call_edges=None
        )
    except Exception as e:
        print(
            f"CONFIRMED -- _project_call_graph raised exception with empty phases:"
            f" {type(e).__name__}: {e}"
        )
        sys.exit(0)

    maps_ok = (
        isinstance(callees_map, dict) and len(callees_map) == 0
        and isinstance(callers_map, dict) and len(callers_map) == 0
        and isinstance(file_map, dict) and len(file_map) == 0
        and isinstance(edge_aliases_map, dict)
    )

    if maps_ok:
        print(
            "NOT CONFIRMED"
            " -- _build_call_graph([], ...) returns valid empty 6-tuple;"
            " _project_call_graph with empty phases returns valid empty 4-tuple;"
            " the implementation handles empty all_files gracefully without errors."
            " The spec-generated pre-condition for _build_call_graph (non-empty all_files)"
            " does not match the actual implementation which tolerates empty input."
        )
    else:
        print(
            f"CONFIRMED -- _project_call_graph result maps are not valid/empty:"
            f" callees_map type={type(callees_map).__name__} len={len(callees_map) if isinstance(callees_map, dict) else 'N/A'},"
            f" callers_map type={type(callers_map).__name__} len={len(callers_map) if isinstance(callers_map, dict) else 'N/A'},"
            f" file_map type={type(file_map).__name__} len={len(file_map) if isinstance(file_map, dict) else 'N/A'}"
        )

finally:
    shutil.rmtree(probe_tmp, ignore_errors=True)
