"""Probe for bug src--reasoner-py--_split_into_blocks_braced.

Bug: _split_into_blocks_braced computes entry_depth as first positive depth when
depths[0]==0, but the first block starts at line 0 (depth 0) instead of at a line
with depth==entry_depth. This violates the spec that each segment begins and ends
at the same nesting depth as the function's entry depth.

Repro: C function body with opening brace on the second line.
"""
import importlib
import sys
import os

# All file I/O in a fresh temp directory (self-validation guard)
TMP = os.environ.get("FM_AGENT_TMP", "/tmp/opencode")
os.makedirs(TMP, exist_ok=True)
os.chdir(TMP)

try:
    # Load _split_into_blocks_braced via the package's internal module.
    # Per the FM-Agent self-validation guard, testing the smallest relevant
    # pure-computation unit is allowed — this does not start an FM-Agent workflow.
    import src.reasoner as reasoner

    # Monkey-patch GRANULARITY to 1 so a small function body triggers the split logic
    reasoner.GRANULARITY = 1

    # C function body: opening brace on the second line
    # depths: line0=0, line1=1, line2=1, line3=0
    func = "int main()\n{\n    return 0;\n}"
    language = "c"

    # Compute depths for verification
    stripped = func.strip().split("\n")
    depths = reasoner._compute_brace_depth_per_line(stripped)

    # entry_depth per the code: depths[0]=0 → next positive = 1
    entry_depth = depths[0] if depths[0] > 0 else next((d for d in depths if d > 0), 0)

    # Run the buggy function
    blocks = reasoner._split_into_blocks_braced(func, language)

    # Verify: per spec, the first block should begin at entry_depth.
    # The buggy code produces a first block that includes line 0 (depth 0),
    # which is below entry_depth. Check that the first block starts at a depth
    # that is NOT equal to entry_depth.
    first_block_lines = blocks[0].split("\n")
    first_line_depth = depths[0]  # depth of the first line in the first block

    # The spec requires: each segment begins at entry_depth.
    # Bug reproduced if first block begins at depth != entry_depth.
    starts_at_entry = (first_line_depth == entry_depth)

    mid_line_depths = [depths[i] for i in range(len(first_block_lines))]
    ends_at_entry = (mid_line_depths[-1] == entry_depth)

    bug_reproduced = (not starts_at_entry) and ends_at_entry and len(blocks) >= 2

    if bug_reproduced:
        print(
            f"CONFIRMED — first block starts at depth {first_line_depth}, "
            f"not entry_depth {entry_depth}. "
            f"Block: {blocks[0]!r} "
            f"| all_blocks: {blocks} "
            f"| depths: {depths}"
        )
    else:
        print(
            f"NOT CONFIRMED — first block starts at depth {first_line_depth}, "
            f"entry_depth={entry_depth}. "
            f"blocks: {blocks} "
            f"| depths: {depths}"
        )

    # Restore GRANULARITY
    importlib.reload(reasoner)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
