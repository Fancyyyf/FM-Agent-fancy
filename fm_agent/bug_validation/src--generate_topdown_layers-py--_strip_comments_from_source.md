# Bug Report: _strip_comments_from_source

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/generate_topdown_layers-py/_strip_comments_from_source.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a string of the same length as text
  - Every character position that lies within a comment region in the input
    is replaced with a space character (' ') in the output, where a comment
    region is defined according to the language-specific comment syntax:
      * When the language configuration for lang_key has comment_prefix "#":
        a comment region spans from a '#' character (that is not inside a
        string literal) to the end of the same line
      * When the language configuration for lang_key has comment_prefix
        "//": a line-comment region spans from "//" to end of line; a
        block-comment region spans from "/*" to the next "*/" (non-nesting)
      * When lang_key is not found in the language configuration, "//"
        comment syntax is assumed
  - Every character position that lies within a string-literal region in
    the input is replaced with a space character in the output, where a
    string-literal region is delimited by matching single-quote ('...'),
    double-quote ("..."), triple-single-quote ('''...'''), or
    triple-double-quote ("""...""") markers, with standard backslash-escape
    handling (an escaped character is treated as non-delimiting)
  - Newline characters (\n) are never replaced; they are preserved at their
    original positions
  - Any character position that is neither within a comment region nor
    within a string-literal region is preserved unchanged, including
    whitespace, punctuation, identifiers, keywords, and all other source
    tokens
  - Character positions are preserved in the sense that the byte length of
    the output string equals the character length of the input text, and
    non-removed characters remain at their original indices

---

### Actual Behavior

The function returns a string `out` such that |out| == |text| and for every index i (0 <= i < |text|), out[i] = ' ' if position i lies inside a comment region (as defined by the language configuration for `lang_key`, defaulting to `//` line comments, with correct handling of block comments when configured) and is **not** inside a string literal; otherwise out[i] = text[i]. String literals are recognised by singlequote (`'`), doublequote (`"`), or triplequote (`'''` or `"""`) delimiters, with backslash escaping treated properly so that any commentlike sequence inside a literal is ignored. The original arguments `text` and `lang_key` are not mutated.

Formally, let `InComment(i, text, lang_key)` be true iff character `i` belongs to a comment according to the rules derived from `LANG_CONFIG[lang_key]` (with the specified defaults), and let `InStringLiteral(i, text)` be true iff `i` is inside a string literal respecting the given quoting and escaping rules. Then:

  out = "".join( [ ( ' ' if InComment(i, text, lang_key) AND NOT InStringLiteral(i, text) else text[i] ) for i in range(len(text)) ] )

---

## Code Evidence

Line 41: while i < len(result):
Line 44: result[i] = " "
Line 46: result[i + 1] = " "
Line 51: result[i] = " "
Line 55: result[i] = " "

---

## Trigger Condition

Condition A states that positions inside string literals are not replaced (out[i] = text[i] when InStringLiteral is true). Specification B requires that every position inside a string literal be replaced with a space. For the given counterexample, A outputs '"hello"' (preserving literal contents), while B requires '       ' (all seven positions replaced by spaces).

---

## How to trigger the bug

The reported bug claims that string-literal characters are preserved rather than masked with spaces. However, inspection of the source code and empirical testing both show that the function correctly replaces all string-literal characters with spaces.

### Inputs

| Parameter | Value |
|-----------|-------|
| text | `'"hello"'` |
| lang_key | `"python"` |

### Expected (spec-correct) Output

`'       '` (7 spaces — all positions masked because the entire input is a string literal)

### Actual (buggy) Output

`'       '` (7 spaces — the code correctly masks all characters)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.generate_topdown_layers import _strip_comments_from_source

# The bug report claims '"hello"' should NOT become all spaces,
# but it does become all spaces, matching the spec.
result = _strip_comments_from_source('"hello"', "python")
print(repr(result))
# actual (buggy) output: '       '
# expected (correct) output: '       '
```

---

## Probe Script

```python
import sys
import os

# probe_*.py -> fm_agent/bug_validation/ -> fm_agent/ -> repo_root
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.generate_topdown_layers import _strip_comments_from_source

    bug_found = False  # True = bug confirmed

    # Test 1: Pure string literal - spec says all chars must be spaces
    inp = '"hello"'
    actual = _strip_comments_from_source(inp, "python")
    expected = " " * len(inp)
    ok = actual == expected
    print(f"Test 1 (pure string) - {inp!r} -> {actual!r}, expect {expected!r}: {'PASS' if ok else 'FAIL'}")
    if not ok:
        bug_found = True

    # Test 2: Code+string - spec says string chars masked, code chars preserved
    inp = 'x = "hi"'
    actual = _strip_comments_from_source(inp, "python")
    expected = "x = " + " " * 4  # "hi" (4 chars) masked
    ok = actual == expected
    print(f"Test 2 (code+string) - {inp!r} -> {actual!r}, expect {expected!r}: {'PASS' if ok else 'FAIL'}")
    if not ok:
        bug_found = True

    # Test 3: Code+string+comment - spec: string & comment chars masked, code preserved
    inp = 'x = "hi"  # note'
    actual = _strip_comments_from_source(inp, "python")
    expected = "x = " + " " * 4 + "  " + " " * 6
    ok = actual == expected
    print(f"Test 3 (code+string+comment) - {inp!r} -> {actual!r}, expect {expected!r}: {'PASS' if ok else 'FAIL'}")
    if not ok:
        bug_found = True

    # Test 4: Triple-quoted string - spec says all chars inside triple quotes masked
    inp = "x = '''hello'''"
    actual = _strip_comments_from_source(inp, "python")
    expected = "x = " + " " * 11
    ok = actual == expected
    print(f"Test 4 (triple-quoted) - {inp!r} -> {actual!r}, expect {expected!r}: {'PASS' if ok else 'FAIL'}")
    if not ok:
        bug_found = True

    # Test 5: C-style with string and line comment (lang_key="cpp")
    inp = 'const char* s = "hello"; // note'
    actual = _strip_comments_from_source(inp, "cpp")
    expected = "const char* s = " + " " * 7 + "; " + " " * 7
    ok = actual == expected
    print(f"Test 5 (C-style) - {inp!r} -> {actual!r}, expect {expected!r}: {'PASS' if ok else 'FAIL'}")
    if not ok:
        bug_found = True

    # Test 6: String with escaped quote - spec says it's all one string, all masked
    inp = 'x = "he\\"llo"'
    actual = _strip_comments_from_source(inp, "python")
    expected = "x = " + " " * 9  # "he\"llo" = 9 chars
    ok = actual == expected
    print(f"Test 6 (escaped quote) - {inp!r} -> {actual!r}, expect {expected!r}: {'PASS' if ok else 'FAIL'}")
    if not ok:
        bug_found = True

    # Test 7: Comment only, no string - spec says comment chars masked
    inp = "x = 1  # comment"
    actual = _strip_comments_from_source(inp, "python")
    expected = "x = 1  " + " " * 9
    ok = actual == expected
    print(f"Test 7 (comment only) - {inp!r} -> {actual!r}, expect {expected!r}: {'PASS' if ok else 'FAIL'}")
    if not ok:
        bug_found = True

    if bug_found:
        print("\nCONFIRMED -- string literal characters were NOT correctly masked with spaces")
    else:
        print("\nNOT CONFIRMED -- all tests pass: string literal characters ARE correctly masked with spaces")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
Test 1 (pure string) - '"hello"' -> '       ', expect '       ': PASS
Test 2 (code+string) - 'x = "hi"' -> 'x =     ', expect 'x =     ': PASS
Test 3 (code+string+comment) - 'x = "hi"  # note' -> 'x =             ', expect 'x =             ': PASS
Test 4 (triple-quoted) - "x = '''hello'''" -> 'x =            ', expect 'x =            ': PASS
Test 5 (C-style) - 'const char* s = "hello"; // note' -> 'const char* s =        ;        ', expect 'const char* s =        ;        ': PASS
Test 6 (escaped quote) - 'x = "he\\"llo"' -> 'x =          ', expect 'x =          ': PASS
Test 7 (comment only) - 'x = 1  # comment' -> 'x = 1           ', expect 'x = 1           ': PASS

NOT CONFIRMED -- all tests pass: string literal characters ARE correctly masked with spaces
```
