# Bug Report: _strip_comments_from_source

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/generate_topdown_layers-py/_strip_comments_from_source.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a string of the same length as text (same number of characters)
  - Every character position that lies within a comment region in the input
    is replaced with a space character (' ') in the output, where a comment
    region is defined according to the language-specific comment syntax:
      * When the language configuration for lang_key has comment_prefix "#":
        a comment region spans from a '#' character (that is not inside a
        string literal) to the end of the same line, including the '#'.
      * When the language configuration for lang_key has comment_prefix
        "//" (or when lang_key is not found, defaulting to "//"): a line-
        comment region spans from "//" to end of line; a block-comment
        region spans from "/*" to the next "*/" (non-nesting). The opening
        and closing markers are part of the comment region.
      * Characters within comment regions that are newline characters (\n)
        are never replaced; they remain unchanged.
  - Every character position that lies within a string-literal region in
    the input is replaced with a space character in the output. A string-
    literal region includes its delimiting quote characters and all
    characters between them. Delimiters may be:
      * single-quote ('...'), double-quote ("..."),
      * triple-single-quote ('''...'''), triple-double-quote ("""...""").
    Backslash-escape handling: a backslash (\) and the immediately
    following character (if any) are treated as non-delimiting and are
    replaced with spaces; if the following character is a newline, only
    the backslash is replaced, the newline is preserved.
  - Any character position that is neither within a comment region nor
    within a string-literal region is preserved unchanged (including
    whitespace, punctuation, identifiers, keywords, etc.).
  - The order and positions of non-replaced characters are unchanged;
    th...

---

### Actual Behavior

After the code block finishes execution, the input source text has been processed to mask all string literals (single-quoted, double-quoted, and triple-quoted strings, with backslash-escaped characters handled) by replacing their characters with spaces. The variable 'result' is a list of characters of the same length as 'text'. For every index j, if the j-th character in the original 'text' lies inside a string literal (according to the quoting rules of the language and the processing logic), then result[j] equals a space ' '; otherwise result[j] equals text[j]. The index 'i' is equal to len(result), indicating that the scanning loop has completed. The variables 'lang_cfg', 'comment_prefix', and 'is_hash_comment' hold the derived language configuration. Formally: len(result) = len(text) AND (forall j in [0, len(text)-1] : (in_string_literal(text, j) -> result[j] = ' ') and (not in_string_literal(text, j) -> result[j] = text[j])) AND i = len(result) AND is_hash_comment = (comment_prefix = '#') AND comment_prefix = (LANG_CONFIG.get(lang_key, {})).get('comment_prefix', '//') AND lang_cfg = LANG_CONFIG.get(lang_key, {})

---

## Code Evidence

Line 59-64 (hash comment handling) are either not executed or do not affect the behavior described by A. According to A, the code does not mask comments, violating the requirement in B that comment regions be replaced with spaces.

---

## Trigger Condition

Condition A states that only string literals are masked; characters not in string literals are preserved unchanged. Specification B requires that comment regions also be masked (replaced with spaces). Any input containing a comment (e.g., '# comment\n') will result in the comment characters being left as-is by A, whereas B requires them to be spaces. This is a direct violation.

---

## How to trigger the bug

The verification tool's formal analysis incorrectly claimed that the function only masks string literals and not comments. Empirical testing with 6 distinct test cases (Python `#` comments, string literals with comments, C++ `//` comments, C `/* */` block comments, unknown language key, and backslash-escaped strings with comments) shows the function **correctly masks both string literals AND comment regions** in all cases.

The tool's post-condition analysis appears to have missed the comment-handling code paths at lines 184-190 (hash comments), 192-197 (C-style line comments), and 199-213 (block comments) in the source file, which are all executed and function correctly.

### Inputs

| Parameter | Value |
|-----------|-------|
| text | `"x = 1  # this is a comment\n"` |
| lang_key | `"python"` |

### Expected (spec-correct) Output

`"x = 1                     \n"` (code preserved, comment `# this is a comment` replaced with spaces, newline preserved)

### Actual (buggy) Output

The actual output matches the spec-correct output exactly. The `#` and all subsequent non-newline characters in the comment are replaced with spaces.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot')
from src.generate_topdown_layers import _strip_comments_from_source

# Python hash comment
result = _strip_comments_from_source("x = 1  # this is a comment\n", "python")
print(repr(result))
# actual output: 'x = 1                     \n'
# expected output: 'x = 1                     \n' (comment characters → spaces)
```

---

## Probe Script

```python
import sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot')

try:
    from src.generate_topdown_layers import _strip_comments_from_source
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)


def build_hash_comment_expected(text):
    """Build expected output for hash-style comment: #...→spaces, \n preserved."""
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
```

### Probe Output

```
=== Test 1: Python hash comment ===
  PASS: True
  Input:    'x = 1  # this is a comment\n'
  Result:   'x = 1                     \n'
  Expected: 'x = 1                     \n'

=== Test 2: Python string + comment ===
  PASS: True
  Input:    'print("hello")  # greet\n'
  Result:   'print(       )         \n'
  Expected: 'print(       )         \n'

=== Test 3: C++ // comment ===
  PASS: True
  Input:    'int x = 1; // comment\n'
  Result:   'int x = 1;           \n'
  Expected: 'int x = 1;           \n'

=== Test 4: C block comment ===
  PASS: True
  Input:    'int /* block */ x;\n'
  Result:   'int             x;\n'
  Expected: 'int             x;\n'

=== Test 5: Unknown lang # (NOT comment) ===
  PASS: True
  Input:    'code # not a comment for unknown lang\n'
  Result:   'code # not a comment for unknown lang\n'
  Expected: 'code # not a comment for unknown lang\n'

=== Test 6: Backslash escape in string + comment ===
  PASS: True
  Input:    'print("hello\\"world") # comment\n'
  Result:   'print(              )          \n'

============================================================
  Python # comment: PASS
  String + # comment: PASS
  C++ // comment: PASS
  Block /* */ comment: PASS
  Unknown lang #: PASS
  Backslash escape: PASS

Bug NOT CONFIRMED: function correctly masks both string literals AND comments.
NOT CONFIRMED
```
