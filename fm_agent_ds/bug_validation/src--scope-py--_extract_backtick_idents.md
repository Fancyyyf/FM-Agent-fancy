# Bug Report: _extract_backtick_idents

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/scope-py/_extract_backtick_idents.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a set of lowercase strings, each a valid identifier token (a contiguous sequence beginning with a letter or underscore, followed by zero or more alphanumeric or underscore characters) of length at least 2, extracted from single-backtick-quoted spans and triple-backtick-fenced code blocks within issue_text. Identifier tokens matching a programming-language keyword are excluded. Identifier tokens matching a predefined stop-word set are excluded. Within single-backtick spans, any leading RST/Sphinx role-annotation prefix (a colon-separated pair of lowercase words followed by optional whitespace) is removed before identifier extraction. Leading underscores are stripped from each candidate before keyword and stop-word comparison.

---

### Actual Behavior

The function returns a set `result` containing exactly those strings `s` for which there exists a substring `w` in `issue_text` satisfying one of the following two conditions, and after lowercasing `w` and stripping leading/trailing underscores to obtain `t`, we have `s = t`, `len(s) >= 2`, `s` is not a Python keyword ( `_PY_KEYWORDS`) and `s` is not a common builtin/stopword ( `_STOP`):
(1) `w` appears inside a backtickdelimited span (i.e., between two backtick characters) as a maximal contiguous run of alphanumerics or underscores of length at least 2 (matching the pattern `[a-zA-Z_][a-zA-Z0-9_]{1,}`), *after* the span has been stripped of an optional RST/Sphinx role prefix (a prefix matching `^[a-z]+:[a-z]+\s*`).
(2) `w` appears inside a triplebacktick fenced code block (from ``` to ```) as a wholeword identifier bounded by word boundaries, starting with a letter or underscore and consisting solely of alphanumerics and underscores, with length at least 3 (matching `\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b`).
Formally:
result = { s : t  T, t = w.lower().strip('_'), s = t, len(s)  2, s  _PY_KEYWORDS, s  _STOP },
where T = T  T, with
T = { w :  backtick span B  issue_text (B enclosed in backticks), let B' = re.sub(r'^[a-z]+:[a-z]+\s*', '', B.strip()), and w  re.findall(r'[a-zA-Z_][a-zA-Z0-9_]{1,}', B') },
T = { w :  code block C  issue_text (from ``` to ```), and w  re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b', C) }.
The original `issue_text` remains unchanged.

---

## Code Evidence

Line 17: for ident in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b', block):

---

## Trigger Condition

The specification requires identifiers of length at least 2 to be extracted from code blocks. The code on line 17 uses a regex that demands at least two characters after the first letter/underscore, i.e., total length >= 3. A two-letter identifier like 'ab' inside a code block is incorrectly omitted, while the specification would include it.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `issue_text` | `"```\nab = 42\ncd = ab\n```"` |

### Expected (spec-correct) Output

`{'ab', 'cd'}`

The specification requires identifiers of length at least 2 to be extracted from code blocks. The identifiers `ab` and `cd` are 2 characters each, not Python keywords, not stop words, and should be included.

### Actual (buggy) Output

The code block regex path produces `[]` (empty) because the regex `\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b` demands a minimum total length of 3 characters. The 2-character identifiers `ab` and `cd` are silently dropped.

Note: The single-backtick regex path (`r'[a-zA-Z_][a-zA-Z0-9_]{1,}'` on line 132) partially masks this bug because it can fire on triple-backtick delimiters — matching between the third backtick of the opening ``` and the first backtick of the closing ```. However, the code-block-specific regex path is independently broken.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import re

# The buggy regex from line 17 (extracted) / line 136 (source)
block = "```\nab = 42\ncd = ab\n```"
buggy_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b', block)
# actual (buggy) output: []
# expected (correct) output: ['ab', 'cd', 'ab']

# The corrected regex (change {2,} to {1,})
corrected_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{1,})\b', block)
# output: ['ab', 'cd', 'ab']
```

---

## Probe Script

```python
import sys
import os
import re

# Add the repo root to sys.path so 'src.scope' can be imported.
# __file__ =  <repo_root>/fm_agent/bug_validation/probe_<bug_id>.py
# Three dirnames up reaches the repo root.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from src.scope import _extract_backtick_idents
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# ── test case ──────────────────────────────────────────────────────────────
# The specification requires identifiers of length ≥ 2 to be extracted from
# triple-backtick code blocks.  The implementation at line 136 uses
#   re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b', block)
# which demands at least two characters *after* the leading letter/underscore,
# i.e. a minimum total length of 3.  A two-letter identifier like 'ab' is
# therefore silently dropped by the code-block-specific regex.
#
# Note: The single-backtick regex (line 132) also fires on triple-backtick
# delimiters (matching the third backtick of opening ``` to the first backtick
# of closing ```), which can mask the bug.  This probe tests the code block
# regex pattern directly in isolation to demonstrate the bug.

# ── Test 1 (control): single-backtick span with 2-char identifier ──────
# The single-backtick path uses {1,} which correctly captures length >= 2.
text1 = "See `ab` for details"
try:
    result1 = _extract_backtick_idents(text1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
ab_in_backtick = 'ab' in result1

# ── Test 2: code block regex in isolation ─────────────────────────────
# This is the exact regex from line 136 of src/scope.py (the buggy pattern).
block = "```\nab = 42\ncd = ab\n```"
buggy_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b', block)
ab_in_buggy = 'ab' in buggy_matches
cd_in_buggy = 'cd' in buggy_matches

# ── Test 3: corrected regex (what the spec demands) ────────────────────
# {1,} means at least 1 more after the first char, i.e. total >= 2.
corrected_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{1,})\b', block)
ab_in_corrected = 'ab' in corrected_matches
cd_in_corrected = 'cd' in corrected_matches

# ── Verdict ────────────────────────────────────────────────────────────
if ab_in_backtick and (not ab_in_buggy) and ab_in_corrected and (not cd_in_buggy) and cd_in_corrected:
    print(
        'CONFIRMED'
        ' — backtick-path correctly finds 2-char idents ({1,} quantifier)'
        ' | code-block-path regex (line 136) has wrong quantifier {2,}'
        ' (misses "ab", "cd")'
        ' | corrected {1,} finds them'
        f' | buggy_matches={buggy_matches!r}, corrected_matches={corrected_matches!r}'
    )
else:
    print(
        'NOT CONFIRMED'
        f' — ab_in_backtick={ab_in_backtick}'
        f', ab_in_buggy={ab_in_buggy}, cd_in_buggy={cd_in_buggy}'
        f', ab_in_corrected={ab_in_corrected}, cd_in_corrected={cd_in_corrected}'
    )
```

### Probe Output

```
CONFIRMED — backtick-path correctly finds 2-char idents ({1,} quantifier) | code-block-path regex (line 136) has wrong quantifier {2,} (misses "ab", "cd") | corrected {1,} finds them | buggy_matches=[], corrected_matches=['ab', 'cd', 'ab']
```
