"""Probe for bug src--incremental_reasoner-py--_update_specs_for_intent.

Claim: seed set is only populated from relevant_rel_files; changed_targets are
never added.  The probe inspects the source of _update_specs_for_intent to
verify whether seed.update(changed_targets.keys()) is present.
"""
import sys
import inspect

try:
    from src.incremental_reasoner import _update_specs_for_intent

    source = inspect.getsource(_update_specs_for_intent)

    # The spec requires that changed_targets (added/modified) populate the seed.
    # The actual code does this at line 1708 of the source file.
    has_seed_update = "seed.update(changed_targets" in source

    if has_seed_update:
        # changed_targets ARE added to seed — the code matches the spec.
        # Bug NOT confirmed.
        print(
            "NOT CONFIRMED — seed.update(changed_targets.keys()) found in "
            "_update_specs_for_intent; changed_targets are added to the seed "
            "alongside relevant_rel_files."
        )
    else:
        # changed_targets are NOT added — the bug IS real.
        print(
            "CONFIRMED — seed.update(changed_targets.keys()) missing from "
            "_update_specs_for_intent; only relevant_rel_files populate the seed."
        )
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
