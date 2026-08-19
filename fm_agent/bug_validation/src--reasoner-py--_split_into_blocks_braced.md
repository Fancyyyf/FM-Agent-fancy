# Bug Report: `_split_into_blocks_braced`

**Source file:** `/tmp/fm_agent_wt_FM-Agent_jx75d3w8/snapshot/fm_agent/extracted_functions/src/reasoner-py/_split_into_blocks_braced.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

(The extracted-function entry above corresponds to `_split_into_blocks_braced` in the real source file `src/reasoner.py`; the cited line `target = i + GRANULARITY` is line 131 of `src/reasoner.py`.)

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a non-empty list of block strings that exactly partitions the whitespace-stripped text of func: joining the blocks in order with single-newline separators reproduces that stripped text, every line of func appears in exactly one block with its 'Line N: ' prefix preserved unchanged, and block order matches line order. If the stripped text has at most the granularity number of lines, exactly one block is returned containing the entire stripped text. Otherwise the governing size rule holds: every non-final block has at least the configured granularity of lines, and whenever the number of not-yet-emitted lines falls to at most twice the granularity, all remaining lines are absorbed into the final block, so no trailing fragment of at most twice the granularity is ever emitted as its own block. For languages whose syntax delimits blocks with paired braces, a split boundary may occur only after a line at which the brace nesting depth has returned to the function body's entry depth (the nesting depth at which the function's outermost statements sit), so no block ends inside a nested braced construct, and each boundary is the earliest such line at or beyond the current block's minimum size; if no such line exists through the end of the text, all remaining lines form the final block. For indentation-based languages (Python), and for braced-language text in which no positive nesting depth can be detected, boundaries are determined by line count alone under the same partition and size guarantees. The function never modifies func, writes no files, and produces no effects beyond the returned list.

---

### Actual Behavior

The function returns a non-empty list of strings (blocks). All execution paths guarantee the following universal properties: (1) joining the returned blocks in order with '\n' reproduces func.strip() exactly; (2) every line of func.strip() appears in exactly one block, in the original order, with its 'Line N: ' prefix preserved unchanged; (3) func is never mutated.

Path-specific behavior:

 If language.lower() == 'python': the result is identical to _split_into_blocks(func), i.e., a purely line-count-based partition where every non-final block has exactly GRANULARITY lines and the final block holds the remainder (at most GRANULARITY lines), or a single block if total lines  GRANULARITY.

 If language is not Python-like and the total number of lines in func.strip() (call it total) satisfies total  GRANULARITY: returns the single-element list [func.strip()].

 If language is not Python-like, total > GRANULARITY, and the computed entry_depth is 0 (meaning no line in the prefix-stripped content ever reaches a positive brace depth): falls back to _split_into_blocks(func), yielding the same line-count-only partition described above.

 Otherwise (non-Python-like, total > GRANULARITY, entry_depth > 0): the function performs brace-aware greedy splitting. Formally, let raw_lines = func.strip().split('\n'), let stripped_lines be raw_lines with any 'Line N: ' prefix removed, and let depths = _compute_brace_depth_per_line(stripped_lines). Then:
  (a) Every boundary between consecutive blocks occurs at an index j (0-based into raw_lines) such that depths[j] == entry_depth, meaning the cumulative brace nesting depth of the prefix-stripped content at the end of that line equals the entry depth.
  (b) Every non-final block spans at least GRANULARITY + 1 lines (since the search for a split point begins at offset i + GRANULARITY from the block start).
  (c) If at any iteration the number of remaining unassigned lines is  GRANULARITY  2, all remaining lines are placed into the final block and the loop terminates.
  (d) If no index j  i + GRANULARITY satisfies depths[j] == entry_depth, all remaining lines from i onward form the final block and the loop terminates.
  (e) The final block therefore contains at most GRANULARITY  2 lines when condition (c) triggers, or an unbounded remainder when condition (d) triggers (no valid split point exists).
  (f) entry_depth is defined as depths[0] if depths[0] > 0, otherwise the first strictly positive value in depths, ensuring it reflects the nesting level at which top-level statements of the function body reside.

In all paths, no exception is raised assuming the pre-conditions hold and the helper functions (_split_into_blocks, _compute_brace_depth_per_line) behave per their contracts. GRANULARITY is the module-level configured block granularity (a positive integer).

---

## Code Evidence

Line 37:         target = i + GRANULARITY

---

## Trigger Condition

The spec states 'each boundary is the earliest such line at or beyond the current block's minimum size' where the minimum size is GRANULARITY lines. A block starting at index i with exactly GRANULARITY lines ends at index i+GRANULARITY-1, so the search for a valid split point (depth==entry_depth) should begin at index i+GRANULARITY-1. The code uses target=i+GRANULARITY, which is one position too late, causing it to skip a valid split point at i+GRANULARITY-1 and produce a non-earliest boundary. This results in non-final blocks having GRANULARITY+1 lines minimum instead of the spec-permitted GRANULARITY lines minimum, violating the 'earliest such line' requirement.

---

## How to trigger the bug

The spec requires that each brace-aware split boundary is "the earliest [line
at entry depth] at or beyond the current block's minimum size", where the
minimum size is `GRANULARITY` lines. For a block starting at index `i`, a
block of exactly `GRANULARITY` lines ends at index `i + GRANULARITY - 1`, so
the search for a split point must begin at `i + GRANULARITY - 1`. The code
starts it at `i + GRANULARITY` (line 131 of `src/reasoner.py`), one position
late.

The probe feeds a C-like function body of `2 * GRANULARITY + 5` lines through
the package's public reasoning entry point `src.reasoner.reasoner()` (the only
public call path that reaches `_split_into_blocks_braced`). The fixture's brace
nesting depth returns to the function-body entry depth (1) at exactly index
`GRANULARITY - 1` — the earliest valid boundary permitted by the spec — and
then returns to entry depth again at index `GRANULARITY + 1`. The buggy search
skips the valid boundary at `GRANULARITY - 1` and splits at `GRANULARITY + 1`
instead, making the first non-final block 2 lines larger than the spec allows.

The LLM-dependent helpers (`_generate_block_post_condition`,
`_check_post_implies_spec`) are replaced with local recorders/stubs so the
probe tests only the splitting unit; no FM-Agent workflow, subprocess, or
network call is started.

### Inputs

| Parameter | Value |
|-----------|-------|
| `func` | C-like function body, `2 * GRANULARITY + 5` = 85 lines (with `GRANULARITY` = 40); entry depth 1; depth returns to entry depth exactly at index 39 (`GRANULARITY - 1`), then again at index 41 (`GRANULARITY + 1`) |
| `language` | `"c"` |
| `spec` | Minimal spec with parseable `Pre-condition:` / `Post-condition:` sections |
| Entry point | `src.reasoner.reasoner(func, spec, info, language)` with the two LLM helpers mocked |

### Expected (spec-correct) Output

`First block = exactly GRANULARITY lines → block sizes [40, 45]`

### Actual (buggy) Output

`First block = GRANULARITY + 2 lines → block sizes [42, 43]`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, ".")  # repo root
import src.reasoner as r

captured = []
r._generate_block_post_condition = lambda block, pre, info, lang, **kw: (captured.append(block), "ok")[1]
r._check_post_implies_spec = lambda *a, **kw: (True, "", "", "")

from config import GRANULARITY as G
lines = ["int probe_func(int n) {"]                      # depth 1 (entry depth)
lines += ["    int v%d = %d;" % (k, k) for k in range(1, G - 2)]
lines += ["    if (n == 1) {", "    }"]                  # depth back to 1 at index G-1
lines += ["    if (n == 2) {", "    }"]                  # depth back to 1 at index G+1
while len(lines) < 2 * G + 5:
    lines.append("    n = n + %d;" % len(lines))
func = "\n".join(lines)

spec = "Pre-condition:\n  n is an integer.\nPost-condition:\n  returns consistently."
r.reasoner(func, spec, "fixture", "c")
print(len(captured[0].split("\n")))
# actual (buggy) output: 42 (= GRANULARITY + 2)
# expected (correct) output: 40 (= GRANULARITY)
```

---

## Probe Script

```py
import os
import sys
import tempfile

# Do not litter the repo with bytecode caches while importing project modules.
sys.dont_write_bytecode = True

# Ensure OpenAI client construction inside src.llm_client never fails or phones
# home: dummy key, no requests are ever issued (LLM functions are mocked below).
os.environ.setdefault("LLM_API_KEY", "probe-dummy-key")

# Make the repository root importable (probe lives in fm_agent/bug_validation/).
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Probe-owned workspace: all fixture/runtime file I/O stays inside this fresh
# temporary directory (never in the repo or its fm_agent/ directory).
_WORKDIR = tempfile.mkdtemp(prefix="probe_split_braced_")


def build_fixture(g):
    """C-like function body (total 2*g+5 lines) whose brace depth returns to
    the entry depth (1) exactly at index g-1 — the earliest valid boundary at or
    beyond the minimum block size of g lines per the spec — then nests again at
    index g and returns to entry depth at index g+1.
    """
    lines = ["int probe_func(int n) {"]                     # idx 0     -> depth 1
    for k in range(1, g - 2):                               # idx 1..g-3 -> depth 1
        lines.append("    int v%d = %d;" % (k, k))
    lines.append("    if (n == 1) {")                       # idx g-2   -> depth 2
    lines.append("    }")                                   # idx g-1   -> depth 1 (spec's earliest boundary)
    lines.append("    if (n == 2) {")                       # idx g     -> depth 2
    lines.append("    }")                                   # idx g+1   -> depth 1 (buggy boundary)
    while len(lines) < 2 * g + 5:                           # pad tail, depth 1
        lines.append("    n = n + %d;" % len(lines))
    return "\n".join(lines)


try:
    import src.reasoner as reasoner_mod
    import config

    g = config.GRANULARITY

    # Fixture round-trips through the probe's own temp dir only.
    fixture_path = os.path.join(_WORKDIR, "fixture.c")
    with open(fixture_path, "w", encoding="utf-8") as f:
        f.write(build_fixture(g))
    with open(fixture_path, "r", encoding="utf-8") as f:
        func_text = f.read()

    # --- FM-Agent self-validation guard: never start an FM-Agent workflow.
    # Replace the LLM-dependent helpers inside src.reasoner's namespace with
    # recorders so reasoner() runs purely locally. The recorder for the block
    # post-condition generator captures exactly the blocks produced by
    # _split_into_blocks_braced, which is the unit under test.
    captured_blocks = []

    def fake_generate_block_post_condition(block, pre_condition, info, language,
                                           trace_dir=None, trace_meta=None):
        captured_blocks.append(block)
        return "Post-condition: state is consistent."

    def fake_check_post_implies_spec(block, post_condition, spec_post_condition,
                                     info, language, trace_dir=None, trace_meta=None):
        return (True, "", "", "")

    reasoner_mod._generate_block_post_condition = fake_generate_block_post_condition
    reasoner_mod._check_post_implies_spec = fake_check_post_implies_spec

    spec = (
        "Pre-condition:\n"
        "  n is an integer.\n"
        "Post-condition:\n"
        "  returns with state consistent."
    )

    # Public entry point of the src package's reasoning module; the only public
    # call path that reaches _split_into_blocks_braced (src/reasoner.py line 196).
    outcome = reasoner_mod.reasoner(func_text, spec, "probe fixture", "c")

    if not captured_blocks:
        print("ERROR: reasoner() produced no blocks; outcome: %r" % outcome)
        sys.exit(1)

    actual_sizes = [len(b.split("\n")) for b in captured_blocks]
    actual_first = actual_sizes[0]

    # Spec: "each boundary is the earliest such line at or beyond the current
    # block's minimum size" (minimum size = GRANULARITY lines). depths[g-1] ==
    # entry depth, so the first block must contain exactly g lines.
    expected_first = g

    # Sanity: partition integrity must hold regardless of the bug.
    partition_ok = "\n".join(captured_blocks) == func_text.strip()

    passed = actual_first != expected_first  # True -> bug reproduced
except Exception as e:
    print("ERROR: %s" % e)
    sys.exit(1)

if passed:
    print("CONFIRMED — actual first-block lines: %d | expected: %d | block sizes: %s | partition_ok: %s"
          % (actual_first, expected_first, actual_sizes, partition_ok))
else:
    print("NOT CONFIRMED — actual matched expected: %d | block sizes: %s"
          % (actual_first, actual_sizes))
```

### Probe Output

```
CONFIRMED — actual first-block lines: 42 | expected: 40 | block sizes: [42, 43] | partition_ok: True
```
