"""Probe script: verify whether _find_call_sites incorrectly captures
identifiers inside string/character literals.

Bug claim: _strip_comments_from_source only strips comments, not string
literals, so _find_call_sites can match identifiers inside string literals.

If the code correctly masks string literals, the probe should return
NOT CONFIRMED for the string-literal cases.
"""
import sys

try:
    from src.generate_topdown_layers import _find_call_sites, _get_call_regex, _strip_comments_from_source
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Use "python" as lang_key — Python uses # comments and the default regex
LANG_KEY = "python"
# These are stems we're looking for.
KNOWN_STEMS = {"foo", "bar", "baz", "qux", "helper"}
# No keywords to exclude for this test
KEYWORDS = set()

# -------------------------------------------------------------------
# Test 1: Identifier inside a single-quoted string
# Expected: foo should NOT be found (it's inside a string literal)
# -------------------------------------------------------------------
text1 = 'x = \'foo() should not match\''
result1 = _find_call_sites(text1, LANG_KEY, KNOWN_STEMS, KEYWORDS)

# -------------------------------------------------------------------
# Test 2: Identifier inside a double-quoted string
# Expected: bar should NOT be found (it's inside a string literal)
# -------------------------------------------------------------------
text2 = 'x = "bar() inside string"'
result2 = _find_call_sites(text2, LANG_KEY, KNOWN_STEMS, KEYWORDS)

# -------------------------------------------------------------------
# Test 3: Identifier inside a triple-quoted string
# Expected: baz should NOT be found
# -------------------------------------------------------------------
text3 = 'x = """baz() in triple quotes"""'
result3 = _find_call_sites(text3, LANG_KEY, KNOWN_STEMS, KEYWORDS)

# -------------------------------------------------------------------
# Test 4: Real function call outside any string
# Expected: qux SHOULD be found (positive control)
# -------------------------------------------------------------------
text4 = 'result = qux(1, 2, 3)'
result4 = _find_call_sites(text4, LANG_KEY, KNOWN_STEMS, KEYWORDS)

# -------------------------------------------------------------------
# Test 5: Mixed — string with foo() and real helper() call
# Expected: foo NOT found, helper FOUND
# -------------------------------------------------------------------
text5 = 'print("foo() here") + helper(x)'
result5 = _find_call_sites(text5, LANG_KEY, KNOWN_STEMS, KEYWORDS)

# -------------------------------------------------------------------
# Test 6: Identifier inside f-string
# Expected: foo should NOT be found
# -------------------------------------------------------------------
text6 = 'x = f"calling foo() inside f-string"'
result6 = _find_call_sites(text6, LANG_KEY, KNOWN_STEMS, KEYWORDS)

# -------------------------------------------------------------------
# Test 7: Identifier inside raw string
# Expected: foo should NOT be found
# -------------------------------------------------------------------
text7 = 'x = r"foo() inside raw string"'
result7 = _find_call_sites(text7, LANG_KEY, KNOWN_STEMS, KEYWORDS)

# -------------------------------------------------------------------
# Evaluate all results
# -------------------------------------------------------------------
bugs_found = []

# Test 1: foo in single-quoted string
if "foo" in result1:
    bugs_found.append("foo captured inside single-quoted string")

# Test 2: bar in double-quoted string
if "bar" in result2:
    bugs_found.append("bar captured inside double-quoted string")

# Test 3: baz in triple-quoted string
if "baz" in result3:
    bugs_found.append("baz captured inside triple-quoted string")

# Test 4: qux in real call (should be found)
if "qux" not in result4:
    bugs_found.append("qux NOT captured in real function call (false negative)")

# Test 5: foo in string + helper outside
if "foo" in result5:
    bugs_found.append("foo captured inside string in mixed test")
if "helper" not in result5:
    bugs_found.append("helper NOT captured in real call (false negative in mixed test)")

# Test 6: foo in f-string
if "foo" in result6:
    bugs_found.append("foo captured inside f-string")

# Test 7: foo in raw string
if "foo" in result7:
    bugs_found.append("foo captured inside raw string")

if bugs_found:
    print(f'CONFIRMED — bugs found: {"; ".join(bugs_found)}')
else:
    print('NOT CONFIRMED — all string/character literal identifiers correctly excluded; real call sites correctly detected')
    print(f'  result1 (single-quoted): {result1}')
    print(f'  result2 (double-quoted): {result2}')
    print(f'  result3 (triple-quoted): {result3}')
    print(f'  result4 (real call):     {result4}')
    print(f'  result5 (mixed):         {result5}')
    print(f'  result6 (f-string):      {result6}')
    print(f'  result7 (raw string):    {result7}')
