import sys
import os

# Probe workspace: create a temp dir for any fixtures/runtime state.
import tempfile
_PROBE_TMP = tempfile.mkdtemp(prefix="probe_escape_component_")

try:
    # Ensure repo root is on path so the public package resolves.
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from src.languages.erlang import _escape_component

    # ── Test 1: π (U+03C0) ──
    # Code yields '_3c0' — three hex digits for the code point.
    # The spec requires exactly two hex digits.
    actual = _escape_component("\u03c0")

    # Verify the actual output structure: underscore + hex digits.
    # The code uses f"_{ord(char):02x}" which guarantees min width 2,
    # but does NOT cap at exactly 2 hex digits.
    underscore_pos = actual.find("_")
    if underscore_pos == -1:
        raise AssertionError(f"Expected underscore in output, got {actual!r}")
    hex_part = actual[underscore_pos + 1:]

    # The bug: hex_part should be exactly 2 chars per spec, but for code points
    # >= 256 the :02x format produces 3+ chars.
    uses_two_hex_digits = len(hex_part) == 2 and all(c in "0123456789abcdefABCDEF" for c in hex_part)

    # spec_claim: "every other character is replaced by an underscore followed by
    # its Unicode code point expressed as a zero-padded two-digit hexadecimal number."
    # actual_behavior produces variable-width hex.
    # CONFIRMED if the output has more than 2 hex digits for π (code point 0x3C0).
    passed = not uses_two_hex_digits  # bug reproduced when spec violated

    # Build expected per spec: zero-padded two-digit hex of ord('\u03c0') = 960 = 0x3C0
    # which can't be represented in exactly 2 digits without truncation.
    # The simplest spec-consistent output would be "_c0" (truncated).
    expected = "_c0"

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected (spec two-digit): {expected!r} "
          f"| hex digits in output: {len(hex_part)} (spec requires exactly 2)")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
