import sys
import os

# Ensure the project root is on sys.path so `config` and `src` resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../..')

# Override GRANULARITY to a small value so splitting occurs
import config
config.GRANULARITY = 1

try:
    from src.reasoner import _split_into_blocks_braced
    from src.reasoner import _compute_brace_depth_per_line

    # Trigger condition from the bug report:
    #   language='c', func='{\n    int a;\n}'
    #   - entry_depth is 1 (depth after line 0: '{')
    #   - when GRANULARITY=1, the last block '}' ends at depth 0 != entry_depth → VIOLATION
    func = '{\n    int a;\n}'
    language = 'c'

    result = _split_into_blocks_braced(func, language)

    # Compute entry depth to check against
    stripped = func.strip()
    raw_lines = stripped.split('\n')
    # Strip "Line N: " prefix from lines (as the function does internally)
    stripped_lines = []
    for line in raw_lines:
        if line.startswith("Line "):
            colon = line.find(":", 5)
            if colon != -1:
                line = line[colon + 1:].lstrip()
        stripped_lines.append(line)
    depths = _compute_brace_depth_per_line(stripped_lines)
    entry_depth = depths[0] if depths else 0
    if entry_depth == 0:
        entry_depth = next((d for d in depths if d > 0), 0)

    # Spec claim: every segment begins and ends at the same nesting depth as entry_depth.
    # Track the cumulative line position within the full function body.
    blocked_lines = []
    for block in result:
        blocked_lines.extend(block.strip().split('\n'))

    # Recompute depths on the concatenated blocked lines (same as full function body).
    # Then check block boundary positions.
    blocked_depths = _compute_brace_depth_per_line(blocked_lines)

    violated = False
    violation_detail = ""
    cursor = 0
    for idx, block in enumerate(result):
        block_line_count = len(block.strip().split('\n'))
        block_end_idx = cursor + block_line_count - 1
        block_end_depth = blocked_depths[block_end_idx]
        if block_end_idx < len(blocked_depths) and block_end_depth != entry_depth:
            violated = True
            violation_detail = (
                f"Block[{idx}] ends at depth {block_end_depth} "
                f"(line index {block_end_idx}), "
                f"expected entry_depth {entry_depth}. "
                f"Block content: {block!r}"
            )
            break
        cursor += block_line_count

    expected = f"all segments end at depth {entry_depth}"
    if violated:
        print(f'CONFIRMED — {violation_detail}')
        print(f'  All blocks: {result!r}')
        print(f'  Entry depth: {entry_depth}')
        print(f'  Expected: {expected}')
    else:
        print(f'NOT CONFIRMED — all blocks end at entry_depth {entry_depth}. Blocks: {result!r}')

except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)
