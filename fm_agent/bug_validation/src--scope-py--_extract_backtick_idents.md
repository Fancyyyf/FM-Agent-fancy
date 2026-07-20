# Bug Report: _extract_backtick_idents

**Source file:** `src/scope-py/_extract_backtick_idents.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a set of lowercased identifier strings extracted from issue_text
- Every returned string has length ≥ 2 and consists of ASCII letters, digits, and underscores
- An identifier is included if and only if it appears within a backtick-quoted span (`` `...` ``) or a triple-backtick-fenced code block (`` ```...``` ``) in issue_text
- Identifiers that match Python language keywords or a fixed set of common built-in / stop-word names are excluded from the returned set
- For backtick-quoted spans, leading RST/Sphinx role prefixes of the form `<word>:<word>` are stripped before identifier extraction; the prefix portion contributes no identifiers to the result
- Within code blocks, only identifiers of length ≥ 3 characters are extracted

---

### Actual Behavior

The function returns a set `result` of strings. Each string `t` in `result` satisfies:
- `t` is a valid identifier-like token extracted from `issue_text`,
- `t` has length at least 2, is not in `_PY_KEYWORDS` and not in `_STOP`,
- `t` is obtained by lowercasing and stripping leading/trailing underscores from a match.

---

## Code Evidence

Line 8: `t = token.lower().strip('_')`

---

## Trigger Condition

The code strips leading and trailing underscores from identifiers, but the specification does not mention such stripping. For the input '`__init__`', the code returns {'init'} while the specification expects {'__init__'}.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| issue_text | `` "`__init__`" `` |

### Expected (spec-correct) Output

`{'__init__'}` — the identifier `__init__` should be preserved with its leading/trailing underscores, as the spec makes no mention of underscore stripping.

### Actual (buggy) Output

`{'init'}` — the `.strip('_')` call on line 125 of `src/scope.py` removes leading/trailing underscores, reducing `__init__` to `init`.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.scope import _parse_issue_signals

signals = _parse_issue_signals("`__init__`")
print(signals["backtick_idents"])
# actual (buggy) output: {'init'}
# expected (correct) output: {'__init__'}
```

---

## Probe Script

```python
"""Probe script for bug src--scope-py--_extract_backtick_idents.

Bug: _extract_backtick_idents (called via _parse_issue_signals) strips
leading/trailing underscores from identifiers via .strip('_').

Trigger: input '`__init__`' → buggy code returns {'init'}, spec expects {'__init__'}.
"""
import sys
from pathlib import Path

# Ensure the project root is on sys.path so 'src' is importable
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from src.scope import _parse_issue_signals

    # The trigger condition: backtick-quoted __init__
    issue_text = "`__init__`"
    signals = _parse_issue_signals(issue_text)
    actual = signals["backtick_idents"]

    # Per spec, '__init__' should be preserved (not stripped to 'init')
    expected_wanted = "__init__"
    expected_unwanted = "init"

    # The bug strips underscores, so we expect 'init' in result but not '__init__'
    has_buggy = expected_unwanted in actual
    has_spec_correct = expected_wanted in actual

    # CONFIRMED = bug exists (stripped underscores, returns 'init' instead of '__init__')
    bug_reproduced = has_buggy and not has_spec_correct

    if bug_reproduced:
        print(f"CONFIRMED — actual: {actual!r} | expected '__init__' preserved, 'init' absent")
    elif has_spec_correct and not has_buggy:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
    else:
        print(f"NOT CONFIRMED — ambiguous: actual={actual!r}, expected='__init__' but got neither")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: {'init'} | expected '__init__' preserved, 'init' absent
```
