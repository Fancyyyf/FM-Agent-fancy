r"""Probe for _codegraph_legacy_coverage: _bare_function_name incorrectly strips dedup suffixes.

Bug: _bare_function_name (src/incremental_reasoner.py:216) uses re.sub(r"_\d+$", "", bare)
which strips trailing dedup suffixes like "_1" from function names. This causes
_codegraph_legacy_coverage to return True (covered) even when the legacy extractor
produces a name like "my_func_1" and CodeGraph only has "my_func" —
they should be treated as different functions per the spec.

Scenario:
- Legacy extractor reports: my_func_1 (with dedup suffix)
- CodeGraph has: my_func (no suffix, identical body)
- _bare_function_name("my_func_1") → "my_func"
- _bare_function_name("my_func") → "my_func"
- Names falsely match → returns True (should be False)
"""
import sys
import os
import tempfile
import shutil

# Ensure repo root is on path so the 'src' package and 'config' module
# are importable when we run from the repo root.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

TMPDIR = tempfile.mkdtemp(prefix="bug_probe_")
PROBE_FILE = os.path.join(TMPDIR, "test.py")

result = None
error_msg = None
confirmed = False

try:
    # Create a real file so os.path.exists() passes.
    with open(PROBE_FILE, "w") as f:
        f.write("def my_func():\n    pass\n")

    # Import the module under test.
    # Importing incremental_reasoner pulls in config and other deps;
    # we assume the dev environment has them available.
    import src.incremental_reasoner as mod

    # Save original extract_functions_from_file for restoration.
    _original_extract = mod.extract_functions_from_file

    # Mock: return a legacy function WITH a dedup suffix that has the
    # same body as the CodeGraph function (so the source comparison
    # would also pass if the name comparison erroneously passes).
    def _mock_extract(filepath, lang_key):
        return [("my_func_1", "def my_func():\n    pass\n")]

    mod.extract_functions_from_file = _mock_extract

    # CodeGraph data: has "my_func" WITHOUT the "_1" suffix.
    codegraph_functions = {
        "test.py": {
            "my_func": "def my_func():\n    pass\n",
        }
    }
    file_languages = {PROBE_FILE: "python"}

    # Call the function under test.
    result = mod._codegraph_legacy_coverage(TMPDIR, codegraph_functions, file_languages)

    # Restore the original.
    mod.extract_functions_from_file = _original_extract

    # Determine the normalized key the function would have used.
    rel_key = mod._normalized_relative_path(TMPDIR, PROBE_FILE)
    actual = result.get(rel_key)

    # Per the spec ("unqualified function name" should NOT strip dedup suffixes),
    # "my_func_1" and "my_func" are different functions, so CodeGraph does NOT
    # cover this legacy function → expected is False.
    expected = False

    # Bug is confirmed if the code returns True (wrong) instead of False.
    confirmed = (actual == True)

    if confirmed:
        print("CONFIRMED — actual: %s | expected: %s (legacy 'my_func_1' should NOT match CodeGraph 'my_func')" % (actual, expected))
    else:
        print("NOT CONFIRMED — actual: %s | expected: %s" % (actual, expected))

except Exception as e:
    error_msg = str(e)
    print("ERROR: %s" % error_msg)
    # Also print a traceback for diagnostic purposes.
    import traceback
    traceback.print_exc()

finally:
    # Clean up temp directory.
    shutil.rmtree(TMPDIR, ignore_errors=True)
