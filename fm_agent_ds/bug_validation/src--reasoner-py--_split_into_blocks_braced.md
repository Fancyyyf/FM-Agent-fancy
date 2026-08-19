# Bug Report: _split_into_blocks_braced

**Source file:** `src/reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns an ordered list of block strings, each a contiguous segment of func. The concatenation of all blocks in returned order reconstructs the original function body. No block contains an unclosed brace grouping — every opening brace inside a block has its matching closing brace also inside that same block. When the function body contains no detectable brace pairs, this constraint is vacuously satisfied and blocks are split by line count. Every block except possibly the last contains at least GRANULARITY lines. When the total line count of func does not exceed GRANULARITY, the result is a single-element list containing the function body. When fewer than 2*GRANULARITY lines remain at the end, the remaining lines form the final block.

---

### Actual Behavior

If `language.lower()` is `'python'`, the function returns the result of `_split_into_blocks(func)`. This result is an ordered list `blocks` of nonempty strings such that `"\n".join(blocks) == func.strip()`. For every block except the last, the block contains exactly `GRANULARITY` lines. The last block contains the remaining lines when fewer than `2*GRANULARITY` lines remain in the input.

Otherwise (nonPython language): let `raw_lines = func.strip().split("\n")` and `N = len(raw_lines)`. If `N <= GRANULARITY`, the function returns a list containing the single element `func.strip()`. Else a normalized version `stripped` of `raw_lines` is built by removing `"Line X:"` prefixes from each line, and `depths` is computed via `_compute_brace_depth_per_line(stripped)`, which yields an integer list of length `N`. Let `entry_depth` be `depths[0]` if `depths[0] != 0`, otherwise the first strictly positive value in `depths`, or 0 if none exists. If `entry_depth == 0`, the function falls back to `_split_into_blocks(func)` as above.

When `entry_depth > 0`, the function partitions `raw_lines` into contiguous segments forming the returned `blocks` list:
- Initialize `blocks = []`, `i = 0`.
- While `i < N`:
   * If `N - i <= 2 * GRANULARITY`, append `"\n".join(raw_lines[i:])` to `blocks` and exit the loop.
   * Otherwise, find the smallest `j` in `[i + GRANULARITY, N-1]` for which `depths[j] == entry_depth`. If such `j` exists, append `"\n".join(raw_lines[i:j+1])` and set `i = j + 1`. If no such `j` exists, append `"\n".join(raw_lines[i:])` and exit the loop.

Consequently, every nonfinal block ends at a line whose cumulative brace depth returns to `entry_depth`, ensuring splits only at syntactic boundaries; the split point is at least `GRANULARITY` lines after the start of the block. The concatenation of all returned blocks with `"\n"` reconstructs exactly `func.strip()`. All returned blocks are nonempty strings.

Formally: the code splits when cumulative brace depth equals entry_depth, but never verifies that the block's starting depth also equals entry_depth. When the first line of a block contains an opening brace (e.g., the opening `{` of a C function body), the block starts at depth > entry_depth, and the split at the next occurrence of entry_depth occurs before the matching `}`, leaving an unclosed brace grouping inside that block.

---

## Code Evidence

Line 23: entry_depth = depths[0] if total > 0 else 0
Line 24: if entry_depth == 0:
Line 25:     entry_depth = next((d for d in depths if d > 0), 0)
Line 41: if depths[j] == entry_depth:

---

## Trigger Condition

The specification requires that no block contains an unclosed brace grouping, i.e., every opening brace inside a block must have its matching closing brace also inside that block. The code splits the function body into blocks when the cumulative brace depth equals entry_depth, but does not ensure that the starting depth of the block equals entry_depth. Consequently, a block may begin with an opening brace (e.g., the opening brace of the function body) without containing its matching closing brace, violating the specification. For the given counterexample with GRANULARITY=2, the code produces a block containing `{` and two statements but not the closing `}`, leaving the opening brace unclosed within the block.

---

## How to trigger the bug

When a C-like function body begins with an opening brace `{` as its first line (common in C/Java/Go/Rust/etc.), and GRANULARITY is small enough that the function body is split into multiple blocks, the first block will contain the opening `{` but not its matching `}`. The matching `}` ends up in a later block.

### Inputs

| Parameter | Value |
|---|---|
| `func` | `"{\n    int x = 1;\n    int y = 2;\n    int z = 3;\n    int w = 4;\n    int v = 5;\n    return x + y;\n}"` |
| `language` | `"c"` |
| `GRANULARITY` | `2` |

### Expected (spec-correct) Output

Each block must contain no unclosed brace groupings. Blocks should be formed such that every `{` inside a block has its matching `}` inside the same block.

### Actual (buggy) Output

Three blocks are returned:
- **Block 0**: `{\n    int x = 1;\n    int y = 2;` — contains opening `{` without matching `}` (net depth +1)
- **Block 1**: `    int z = 3;\n    int w = 4;\n    int v = 5;` — balanced (no braces)
- **Block 2**: `    return x + y;\n}` — contains closing `}` without matching `{` (net depth -1)

The concatenation `"\n".join(blocks)` correctly reconstructs `func.strip()`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.reasoner import _split_into_blocks_braced
import src.reasoner as reasoner
reasoner.GRANULARITY = 2

func_body = """{
    int x = 1;
    int y = 2;
    int z = 3;
    int w = 4;
    int v = 5;
    return x + y;
}"""

blocks = _split_into_blocks_braced(func_body, "c")
# Block 0 contains '{' without matching '}' — net brace depth = 1
# actual (buggy) output: 3 blocks, first block unbalanced
# expected (correct) output: all blocks brace-balanced
```

---

## Probe Script

```python
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
```

### Probe Output

```
Concatenation check: PASS
Block 0 has unbalanced braces (net depth=1):
  line 0: '{'
  line 1: '    int x = 1;'
  line 2: '    int y = 2;'
Block 1: balanced, 3 lines
Block 2 has unbalanced braces (net depth=-1):
  line 0: '    return x + y;'
  line 1: '}'
CONFIRMED — blocks contain unclosed brace groupings
```
