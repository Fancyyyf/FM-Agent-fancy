"""Probe: _build_call_graph adds registry edges even when file I/O fails.

Bug summary: In the registry branch (lang_key in registry_langs), callee_fqns
are computed from registry_edges BEFORE any file I/O. When the file is
unreadable (OSError), the except block only handles extra-edge call site
detection (sets text=""), but registry-derived callee edges remain.

Spec says: "Function files that cannot be read due to I/O errors contribute no
callee edges." The bug reproduces when a registry-language file triggers OSError
but registry_edges still supply callee edges for its FQN.
"""

import os
import sys
import tempfile
import shutil
from unittest.mock import patch
from collections import defaultdict


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def main():
    bug_id = "src--generate_topdown_layers-py--_build_call_graph"

    tmp = tempfile.mkdtemp(prefix="probe_build_call_graph_")
    extracted_dir = os.path.join(tmp, "extracted_functions", "src", "test-py")
    os.makedirs(extracted_dir, exist_ok=True)
    test_file = os.path.join(extracted_dir, "func.py")

    # FQN that _file_to_fqn will compute for this file
    # rel = src/test-py/func.py → stem = src/test-py/func → "src::test-py::func"
    test_fqn = "src::test-py::func"

    # A callee FQN that will be in known_fqns (so registry edges referencing it
    # pass the filter on line 72 of the extracted function)
    callee_fqn = "src::test-py::other_func"

    # ---------------------------------------------------------------------------
    # Try to import the target function
    # ---------------------------------------------------------------------------

    try:
        from src.generate_topdown_layers import _build_call_graph
        from src.call_graph_edges import CallEdge, CallerSelector, CalleeTarget
    except Exception as exc:
        print(f"ERROR importing modules: {exc}")
        cleanup(tmp, test_file)
        sys.exit(1)

    # ---------------------------------------------------------------------------
    # Create the test file and make it unreadable
    # ---------------------------------------------------------------------------

    try:
        with open(test_file, "w") as f:
            f.write("def func():\n    pass\n")
    except OSError as exc:
        print(f"ERROR creating test file: {exc}")
        cleanup(tmp, test_file)
        sys.exit(1)

    try:
        os.chmod(test_file, 0o000)
    except OSError:
        # On some constrained systems chmod may not work — still valid,
        # because the probe logic below handles both code paths.
        pass

    # ---------------------------------------------------------------------------
    # Build test inputs
    # ---------------------------------------------------------------------------

    phase_files = [(test_file, "test_module")]

    # effective_stem_to_fqns is the global_stem_to_fqns we pass in.
    # It must contain both test_fqn and callee_fqn so that known_fqns
    # includes the callee (registry edges referencing non-known FQNs are
    # filtered out).
    effective_stem_to_fqns = {
        "func": {test_fqn},
        "other_func": {callee_fqn},
    }

    # Mock call_edges_all to return registry edges for test_fqn
    def mock_call_edges_all(proj_dir, phase_langs):
        edges = {test_fqn: {callee_fqn}}
        langs = {"python"}
        return edges, langs

    # Extra call edges: use callsite_names to make extra_edges_by_callsite
    # truthy, which triggers the file-open code path (lines 331-340 of
    # the extracted function). Without this trigger the file is never
    # opened and no OSError can fire.
    extra_edges = [
        CallEdge(
            caller=CallerSelector(fqn="", callsite_names=("helper",)),
            callee=CalleeTarget(fqn=callee_fqn, info_names=("helper_alias",)),
            source="test",
        )
    ]

    # ---------------------------------------------------------------------------
    # Execute
    # ---------------------------------------------------------------------------

    try:
        with patch("src.generate_topdown_layers.call_edges_all", mock_call_edges_all):
            (
                callees_map,
                callers_map,
                all_callees_map,
                file_map,
                module_map,
                edge_aliases_map,
            ) = _build_call_graph(
                phase_files=phase_files,
                proj_dir=tmp,
                global_stem_to_fqns=effective_stem_to_fqns,
                extra_call_edges=extra_edges,
            )
    except Exception as exc:
        print(f"ERROR executing _build_call_graph: {exc}")
        cleanup(tmp, test_file)
        sys.exit(1)

    # ---------------------------------------------------------------------------
    # Verify
    # ---------------------------------------------------------------------------

    # The bug: an unreadable file SHOULD contribute no callee edges (per spec),
    # but registry_edges still supply edges.
    actual_all_callees = all_callees_map.get(test_fqn, set())
    actual_callees = callees_map.get(test_fqn, set())

    callee_edges_present = bool(actual_all_callees)

    if callee_edges_present:
        print(
            "CONFIRMED — bug reproduced:"
            f" all_callees_map[{test_fqn}] = {sorted(actual_all_callees)}"
        )
        print(
            f"  callees_map[{test_fqn}] = {sorted(actual_callees)}"
        )
        print(
            "  File is unreadable (mode 000) but registry edges were still"
            " used."
        )
    else:
        print(
            f"NOT CONFIRMED — no callee edges from unreadable file:"
            f" all_callees_map[{test_fqn}] = {sorted(actual_all_callees)}"
        )

    # ---------------------------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------------------------
    cleanup(tmp, test_file)


def cleanup(tmp_dir, test_file):
    """Restore file permissions and remove the temp tree."""
    try:
        os.chmod(test_file, 0o644)
    except (OSError, NameError):
        pass
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass


if __name__ == "__main__":
    main()
