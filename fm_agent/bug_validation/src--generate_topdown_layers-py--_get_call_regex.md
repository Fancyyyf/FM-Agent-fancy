# Bug Report: _get_call_regex

**Source file:** `src/generate_topdown_layers.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a compiled regular expression pattern object whose matches
    identify bare-name function-call sites in source code written in the
    language identified by lang_key
  - Capture group 1 of every match yields the identifier string (function
    name) that appears immediately before the opening parenthesis of a call
  - The pattern skips language-specific syntax that may appear between the
    identifier and the opening parenthesis:
    * For C, C++, Java, TypeScript, JavaScript, CUDA, and ArkTS: skips an
      optional angle-bracket-enclosed segment (<...>) representing template
      or generic arguments
    * For Rust: skips an optional turbofish segment (::<...>) representing
      generic type arguments
    * For Go: skips an optional bracket-enclosed segment ([...]) representing
      type parameters
    * For all other language keys: matches a bare identifier directly followed
      by an opening parenthesis with optional whitespace
  - The function is deterministic: repeated calls with the same lang_key
    return patterns with identical matching behavior
  - The function has no side effects beyond creating and returning a compiled
    regex pattern object

---

### Actual Behavior

The function returns a compiled regular expression Pattern object. The pattern depends on lang_key:
- If lang_key  {'cpp','c','java','typescript','javascript','cuda','arkts'}: pattern = r'\b(\w+)\s*(?:<[^>]*>)?\s*\('
- If lang_key = 'rust': pattern = r'\b(\w+)\s*(?:::<[^>]*>)?\s*\('
- If lang_key = 'go': pattern = r'\b(\w+)\s*(?:\[[^\]]*\])?\s*\('
- Otherwise: pattern = r'\b(\w+)\s*\('
Formally: result = _get_call_regex(lang_key)  result is a Pattern with result.pattern equal to the string defined above for the given lang_key, and result behaves as described by re.compile.

---

## Code Evidence

Line 219: return re.compile(r"\b(\w+)\s*(?:<[^>]*>)?\s*\(")

The character class `[^>]*` matches any characters except `>`, which means it stops at the first `>` encountered. This prevents the pattern from matching nested template/generic argument lists, e.g. `bar<map<int,string>>(k)` or `baz<vector<pair<int,int>>>(v)`.

---

## Trigger Condition

The regex uses `<[^>]*>` to skip an angle-bracket-enclosed segment, but this cannot handle nested angle brackets that are valid in C++, Java, and other languages. As a result, the pattern does not match all function-call sites as required by the specification.

---

## How to trigger the bug

When `_get_call_regex` is called with a language key that uses the angle-bracket-skipping pattern (e.g., `"cpp"`, `"java"`, `"c"`, `"typescript"`, etc.), the compiled regex fails to match call sites where the template/generic arguments themselves contain nested angle brackets.

### Inputs

| Parameter | Value |
|---|---|
| lang_key | `"cpp"` |

Test strings:
| Test Input | Expected | Actual |
|---|---|---|
| `foo<int>(x)` | match, group1=`foo` | match, group1=`foo` ✓ |
| `bar<map<int,string>>(k)` | match, group1=`bar` | **no match** ✗ |
| `baz<vector<pair<int,int>>>(v)` | match, group1=`baz` | **no match** ✗ |

### Expected (spec-correct) Output

For `"cpp"`, the regex should match function identifiers followed by optional angle-bracket template arguments containing any nesting depth, and then an opening parenthesis. All three test strings above should produce a match with the correct identifier in group 1.

### Actual (buggy) Output

For `"cpp"`, the regex `\b(\w+)\s*(?:<[^>]*>)?\s*\(` only matches single-level template arguments (no nested `>`). Nested template expressions fail because `[^>]*` terminates at the first `>` instead of matching the balanced pair properly.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import sys, os
sys.path.insert(0, os.getcwd())
from src.generate_topdown_layers import _get_call_regex

regex = _get_call_regex("cpp")

# Single-level template: works correctly
print(regex.search("foo<int>(x)"))   # => match, group1='foo'

# Nested template: fails to match
print(regex.search("bar<map<int,string>>(k)"))   # => None (BUG)
# expected (correct) output: match, group1='bar'

# Deeply nested: also fails
print(regex.search("baz<vector<pair<int,int>>>(v)"))  # => None (BUG)
# expected (correct) output: match, group1='baz'
```

---

## Probe Script

```py
"""Probe script for bug: _get_call_regex regex cannot handle nested angle brackets.

Bug ID: src--generate_topdown_layers-py--_get_call_regex

The spec claims _get_call_regex for C++/Java/etc. will skip an angle-bracket-enclosed
segment representing template arguments between the identifier and the opening paren.
The regex uses [^>]* which fails on nested templates like foo<bar<int>>(x).
"""
import sys
import os

# Ensure project root is on Python path for standalone execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.generate_topdown_layers import _get_call_regex
except Exception as e:
    print(f"ERROR: Cannot import _get_call_regex: {e}")
    sys.exit(1)

bug_id = "src--generate_topdown_layers-py--_get_call_regex"

# --- Test cases ---
# lang_key -> list of (input_str, expected_match, expected_group1, description)
test_cases = {
    "cpp": [
        # Simple template: should match
        ("foo<int>(x)", True, "foo", "simple single-level template foo<int>(x)"),
        # Nested template: should match but WON'T with [^>]* regex
        ("bar<map<int,string>>(k)", True, "bar", "nested template bar<map<int,string>>(k)"),
        # Deeply nested template
        ("baz<vector<pair<int,int>>>(v)", True, "baz", "deeply nested baz<vector<pair<int,int>>>(v)"),
    ],
}

confirmed = False
failures = []
all_passed = True

for lang_key, cases in test_cases.items():
    regex = _get_call_regex(lang_key)
    print(f"Testing lang_key={lang_key!r}, regex pattern: {regex.pattern}")

    for input_str, expected_match, expected_group1, desc in cases:
        m = regex.search(input_str)
        actual_match = m is not None
        actual_group1 = m.group(1) if m else None

        ok = True
        if actual_match != expected_match:
            ok = False
        elif expected_match and actual_group1 != expected_group1:
            ok = False

        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {desc}")
        print(f"    input:        {input_str!r}")
        print(f"    expected:     match={expected_match}, group1={expected_group1!r}")
        print(f"    actual:       match={actual_match}, group1={actual_group1!r}")

        if not ok:
            failures.append((input_str, expected_group1, actual_group1, desc))
            all_passed = False

if failures:
    # Bug confirmed: some cases failed where they should have succeeded
    print(f"\nBug CONFIRMED — {len(failures)} failure(s):")
    for inp, exp, act, desc in failures:
        print(f"  {desc}: actual group1={act!r}, expected={exp!r}")
    print("CONFIRMED")
else:
    print("\nNOT CONFIRMED — all test cases passed")
```

### Probe Output

```
Testing lang_key='cpp', regex pattern: \b(\w+)\s*(?:<[^>]*>)?\s*\(
  [PASS] simple single-level template foo<int>(x)
    input:        'foo<int>(x)'
    expected:     match=True, group1='foo'
    actual:       match=True, group1='foo'
  [FAIL] nested template bar<map<int,string>>(k)
    input:        'bar<map<int,string>>(k)'
    expected:     match=True, group1='bar'
    actual:       match=False, group1=None
  [FAIL] deeply nested baz<vector<pair<int,int>>>(v)
    input:        'baz<vector<pair<int,int>>>(v)'
    expected:     match=True, group1='baz'
    actual:       match=False, group1=None

Bug CONFIRMED — 2 failure(s):
  nested template bar<map<int,string>>(k): actual group1=None, expected='bar'
  deeply nested baz<vector<pair<int,int>>>(v): actual group1=None, expected='baz'
CONFIRMED
```
