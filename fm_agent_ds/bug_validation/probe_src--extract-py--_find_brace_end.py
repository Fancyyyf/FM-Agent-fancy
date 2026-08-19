"""Probe script for bug: _find_brace_end incorrectly treats '}' inside multi-line
block comments as a closing brace, causing premature function end detection."""

import sys
import os
import tempfile


def run_probe():
    # Create temp workspace (NOT fm_agent/ directory)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a C source file with a multi-line block comment containing '}'
        c_src = os.path.join(tmpdir, "test.c")
        with open(c_src, "w") as f:
            f.write('void test_func() {\n')
            f.write('    /*\n')
            f.write('     * multi-line block comment\n')
            f.write('     * containing } inside comment\n')
            f.write('     */\n')
            f.write('    int x = 42;\n')
            f.write('}\n')

        try:
            from src.extract import extract_functions_from_file
            funcs = extract_functions_from_file(c_src, "c")
        except Exception as e:
            print(f"ERROR: import or extraction failed: {e}")
            sys.exit(1)

        if not funcs:
            print("ERROR: No functions extracted from test file")
            sys.exit(1)

        name, source = funcs[0]

        # If the bug is present, _find_brace_end will return the line with '}'
        # inside the block comment. The extracted source will be truncated,
        # missing the "int x = 42" line and the real closing brace.
        #
        # If the function works correctly (per spec), it should skip the
        # multi-line block comment and match the real closing brace, so the
        # source includes all lines.

        buggy_truncation = "int x = 42" not in source
        # Spec claims: multi-line block comment should be fully skipped.
        # Expected (correct): source contains the full function body.
        expected = "int x = 42" in source
        actual = "int x = 42" in source if not buggy_truncation else False

        # Bug confirmed when: the function is truncated (missing body content)
        # that should be there according to the spec.
        passed = buggy_truncation  # True → bug reproduced

        if passed:
            # Show what we got vs what we expected
            print(
                f"CONFIRMED — extracted source truncated at comment brace."
                f" actual source: {source!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — function correctly extracted."
                f" source: {source!r}"
            )


if __name__ == "__main__":
    run_probe()
