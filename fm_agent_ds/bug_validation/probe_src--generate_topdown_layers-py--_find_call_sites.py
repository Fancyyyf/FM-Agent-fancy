import sys
import os
import tempfile

# Use a fresh temporary directory for all probe workspace
tmpdir = tempfile.mkdtemp(prefix="bug_probe_find_call_sites_")
os.chdir("/home/fancy/Projects_Vault/FM-Agent")

try:
    from src.generate_topdown_layers import _find_call_sites

    # The bug: _strip_comments_from_source only masks content inside
    # single-quote (') and double-quote (") strings. Template literals
    # (backtick strings) in JavaScript/TypeScript and raw strings in Go
    # use backticks, which are not recognized as string delimiters.
    # As a result, _find_call_sites matches identifiers that appear
    # exclusively inside template literals.

    # Test: JavaScript template literal containing 'my_function()'
    text = """\
const msg = `calling my_function() now`;
const other = `my_function(42)`;
"""
    lang_key = "javascript"
    known_stems = {"my_function"}
    keywords = set()

    actual = _find_call_sites(text, lang_key, known_stems, keywords)
    expected = set()  # Spec: should be empty — 'my_function' appears only inside template literals, not in a syntactic calling position

    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
