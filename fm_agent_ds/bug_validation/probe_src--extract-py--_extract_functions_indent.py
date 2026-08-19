r"""Probe script for bug: src--extract-py--_extract_functions_indent

Bug: _extract_functions_indent uses regex r'\)\s*(:|->)' to detect multi-line
signature continuations, missing continuation lines that don't start with ')'.
When a parameter line at the same indentation does not match, the function span
is truncated.

Counterexample:
    def foo(a,
    b):
        pass

The 'b):' line has indent 0 (same as def), but doesn't match the continuation
regex, so the function span becomes [0,0] instead of [0,2].
"""

import os
import sys
import tempfile

# Ensure the src package is importable from the repo root
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(_REPO_ROOT, "pyproject.toml")):
    parent = os.path.dirname(_REPO_ROOT)
    if parent == _REPO_ROOT:
        print("ERROR: Could not find repo root")
        sys.exit(1)
    _REPO_ROOT = parent

sys.path.insert(0, _REPO_ROOT)


def main():
    # Counterexample that triggers the bug:
    # 'b):' at indent 0 does NOT start with ')', so the continuation regex
    # fails and the function span is truncated.
    counterexample = """def foo(a,
b):
    pass
"""

    tmpdir = None
    try:
        tmpdir = tempfile.mkdtemp(prefix="probe_extract_indent_")
        test_file = os.path.join(tmpdir, "test_func.py")
        with open(test_file, "w") as f:
            f.write(counterexample)

        from src.extract import extract_functions_from_file

        results = extract_functions_from_file(test_file, "python")

        if not results:
            print("CONFIRMED — no functions extracted from valid Python file")
            return 0

        name, source = results[0]

        # The spec says the span should cover the entire function body.
        # 'pass' is in the function body — it should be present in the
        # extracted source if the span is correct.
        if "pass" not in source:
            print(
                "CONFIRMED — function body truncated."
                f" Extracted source: {source!r}"
            )
            return 0
        else:
            print(
                "NOT CONFIRMED — full function body present."
                f" Extracted source: {source!r}"
            )
            return 0

    except ImportError as e:
        print(f"ERROR: Import failed — {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        if tmpdir is not None:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
