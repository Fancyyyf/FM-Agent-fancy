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
