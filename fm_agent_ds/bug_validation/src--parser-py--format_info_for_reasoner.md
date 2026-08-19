# Bug Report: format_info_for_reasoner

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/parser-py/format_info_for_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a FunctionSpecMap containing one entry per callee in the input list. Each entry maps the callee's "name" value to a two-line string of the form "Pre-condition: <pre_condition>\nPost-condition: <post_condition>". The signatures attribute of the returned FunctionSpecMap is a dict mapping each callee's "name" value to its "signature" value. Returns an empty FunctionSpecMap (containing no entries and an empty signatures dict) when the input list is empty.

---

### Actual Behavior

The function returns a newly created FunctionSpecMap object. Let callees = info['callees'] (a list of dicts, each with keys 'name', 'signature', 'pre_condition', 'post_condition'). For each d in callees, define name = d['name'], sig = d['signature'], spec_str = 'Pre-condition: ' + d['pre_condition'] + '\nPost-condition: ' + d['post_condition']. The resulting FunctionSpecMap stores: for each distinct name, the mappings name  spec_str and name  sig are taken from the last occurrence of that name in the iteration order of callees. If callees is empty, the map contains no entries. No exceptions are raised, and no external state is modified.

---

## Code Evidence

Line 4: for callee in info.get("callees", []):
Line 9: knowledge_map.add_entry(
Line 10:     callee.get("name", ""),
Line 11:     callee.get("signature", ""),
Line 12:     callee_spec,
Line 13: )

---

## Trigger Condition

The specification requires one entry per callee in the input list, but the code uses a mapping keyed by name and overwrites duplicates. For the counterexample with two callees both named 'foo', the resulting FunctionSpecMap has only one entry (the second callee's spec and signature) instead of preserving entries for each callee as required.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| info["callees"][0]["name"] | "foo" |
| info["callees"][0]["signature"] | "def foo(x: int) -> int" |
| info["callees"][0]["pre_condition"] | "x > 0" |
| info["callees"][0]["post_condition"] | "returns x + 1" |
| info["callees"][1]["name"] | "foo" |
| info["callees"][1]["signature"] | "def foo(x: str) -> str" |
| info["callees"][1]["pre_condition"] | "x is not empty" |
| info["callees"][1]["post_condition"] | "returns x.upper()" |

### Expected (spec-correct) Output

`FunctionSpecMap containing 2 entries — one per callee in the input list`

### Actual (buggy) Output

`FunctionSpecMap containing 1 entry — only the last callee named "foo" is retained; the first is overwritten because FunctionSpecMap extends dict and uses the callee name as a key.`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.parser import format_info_for_reasoner

info = {
    "callees": [
        {
            "name": "foo",
            "signature": "def foo(x: int) -> int",
            "pre_condition": "x > 0",
            "post_condition": "returns x + 1",
        },
        {
            "name": "foo",
            "signature": "def foo(x: str) -> str",
            "pre_condition": "x is not empty",
            "post_condition": "returns x.upper()",
        },
    ]
}

result = format_info_for_reasoner(info)
# actual (buggy) output: len(result) == 1 (only second "foo" callee retained)
# expected (correct) output: len(result) == 2 (one per callee)
```

---

## Probe Script

```python
import sys
import os

# Ensure repo root is on path so we can import the source module
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.parser import format_info_for_reasoner, FunctionSpecMap

    # Two callees with the same name "foo" but different specs/signatures.
    # Spec claims one entry per callee, but dict-based FunctionSpecMap
    # overwrites duplicate names, keeping only the last one.
    info = {
        "callees": [
            {
                "name": "foo",
                "signature": "def foo(x: int) -> int",
                "pre_condition": "x > 0",
                "post_condition": "returns x + 1",
            },
            {
                "name": "foo",
                "signature": "def foo(x: str) -> str",
                "pre_condition": "x is not empty",
                "post_condition": "returns x.upper()",
            },
        ]
    }

    result = format_info_for_reasoner(info)

    # Expected (spec-correct): 2 entries — one per callee
    # Actual (buggy): only 1 entry because second "foo" overwrites first
    expected_entries = 2
    actual_entries = len(result)

    # Also verify: the retained spec should be from the LAST callee (overwrite),
    # which should be the second one if the bug exists as described.
    retained_spec = result.get("foo", "")
    second_callee_spec_expected = (
        "Pre-condition: x is not empty\n"
        "Post-condition: returns x.upper()"
    )
    first_callee_spec_expected = (
        "Pre-condition: x > 0\n"
        "Post-condition: returns x + 1"
    )

    entry_count_mismatch = actual_entries != expected_entries
    last_overwrites = retained_spec == second_callee_spec_expected

    passed = entry_count_mismatch and last_overwrites

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(
        f"CONFIRMED — actual entries: {actual_entries!r} (only last callee survives)"
        f" | expected entries: {expected_entries!r} (one per callee)"
    )
    print(f"  retained spec is from callee #2: {retained_spec!r}")
else:
    if not entry_count_mismatch:
        print(
            f"NOT CONFIRMED — entry count matched expected: {actual_entries!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — entry count mismatch ({actual_entries} vs {expected_entries})"
            f" but retained spec does not match callee #2: {retained_spec!r}"
        )
```

### Probe Output

```
CONFIRMED — actual entries: 1 (only last callee survives) | expected entries: 2 (one per callee)
  retained spec is from callee #2: 'Pre-condition: x is not empty\nPost-condition: returns x.upper()'
```
