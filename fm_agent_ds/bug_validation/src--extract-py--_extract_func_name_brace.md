# Bug Report: _extract_func_name_brace

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/extract-py/_extract_func_name_brace.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the bare function name as a string when signature_text contains a recognizable function declaration, or None when it does not. For declarations matching the pattern of an operator overload  'operator' followed by operator tokens or keywords (e.g., '[]', '()', 'new[]', arithmetic/bitwise symbols) immediately preceding '('  returns the full operator specifier string. For all other declarations, after removing template/generic angle-bracket regions from signature_text, returns the first word token immediately preceding '(' whose text is not a member of lang_cfg['keywords']. Returns None when no such token exists after keyword filtering.

---

### Actual Behavior

The function returns a string representing the extracted function name, or None if no name could be extracted. Specifically:
- If signature_text contains a substring matching the regular expression `\b(operator\s*(?:\[\]|\(\)|[+\-*/%&|^~!=<>]+|new(?:\s*\[\s*\])?|delete(?:\s*\[\s*\])?))\s*\(`, return the captured group (the operator keyword followed by its overload specification, e.g., 'operator+', 'operator()', 'operator new[]').
- Otherwise, let cleaned_text be the result of _strip_angle_brackets(signature_text). For each match of the regular expression `\b(\w+)\s*\(` in cleaned_text (in left-to-right order), if the captured group (the identifier before the parenthesis) is not a member of lang_cfg['keywords'], return that identifier.
- If no such identifier is found, return None.

Formally:
Let op_pattern = /\b(operator\s*(?:\[\]|\(\)|[+\-*/%&|^~!=<>]+|new(?:\s*\[\s*\])?|delete(?:\s*\[\s*\])?))\s*\(/
Let id_pattern = /\b(\w+)\s*\(/
Let keywords = lang_cfg['keywords']
Let remove_brackets(s) = _strip_angle_brackets(s)

If  match m = search(op_pattern, signature_text), then return m.group(1).
Else let cleaned = remove_brackets(signature_text).
If  match m in finditer(id_pattern, cleaned) such that m.group(1)  keywords, then return the first such m.group(1).
Else return None.

---

## Code Evidence

Line 4: m = re.search(...)
Line 9: if m:
Line 10: return m.group(1)

---

## Trigger Condition

The code searches for the operator pattern in the entire signature_text before stripping angle brackets. This causes a false match on 'operator+' inside the template parameter list, even though the overall declaration is not an operator overload. The specification requires that operator overload patterns apply only to operator declarations; for all other declarations the name should be extracted after removing template/generic angle-bracket regions, yielding 'bar' here.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `signature_text` | `"void bar(Template<operator()(int)> t)"` |
| `lang_cfg` | `{"keywords": set()}` |

### Expected (spec-correct) Output

`"bar"`

### Actual (buggy) Output

`"operator()"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.extract import _extract_func_name_brace

sig = "void bar(Template<operator()(int)> t)"
cfg = {"keywords": set()}
result = _extract_func_name_brace(sig, cfg)
# actual (buggy) output: "operator()"
# expected (correct) output: "bar"
```

---

## Probe Script

```python
"""Probe for bug: _extract_func_name_brace matches operator pattern
inside angle brackets before stripping them, producing a false match.

Bug ID: src--extract-py--_extract_func_name_brace
"""

import sys
import os
from pathlib import Path

# Ensure the repo root is importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from src.extract import _extract_func_name_brace

    # Minimal lang_cfg with no keywords (none needed for the test)
    lang_cfg: dict = {"keywords": set()}

    # Signature text where `operator()(int)` appears inside angle brackets.
    # The real function name is `bar`, but `re.search` will match
    # `operator()` inside the template parameter list first because
    # angle brackets are NOT stripped before the operator-pattern scan.
    signature_text: str = "void bar(Template<operator()(int)> t)"

    actual: str | None = _extract_func_name_brace(signature_text, lang_cfg)
    expected: str = "bar"

    # The bug is CONFIRMED if actual != expected (the operator inside <>
    # was matched instead of the real function name).
    passed: bool = actual != expected

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: 'operator()' | expected: 'bar'
```
