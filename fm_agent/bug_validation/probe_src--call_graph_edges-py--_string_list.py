"""Probe script for bug src--call_graph_edges-py--_string_list.

Bug claim: _string_list uses `if label:` (Python truthiness) to filter
cleaned labels. Per spec, the filter should exclude labels whose
label-normalized form is "blank" (no meaningful content). `if label:`
keeps any non-empty string, including strings that are blank but non-empty
(e.g., invisible/whitespace-only strings returned by _clean_label).

The probe constructs a minimal JSON edge file where callsite_names
contains strings designed to stress-test the filter, then checks whether
the returned CallerSelector.callsite_names contains any blank entries.

Entry point: load_call_edges() — the public API.
"""

import json
import os
import sys
import tempfile

# Ensure the project's src/ directory is on the Python path.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    from src.call_graph_edges import load_call_edges
except Exception as e:
    print(f"ERROR: import failed: {e}")
    sys.exit(1)


def _is_blank(s: str) -> bool:
    """Return True if s has no meaningful (visible) content."""
    if not s:
        return True
    # Strip standard Unicode whitespace — if nothing remains, it's blank.
    if not s.strip():
        return True
    # Check for zero-width / invisible characters only.
    # These are not stripped by str.strip() but are invisible.
    invisible = {
        "\u200b",  # ZERO WIDTH SPACE
        "\u200c",  # ZERO WIDTH NON-JOINER
        "\u200d",  # ZERO WIDTH JOINER
        "\u2060",  # WORD JOINER
        "\ufeff",  # ZERO WIDTH NO-BREAK SPACE / BOM
        "\u200e",  # LEFT-TO-RIGHT MARK
        "\u200f",  # RIGHT-TO-LEFT MARK
        "\u061c",  # ARABIC LETTER MARK
    }
    cleaned = s
    for ch in invisible:
        cleaned = cleaned.replace(ch, "")
    return not cleaned.strip()


def _find_blank_entries(callsite_names):
    """Return list of blank entries in a tuple of strings."""
    return [name for name in callsite_names if _is_blank(name)]


# Strategy 1: Zero-width characters — _clean_label doesn't strip these
# because Python's str.strip() doesn't treat them as whitespace.
# They pass `if label:` (truthy) but have no visible content.
zw_tests = [
    ("zero-width space only", "\u200b"),
    ("zero-width joiner only", "\u200d"),
    ("word joiner only", "\u2060"),
    ("BOM only", "\ufeff"),
    ("spaces + ZWSP + spaces", "  \u200b  "),
]

# Strategy 2: Standard whitespace — _clean_label strips these to empty,
# so they should be correctly filtered. These serve as baseline tests.
baseline_tests = [
    ("spaces only", "   "),
    ("tab only", "\t"),
    ("newline only", "\n"),
    ("mixed whitespace", " \t\n "),
]

# Strategy 3: Strings with semicolons — _clean_label strips trailing
# semicolons, then strips whitespace. Edge cases around semicolons.
semicolon_tests = [
    ("semicolon only", ";"),
    ("semicolons with spaces", " ; ; "),
    ("spaces and semicolons", "   ;;   "),
]

# Strategy 4: Quoted strings — _clean_label strips matching quotes,
# then strips whitespace. Test various quoted forms.
quote_tests = [
    ("single-quoted spaces", "'   '"),
    ("double-quoted spaces", '"   "'),
    ("single-quoted empty", "''"),
    ("double-quoted empty", '""'),
    ("single-quoted tab", "'\t'"),
]

confirmed = False
evidence = []

for label, test_str in zw_tests + baseline_tests + semicolon_tests + quote_tests:
    payload = {
        "edges": [
            {
                "caller": {
                    "fqn": "some::module::func",
                    "callsite_names": [test_str],
                },
                "callee": {
                    "fqn": "other::callee::target",
                },
            }
        ]
    }

    fd, tmp_path = tempfile.mkstemp(
        suffix=".json", prefix="probe_string_list_"
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f)

        try:
            result = load_call_edges(tmp_path)
        except Exception as exc:
            evidence.append(
                f"ERROR ({label}): {type(exc).__name__}: {exc}"
            )
            continue

        if not result:
            evidence.append(f"SKIP ({label}): no edges returned")
            continue

        edge = result[0]
        names = edge.caller.callsite_names
        blanks = _find_blank_entries(names)

        if blanks:
            confirmed = True
            evidence.append(
                f"BUG ({label}): blank entries kept — {blanks!r}"
            )
        else:
            evidence.append(
                f"OK  ({label}): input {test_str!r} → "
                f"result {names!r} (no blank entries)"
            )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

# Print evidence
for line in evidence:
    print(line)

if confirmed:
    print("CONFIRMED — _string_list includes blank (non-meaningful) "
          "labels that should have been filtered out by the spec")
else:
    print("NOT CONFIRMED — all blank labels were correctly filtered; "
          "_clean_label never returns a non-empty blank string, "
          "making `if label:` functionally equivalent to the spec's "
          "'non-blank' requirement")
