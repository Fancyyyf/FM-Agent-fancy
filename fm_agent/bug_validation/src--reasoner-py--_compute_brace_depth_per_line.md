# Bug Report: `_compute_brace_depth_per_line`

**Source file:** `/tmp/fm_agent_wt_FM-Agent_jx75d3w8/snapshot/fm_agent/extracted_functions/src/reasoner-py/_compute_brace_depth_per_line.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

(The extracted-function entry above corresponds to `_compute_brace_depth_per_line` in the real source file `src/reasoner.py`; the cited block-comment handling lines 40–48 of the extraction correspond to lines 64–72 of `src/reasoner.py`.)

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of integers with exactly one element per input line, in the same order as the input. The element at index i equals the cumulative brace nesting depth at the end of line i: the number of block-opening brace characters encountered in lines 0 through i minus the number of block-closing brace characters encountered in the same text. Depth is accumulated cumulatively in line order, so values remain consistent for constructs that span multiple lines. A brace character contributes to the depth only when it appears in ordinary code text: braces inside string literals, inside character literals, inside the remainder of a line after the start of a line comment, and inside any portion of a block comment lying within the current line contribute nothing to the depth. Escape sequences within string and character literals do not terminate the literal early, and an unterminated literal or block comment contributes no further depth for the rest of that line. An empty input list yields an empty result list. The function mutates its argument not at all, performs no I/O, raises no exceptions for the stated input, and produces no effects beyond the returned list.

---

### Actual Behavior

The function returns a list `result` such that: (1) len(result) == len(lines); (2) the input list `lines` is not mutated; (3) no exception is raised assuming every element of `lines` is a str; (4) for each index i in range(len(lines)), result[i] equals the cumulative brace depth after sequentially processing lines[0] through lines[i], where the depth starts at 0 and is updated by scanning each line left-to-right character-by-character with the following rules: (a) characters inside a double-quoted string literal (delimited by '"', with backslash-escape sequences skipping the next character) are ignored; (b) characters inside a single-quoted char literal (delimited by "'", with backslash-escape sequences skipping the next character) are ignored; (c) upon encountering '//' outside strings/chars, the remainder of that line is ignored; (d) upon encountering '/*' outside strings/chars, characters are skipped until '*/' is found or the line ends (block comments do NOT span multiple lines in this simplified implementation); (e) each '{' encountered outside all the above contexts increments depth by 1; (f) each '}' encountered outside all the above contexts decrements depth by 1; (5) if lines is empty, result is the empty list []; (6) depth may become negative if closing braces exceed opening braces; (7) unterminated string/char literals or unterminated block comments within a line simply cause the scanner to consume to the end of that line without further brace counting on that line.

---

## Code Evidence

```text
Line 40: if ch == '/' and i + 1 < len(line) and line[i + 1] == '*':
Line 41: i += 2
Line 42: while i < len(line):
Line 43: if line[i] == '*' and i + 1 < len(line) and line[i + 1] == '/':
Line 44: i += 2
Line 45: break
Line 46: i += 1
Line 48: continue
```

---

## Trigger Condition

The specification (Condition B) states that braces 'inside any portion of a block comment lying within the current line contribute nothing to the depth,' which requires tracking multi-line block comments. For input ["/* {", "} */"], the block comment starts on line 0 and ends on line 1. The '}' on line 1 is inside the portion of the block comment lying within that line, so it should not affect depth. The spec requires result [0, 0]. However, the code (Condition A) explicitly does not span block comments across lines: it only skips from '/*' to '*/' or end-of-line within a single line, and starts each new line with no memory of being inside a block comment. Thus on line 1, the code sees '}' as ordinary code and decrements depth, producing [0, -1]. This violates the specification.

---

## How to trigger the bug

`_compute_brace_depth_per_line` is an internal helper; the probe reaches it
through the only public call path that executes it:
`src.reasoner.reasoner()` → `_split_into_blocks_braced()` (`src/reasoner.py`
line 196 → line 108). The block splitter's boundaries are chosen by scanning
the `depths` list for the first index at or beyond the minimum block size
whose depth equals the entry depth, so any depth shift caused by the bug moves
the split boundary.

The fixture embeds the report's trigger shape (a block comment opened on one
line and closed on the next) at depth 1 around the granularity boundary:

- Line `G-2` = `    /* {` — the comment opens and contains `{`. Both the spec
  and the code ignore it within the same line → depth stays 1.
- Line `G-1` = `    } */` — the report's trigger line. Per the spec the `}`
  lies inside the continuation of the block comment and contributes nothing →
  spec depth 1. The code has no cross-line comment state, scans the line as
  ordinary text, and decrements → buggy depth 0.
- Line `G` = `    if (n == 1) {` — spec depth 2, buggy depth 1.
- Line `G+1` = `    }` — spec depth 1, buggy depth 0.

The splitter searches from index `G` (target = block start + GRANULARITY) for
the first line whose depth equals the entry depth (1). With spec-correct
depths the first such line is index `G+1` → first block spans `G+2` lines.
With the buggy depths index `G` already reads 1 → the first block spans only
`G+1` lines. (`G` = GRANULARITY = 40.)

The LLM-dependent helpers (`_generate_block_post_condition`,
`_check_post_implies_spec`) are replaced with local recorders/stubs so the
probe tests only the splitting/depth unit; no FM-Agent workflow, subprocess,
or network call is started.

### Inputs

| Parameter | Value |
|-----------|-------|
| `func` | C-like function body, `3 * GRANULARITY + 4` = 124 lines (with `GRANULARITY` = 40); entry depth 1; block comment opened at line 38 (`/* {`) and closed at line 39 (`} */`), followed by a nested `if` block and brace-free filler |
| `language` | `"c"` |
| `spec` | Minimal spec with parseable `Pre-condition:` / `Post-condition:` sections |
| Entry point | `src.reasoner.reasoner(func, spec, info, language)` with the two LLM helpers mocked |

### Expected (spec-correct) Output

`First block = GRANULARITY + 2 lines → 42 lines (block sizes [42, 41, 41])`

### Actual (buggy) Output

`First block = GRANULARITY + 1 lines → 41 lines (block sizes [41, 83])`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, ".")  # repo root
import os
os.environ.setdefault("LLM_API_KEY", "probe-dummy-key")
import src.reasoner as r
from config import GRANULARITY as G

captured = []
r._generate_block_post_condition = lambda block, pre, info, lang, **kw: (captured.append(block), "ok")[1]
r._check_post_implies_spec = lambda *a, **kw: (True, "", "", "")

lines = ["int probe_func(int n) {"]                        # depth 1 (entry depth)
lines += ["    n = n + %d;" % k for k in range(1, G - 2)]
lines += ["    /* {", "    } */"]                          # trigger: '}' inside continued block comment
lines += ["    if (n == 1) {", "    }"]
while len(lines) < 3 * G + 4:
    lines.append("    n = n + %d;" % len(lines))
func = "\n".join(lines)

spec = "Pre-condition:\n  n is an integer.\nPost-condition:\n  returns consistently."
r.reasoner(func, spec, "fixture", "c")
print(len(captured[0].split("\n")))
# actual (buggy) output: 41 (= GRANULARITY + 1)
# expected (correct) output: 42 (= GRANULARITY + 2)
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
_WORKDIR = tempfile.mkdtemp(prefix="probe_brace_depth_")


def build_fixture(g):
    """C-like function body (total 3*g+4 lines) embedding the report's trigger:
    a block comment opened on line g-2 ("/* {") and closed on line g-1 ("} */").

    Per the spec, the "}" on line g-1 lies inside a block comment, so it must
    not change depth: depths[g-1] stays at the entry depth 1, and later lines
    keep spec-correct depths (depths[g+1] == 1 after the real if-block closes).

    With the bug, block-comment state is dropped at each line end, so the "}"
    on line g-1 is counted as ordinary code: every depth from line g-1 onward
    is shifted down by 1 (depths[g] reads 1), which makes the brace-aware
    splitter in _split_into_blocks_braced cut one line early.
    """
    lines = ["int probe_func(int n) {"]               # idx 0     -> depth 1 (entry depth)
    for k in range(1, g - 2):                         # idx 1..g-3 -> depth 1
        lines.append("    n = n + %d;" % k)
    lines.append("    /* {")                          # idx g-2   -> 1 (comment opens; '{' ignored, same line)
    lines.append("    } */")                          # idx g-1   -> spec: 1 (in comment) | buggy: 0 ('}' counted)
    lines.append("    if (n == 1) {")                 # idx g     -> spec: 2 | buggy: 1
    lines.append("    }")                             # idx g+1   -> spec: 1 | buggy: 0
    while len(lines) < 3 * g + 4:                     # tail filler, brace-free
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
    # recorders so reasoner() runs purely locally. The recorder captures
    # exactly the blocks produced by _split_into_blocks_braced, whose split
    # boundaries are driven by _compute_brace_depth_per_line — the unit
    # under test. No OpenCode/subprocess/network activity is started.
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

    # Public entry point of the src package's reasoning module; the only
    # public call path reaching _compute_brace_depth_per_line
    # (src/reasoner.py: reasoner -> _split_into_blocks_braced -> depth scan).
    outcome = reasoner_mod.reasoner(func_text, spec, "probe fixture", "c")

    if not captured_blocks:
        print("ERROR: reasoner() produced no blocks; outcome: %r" % outcome)
        sys.exit(1)

    actual_sizes = [len(b.split("\n")) for b in captured_blocks]
    actual_first = actual_sizes[0]

    # Spec-correct depths for lines g-2..g+1 are [1, 1, 2, 1]: the earliest
    # line at or beyond the minimum size (index g) whose depth equals the
    # entry depth (1) is index g+1, so the first block must span g+2 lines.
    # Buggy depths are [1, 0, 1, 0]: index g already reads depth 1, so the
    # splitter cuts one line early and the first block spans g+1 lines.
    expected_first = g + 2

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
CONFIRMED — actual first-block lines: 41 | expected: 42 | block sizes: [41, 83] | partition_ok: True
```
