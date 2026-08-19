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
