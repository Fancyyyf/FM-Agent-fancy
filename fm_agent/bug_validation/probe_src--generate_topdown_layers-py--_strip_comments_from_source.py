import sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot')

try:
    from src.generate_topdown_layers import _strip_comments_from_source
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)


def build_hash_comment_expected(text):
    """Build expected output for hash-style comment: #...→spaces, \\n preserved."""
    expected = []
    in_comment = False
    for ch in text:
        if not in_comment and ch == '#':
            in_comment = True
            expected.append(' ')
        elif in_comment:
            expected.append('\n' if ch == '\n' else ' ')
        else:
            expected.append(ch)
    return ''.join(expected)


def build_string_hash_expected(text):
    """Simple expected: double-quoted strings→spaces, # comment→spaces."""
    expected = []
    in_string = False
    in_comment = False
    for ch in text:
        if not in_string and not in_comment and ch == '#':
            in_comment = True
            expected.append(' ')
        elif in_comment:
            expected.append('\n' if ch == '\n' else ' ')
        elif not in_string and ch == '"':
            in_string = True
            expected.append(' ')
        elif in_string and ch == '"':
            in_string = False
            expected.append(' ')
        elif in_string:
            expected.append(' ')
        else:
            expected.append(ch)
    return ''.join(expected)


def build_doubleslash_expected(text):
    """Build expected output for // comments→spaces."""
    expected = []
    i = 0
    in_comment = False
    while i < len(text):
        ch = text[i]
        if not in_comment and ch == '/' and i + 1 < len(text) and text[i + 1] == '/':
            in_comment = True
            expected.append(' ')
            expected.append(' ')
            i += 2
            continue
        if in_comment:
            expected.append('\n' if ch == '\n' else ' ')
        else:
            expected.append(ch)
        i += 1
    return ''.join(expected)


def build_blockcomment_expected(text):
    """Build expected output for /* */ block comments→spaces."""
    expected = []
    i = 0
    in_comment = False
    while i < len(text):
        ch = text[i]
        if not in_comment and ch == '/' and i + 1 < len(text) and text[i + 1] == '*':
            in_comment = True
            expected.append(' ')
            expected.append(' ')
            i += 2
            continue
        if in_comment and ch == '*' and i + 1 < len(text) and text[i + 1] == '/':
            expected.append(' ')
            expected.append(' ')
            in_comment = False
            i += 2
            continue
        if in_comment:
            expected.append('\n' if ch == '\n' else ' ')
        else:
            expected.append(ch)
        i += 1
    return ''.join(expected)


# ── Test 1: Python hash comment ──
text1 = "x = 1  # this is a comment\n"
result1 = _strip_comments_from_source(text1, "python")
expected1 = build_hash_comment_expected(text1)
ok1 = result1 == expected1 and len(result1) == len(text1)

print("=== Test 1: Python hash comment ===")
print(f"  PASS: {ok1}")
print(f"  Input:    {text1!r}")
print(f"  Result:   {result1!r}")
print(f"  Expected: {expected1!r}")

# ── Test 2: string literal + hash comment ──
text2 = 'print("hello")  # greet\n'
result2 = _strip_comments_from_source(text2, "python")
expected2 = build_string_hash_expected(text2)
ok2 = result2 == expected2 and len(result2) == len(text2)

print("\n=== Test 2: Python string + comment ===")
print(f"  PASS: {ok2}")
print(f"  Input:    {text2!r}")
print(f"  Result:   {result2!r}")
print(f"  Expected: {expected2!r}")

# ── Test 3: C++ // comment ──
text3 = "int x = 1; // comment\n"
result3 = _strip_comments_from_source(text3, "cpp")
expected3 = build_doubleslash_expected(text3)
ok3 = result3 == expected3 and len(result3) == len(text3)

print("\n=== Test 3: C++ // comment ===")
print(f"  PASS: {ok3}")
print(f"  Input:    {text3!r}")
print(f"  Result:   {result3!r}")
print(f"  Expected: {expected3!r}")

# ── Test 4: C block comment ──
text4 = "int /* block */ x;\n"
result4 = _strip_comments_from_source(text4, "cpp")
expected4 = build_blockcomment_expected(text4)
ok4 = result4 == expected4 and len(result4) == len(text4)

print("\n=== Test 4: C block comment ===")
print(f"  PASS: {ok4}")
print(f"  Input:    {text4!r}")
print(f"  Result:   {result4!r}")
print(f"  Expected: {expected4!r}")

# ── Test 5: Unknown lang # (NOT a comment) ──
text5 = "code # not a comment for unknown lang\n"
result5 = _strip_comments_from_source(text5, "unknown_lang")
expected5 = text5  # per spec, default is // so # unchanged
ok5 = result5 == expected5 and len(result5) == len(text5)

print("\n=== Test 5: Unknown lang # (NOT comment) ===")
print(f"  PASS: {ok5}")
print(f"  Input:    {text5!r}")
print(f"  Result:   {result5!r}")
print(f"  Expected: {expected5!r}")

# ── Test 6 (edge case): backslash escape inside string ──
text6 = 'print("hello\\"world") # comment\n'
result6 = _strip_comments_from_source(text6, "python")
# Verify: escaped quote inside string should be masked, comment masked
ok6 = len(result6) == len(text6) and result6.find('"') == -1 and result6.find('#') == -1

print("\n=== Test 6: Backslash escape in string + comment ===")
print(f"  PASS: {ok6}")
print(f"  Input:    {text6!r}")
print(f"  Result:   {result6!r}")

# ── Summary ──
results = {
    "Python # comment": ok1,
    "String + # comment": ok2,
    "C++ // comment": ok3,
    "Block /* */ comment": ok4,
    "Unknown lang #": ok5,
    "Backslash escape": ok6,
}

print("\n" + "=" * 60)
all_pass = all(results.values())
for name, passed in results.items():
    status = "PASS" if passed else "FAIL"
    print(f"  {name}: {status}")

if all_pass:
    print("\nBug NOT CONFIRMED: function correctly masks both string literals AND comments.")
    print('NOT CONFIRMED')
else:
    print("\nBug CONFIRMED: at least one test case showed incorrect behavior.")
    print('CONFIRMED')
