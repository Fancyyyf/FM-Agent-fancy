# Bug Report: _string_list

**Source file:** `src/call_graph_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When value is not a list, raises ValueError whose message includes source and key
  - When value is a list and any element is not a string, raises ValueError whose message includes source and key
  - Otherwise, returns a tuple containing the label-normalized form of every string element of value whose label-normalized form is non-blank
  - The relative order of elements in the returned tuple preserves the relative order of the corresponding elements in value

---

### Actual Behavior

If `value` is not a list, a ValueError is raised with the message "{source}: '{key}' must be a string array". If `value` is a list, then for each element at 1based index `i`, if the element is not a string, a ValueError is raised with the message f"{source}: {key}[{i}] must be a string". Otherwise, if all elements are strings, the function returns a tuple containing every `_clean_label(item)` that is not empty (i.e., `len(clean) > 0`), preserving the original order of items. Formally, let `V` be the input argument `value`. Then: (isinstance(V, list)  raises ValueError(source + ": '" + key + "' must be a string array"))  (isinstance(V, list)  ( ( i  {1,,|V|} : isinstance(V[i-1], str))  raises ValueError(source + ": " + key + "[" + str(i) + "] must be a string") )  ( i  {1,,|V|} : isinstance(V[i-1], str)  return = tuple( [clean for x in V if (clean := _clean_label(x)) != ""] ) ) ).

---

## Code Evidence

Line 9: if label:

---

## Trigger Condition

The code filters cleaned labels using 'if label:', which is truthy for any non-empty string. The specification requires including only non-blank strings, so blank (whitespace-only but non-empty) strings returned by _clean_label would be incorrectly kept.

---

## How to trigger the bug

The bug is triggered when `_string_list` receives a list element that, after processing by `_clean_label`, produces a non-empty but blank (content-free) string. Zero-width Unicode characters are the practical vector: Python's `str.strip()` does not classify characters like U+200B (ZERO WIDTH SPACE), U+200D (ZERO WIDTH JOINER), U+2060 (WORD JOINER), or U+FEFF (BOM/ZWNBSP) as whitespace, so `_clean_label` returns them unchanged. The `if label:` truthiness check then treats these invisible strings as valid, violating the specification which requires excluding all "non-blank" entries.

### Inputs

| Parameter | Value |
|-----------|-------|
| `value` (`callsite_names`) | `["\u200b"]` (zero-width space) |
| `key` | `"caller.callsite_names"` |
| `source` | (path to temp JSON file) |

### Expected (spec-correct) Output

An empty tuple `()` or tuple that excludes the zero-width entry — because the label-normalized form has no meaningful (non-blank) content.

### Actual (buggy) Output

`("\u200b",)` — the zero-width space passes `if label:` because it is a non-empty string, even though it is blank/invisible.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, tempfile, os, sys
sys.path.insert(0, ".")

from src.call_graph_edges import load_call_edges

payload = {
    "edges": [{
        "caller": {
            "fqn": "some::module::func",
            "callsite_names": ["\u200b"],
        },
        "callee": {
            "fqn": "other::callee::target",
        },
    }]
}

fd, tmp = tempfile.mkstemp(suffix=".json")
with os.fdopen(fd, "w") as f:
    json.dump(payload, f)

try:
    edges = load_call_edges(tmp)
    print(edges[0].caller.callsite_names)
    # actual (buggy) output: ('\u200b',)
    # expected (correct) output: ()
finally:
    os.unlink(tmp)
```

---

## Probe Script

```python
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
```

### Probe Output

```
BUG (zero-width space only): blank entries kept — ['\u200b']
BUG (zero-width joiner only): blank entries kept — ['\u200d']
BUG (word joiner only): blank entries kept — ['\u2060']
BUG (BOM only): blank entries kept — ['\ufeff']
BUG (spaces + ZWSP + spaces): blank entries kept — ['\u200b']
OK  (spaces only): input '   ' → result () (no blank entries)
OK  (tab only): input '\t' → result () (no blank entries)
OK  (newline only): input '\n' → result () (no blank entries)
OK  (mixed whitespace): input ' \t\n ' → result () (no blank entries)
OK  (semicolon only): input ';' → result () (no blank entries)
OK  (semicolons with spaces): input ' ; ; ' → result (';',) (no blank entries)
OK  (spaces and semicolons): input '   ;;   ' → result () (no blank entries)
OK  (single-quoted spaces): input "'   '" → result () (no blank entries)
OK  (double-quoted spaces): input '"   "' → result () (no blank entries)
OK  (single-quoted empty): input "''" → result () (no blank entries)
OK  (double-quoted empty): input '""' → result () (no blank entries)
OK  (single-quoted tab): input "'\t'" → result () (no blank entries)
CONFIRMED — _string_list includes blank (non-meaningful) labels that should have been filtered out by the spec
```
