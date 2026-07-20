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
