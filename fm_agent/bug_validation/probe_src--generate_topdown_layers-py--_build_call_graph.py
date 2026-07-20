"""Probe script: verify _build_call_graph adds codegraph callee edges even when
the source file cannot be opened for reading.

Spec claim: If a source file cannot be opened for reading, no callee edges are
            added for that file and it is silently skipped.
Bug: In the codegraph path (lang_key in registry_langs), callee_fqns is computed
     from registry_edges *before* any file-open attempt. When the file is
     unreadable and no extra edges are configured, the file-open block is
     skipped entirely, yet codegraph-derived edges are still added to
     callees_map and all_callees_map — violating the spec.
"""

import sys
import os
import tempfile
from unittest.mock import patch

# Add repo root to sys.path so the 'src' package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.generate_topdown_layers import _build_call_graph, _file_to_fqn

    with tempfile.TemporaryDirectory() as proj_dir:
        # Set up the extracted_functions directory structure
        extracted_dir = os.path.join(proj_dir, "extracted_functions", "src", "test-c")
        os.makedirs(extracted_dir)

        # Create two function files:
        #  - caller_func.c: the caller (will be made unreadable)
        #  - callee_func.c: the callee (stays readable for FQN mapping)
        caller_path = os.path.join(extracted_dir, "caller_func.c")
        callee_path = os.path.join(extracted_dir, "callee_func.c")

        for path in (caller_path, callee_path):
            with open(path, "w") as f:
                f.write("// test file\n")

        # Compute FQNs (pure path computation, does not read file contents)
        caller_fqn = _file_to_fqn(caller_path, proj_dir)
        callee_fqn = _file_to_fqn(callee_path, proj_dir)

        # phase_files: both files belong to the same module
        phase_files = [
            (caller_path, "test_module"),
            (callee_path, "callee_module"),
        ]

        # Make the caller file unreadable to trigger the spec condition
        os.chmod(caller_path, 0o000)

        # Mock call_edges_all: returns a codegraph edge caller_fqn -> callee_fqn
        # and registers "c" as a codegraph-handled language. This simulates the
        # scenario where codegraph has resolved the edge and the caller's source
        # file happens to be unreadable at the time _build_call_graph runs.
        mock_edges = {caller_fqn: {callee_fqn}}
        mock_langs = {"c"}

        try:
            with patch(
                "src.generate_topdown_layers.call_edges_all",
                return_value=(mock_edges, mock_langs),
            ):
                (
                    callees_map,
                    callers_map,
                    all_callees_map,
                    file_map,
                    module_map,
                    edge_aliases_map,
                ) = _build_call_graph(phase_files, proj_dir)
        finally:
            # Restore permissions so TemporaryDirectory can clean up
            os.chmod(caller_path, 0o644)

        # Check: did the unreadable caller get callee edges?
        has_callee_edges = callee_fqn in callees_map.get(caller_fqn, set())
        has_all_callee_edges = callee_fqn in all_callees_map.get(caller_fqn, set())
        bug_reproduced = has_callee_edges and has_all_callee_edges

        if bug_reproduced:
            print("CONFIRMED")
            print(f"  caller_fqn:           {caller_fqn}")
            print(f"  callee_fqn:           {callee_fqn}")
            print(f"  callees_map[caller]:  {sorted(callees_map.get(caller_fqn, set()))}")
            print(f"  all_callees_map[caller]: {sorted(all_callees_map.get(caller_fqn, set()))}")
            print(f"  spec requires: no callee edges when file cannot be opened for reading")
            print(f"  bug: codegraph-derived edges added despite unreadable source file")
        else:
            print("NOT CONFIRMED")
            print(f"  callees_map[caller]:   {sorted(callees_map.get(caller_fqn, set()))}")
            print(f"  all_callees_map[caller]: {sorted(all_callees_map.get(caller_fqn, set()))}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
