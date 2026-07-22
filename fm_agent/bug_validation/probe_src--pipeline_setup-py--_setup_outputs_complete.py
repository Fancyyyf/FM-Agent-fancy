"""Probe script for bug: _setup_outputs_complete validates JSON schema instead of
only checking file existence.

Spec claim: Returns True when phases.json, engine_overview.txt, and at least one
phase_NN_types.txt all exist as regular files under work_dir.

Actual behavior: Returns False when phases.json is not valid JSON/schema-conformant,
even though all three required output categories exist on disk.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.pipeline_setup import _setup_outputs_complete

with tempfile.TemporaryDirectory() as tmpdir:
    # Create engine_overview.txt (exists)
    with open(os.path.join(tmpdir, "engine_overview.txt"), "w") as f:
        f.write("dummy overview")

    # Create phase_01_types.txt (exists)
    with open(os.path.join(tmpdir, "phase_01_types.txt"), "w") as f:
        f.write("dummy types")

    # Create spec_prompts/domain_context/ subdirectory structure for
    # _domain_context_complete to find the files
    domain_dir = os.path.join(tmpdir, "spec_prompts", "domain_context")
    os.makedirs(domain_dir, exist_ok=True)
    with open(os.path.join(domain_dir, "engine_overview.txt"), "w") as f:
        f.write("dummy overview")
    with open(os.path.join(domain_dir, "phase_01_types.txt"), "w") as f:
        f.write("dummy types")

    # Create phases.json that EXISTS but is INVALID JSON
    # This satisfies the spec's existence requirement, but _phase_plan_complete
    # will return False because it checks JSON validity + schema.
    with open(os.path.join(tmpdir, "phases.json"), "w") as f:
        f.write("this is not valid json {{{")

    try:
        actual = _setup_outputs_complete(tmpdir)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Spec says: "Returns True when phases.json, engine_overview.txt, and at least
    # one file matching phase_NN_types.txt all exist as regular files under work_dir."
    # All three exist, so expected = True.
    expected = True

    # The bug is that the code returns False when phases.json is invalid JSON,
    # even though all files exist. So the bug is confirmed if actual != expected.
    passed = actual != expected

    if passed:
        print(f"CONFIRMED -- actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED -- actual matched expected: {actual!r}")
