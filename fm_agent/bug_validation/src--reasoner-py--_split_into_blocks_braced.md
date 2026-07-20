# Bug Report: _split_into_blocks_braced

**Source file:** `src/reasoner-py/_split_into_blocks_braced.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a non-empty list of strings, each being a contiguous, non-overlapping segment of the function body, appearing in the same order as in the original body
  - For brace-delimited languages: every boundary between consecutive returned segments occurs at a line whose brace-nesting depth equals the brace-nesting depth at the first meaningful brace level of the function body. Each segment is therefore syntactically self-contained with respect to brace structure — it begins and ends at the same nesting depth as the function's entry depth
  - For languages that use indentation for syntactic structure (classified as Python-like by the function): segments are split at boundaries that respect indentation-level changes, with each segment being a syntactically contiguous block
  - The ordered concatenation of all returned strings, joined with newline characters, reconstructs the original function body text after stripping leading and trailing whitespace

---

### Actual Behavior

**Natural Language:**
The function `_split_into_blocks_braced` returns a nonempty list of strings, each representing a contiguous block of lines from the input function body. The blocks are constructed so that their ordered concatenation with newline characters exactly reproduces the whole function body after stripping leading and trailing whitespace (i.e., `func.strip()`).

If `language.lower()` belongs to the set `{"python"}`, or if the computed bracedepth entry point is zero after the algorithms fallback, the returned value is the result of calling `_split_into_blocks(func)`, which splits on indentation boundaries (that function preserves the stripped reconstruction property).

Otherwise, the function removes any Line N:  prefixes from the lines, computes the running net brace depth per line (via `_compute_brace_depth_per_line`), determines an entry depth (first positive depth, or 0 if none), and then greedily partitions the original prefixed lines into blocks. The splitting algorithm tries to insert a cut only at a line where the brace depth returns to the entry depth, and only after at least `GRANULARITY` lines have been accumulated. The last block may be shorter when the remaining lines are few (≤ 2×GRANULARITY) or when no line at entry depth exists beyond the target line. In the special case where the total number of lines does not exceed `GRANULARITY`, the function returns a single-element list containing the fully stripped function body.

The function raises no exceptions provided the helper functions `_split_into_blocks` and `_compute_brace_depth_per_line` behave as specified (their preconditions are satisfied by the calling context).

**Formal Logic:**
Let `Func` be the input string `func`, `Lang` the input string `language`, and `GRANULARITY` a fixed positive integer constant. Define:
- `stripped = Func.strip()`, `raw_lines = stripped.split("\n")`, `n = len(raw_lines)`.
- `stripped_lines` obtainable from `raw_lines... (line truncated to 2000 chars)

---

## Code Evidence

```
Line 10:     if total <= GRANULARITY:
Line 11:         return [func.strip()]
Line 34:         if remaining <= GRANULARITY * 2:
Line 35:             blocks.append("\n".join(raw_lines[i:]))
Line 36:             break
Line 44:         if split_point == -1:
Line 45:             blocks.append("\n".join(raw_lines[i:]))
Line 46:             break
Line 47:         blocks.append("\n".join(raw_lines[i:split_point + 1]))
```

---

## Trigger Condition

The specification requires that every returned segment for bracedelimited languages ends at a bracenesting depth equal to the function's entry depth. In the provided counterexample (language='c', func='{\n    int a;\n}'), the function body consists of three lines: '{', '    int a;', '}'. The entry depth is 1 (depth after the opening brace). Regardless of GRANULARITY, the returned list includes a segment that ends with the closing brace line, whose depth is 0, not 1. For instance, when GRANULARITY < 2 the algorithm splits after the second line, leaving the third line as a separate block that ends at depth 0. When GRANULARITY > 2 the entire body is returned as a single block, again ending at depth 0. The code never ensures the final block returns to the entry depth, violating the requirement that each segment be syntactically selfcontained with respect to brace structure.

---

## How to trigger the bug

The bug occurs when `_split_into_blocks_braced` processes a brace-delimited function body. The greedy splitting algorithm at lines 127-130 and 140-142 appends remaining lines without ensuring they return to the entry depth. This means the final block always ends at depth 0 (where the closing brace of the function is), not at the entry depth as required by the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `func` | `'{\n    int a;\n}'` |
| `language` | `'c'` |
| `GRANULARITY` | `1` (overridden from default 40 to force splitting) |

### Expected (spec-correct) Output

All returned segments should end at brace depth equal to the entry depth (1):
```
['{\n    int a;\n}']   — single block ending at depth 1
```
(None of the current code paths produce this correctly for this input.)

### Actual (buggy) Output

```
['{\n    int a;', '}']
```
- Block[0]: `{\n    int a;` ends at depth 1 (correct)
- Block[1]: `}` ends at depth 0, not entry depth 1 (violation)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import config
config.GRANULARITY = 1  # must be set before import
from src.reasoner import _split_into_blocks_braced

result = _split_into_blocks_braced('{\n    int a;\n}', 'c')
# actual (buggy) output: ['{\n    int a;', '}']
# expected (correct) output: ['{\n    int a;\n}']  (single block)
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — Block[1] ends at depth 0 (line index 2), expected entry_depth 1. Block content: '}'
  All blocks: ['{\n    int a;', '}']
  Entry depth: 1
  Expected: all segments end at depth 1
```
