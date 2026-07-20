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
