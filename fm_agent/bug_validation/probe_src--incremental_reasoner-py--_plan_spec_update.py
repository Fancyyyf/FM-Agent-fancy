"""Probe for bug: _plan_spec_update does not extract short callee names from updated_callees.

The specification requires updated_callees to contain "short callee names (the last component
of each callee FQN)". At line 1708, the code uses:

    "updated_callees": result.get("updated_callees") or [],

which passes through whatever the LLM returns without extracting short names via split("::")[-1].

Contrast with line 1649 where callee_names is correctly derived:

    callee_names = sorted({c.split("::")[-1] for c in callees_map.get(fqn, ())})

This probe demonstrates the discrepancy without invoking the full FM-Agent workflow
by testing the exact code pattern found at line 1708 against the specification.
"""

import sys

# ── Reproduce the exact code pattern from line 1708 ──────────────────────────
# This is the buggy line:
#     "updated_callees": result.get("updated_callees") or [],

# Simulate an LLM result that returns FQNs (fully-qualified names) instead
# of short names in updated_callees.  The specification demands short names.
mock_result_with_fqns = {
    "spec_updated": True,
    "new_spec": "# [SPEC]\n# Unit: src/module.py\n# some_func() -> int\n# [SPEC]",
    "updated_callees": [
        "src::network::http::send_request",       # FQN, not short name
        "src::database::pool::_get_connection",   # FQN
        "src::utils::parse_config",               # FQN
        "short_name_only",                        # already a short name
    ],
}

# What line 1708 ACTUALLY does (passes through verbatim — BUGGY):
actual_from_code = mock_result_with_fqns.get("updated_callees") or []

# What line 1649 does for callee_names (extracts short names — CORRECT pattern):
#     callee_names = sorted({c.split("::")[-1] for c in callees_map.get(fqn, ())})
# The equivalent transformation for updated_callees would be:
expected_by_spec = [c.split("::")[-1] for c in actual_from_code]

# ── Classification ──────────────────────────────────────────────────────────
# The spec says updated_callees must contain "short callee names (the last
# component of each callee FQN)".  If the LLM returns FQNs, the code passes
# them through without extracting short names — a clear spec violation.

bug_reproduced = actual_from_code != expected_by_spec

if bug_reproduced:
    print(
        "CONFIRMED — "
        f"actual (raw pass-through, FQNs): {actual_from_code!r} | "
        f"expected (short names per spec): {expected_by_spec!r}"
    )
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual_from_code!r}")
