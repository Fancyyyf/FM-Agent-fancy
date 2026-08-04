import sys

try:
    from src.reasoner import _split_into_blocks_braced
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# The bug manifests when GRANULARITY is small enough that blocks split
# inside a brace-delimited function body. Use GRANULARITY=2 to make the
# split aggressive so the opening "{" and closing "}" end up in different
# blocks.
import src.reasoner as reasoner
reasoner.GRANULARITY = 2

# Function body of a C-like function. The opening brace is on the first
# line so depths[0] == 1 (entry_depth = 1). With GRANULARITY=2 and N=8
# lines, the first block captures lines [0:3] — "{", "int x=1", "int y=2" —
# which contains an opening brace but no matching closing brace.
func_body = """{
    int x = 1;
    int y = 2;
    int z = 3;
    int w = 4;
    int v = 5;
    return x + y;
}"""

language = "c"

blocks = _split_into_blocks_braced(func_body, language)

# Verify: concatenation reconstructs func.strip()
reconstructed = "\n".join(blocks)
concat_ok = reconstructed == func_body.strip()
print(f'Concatenation check: {"PASS" if concat_ok else "FAIL"}')

# Check each block for unclosed brace groupings
confirmed = False
for i, block in enumerate(blocks):
    depth = 0
    for ch in block:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
    if depth != 0:
        confirmed = True
        print(f'Block {i} has unbalanced braces (net depth={depth}):')
        lines = block.split('\n')
        for li, l in enumerate(lines):
            print(f'  line {li}: {repr(l)}')
    else:
        print(f'Block {i}: balanced, {len(block.split(chr(10)))} lines')

if confirmed:
    print('CONFIRMED — blocks contain unclosed brace groupings')
else:
    print('NOT CONFIRMED — all blocks have balanced braces')
