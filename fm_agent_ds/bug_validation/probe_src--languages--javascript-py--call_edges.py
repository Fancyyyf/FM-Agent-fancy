"""Probe for bug src--languages--javascript-py--call_edges.

Bug: call_edges() in src/languages/javascript.py calls
CodeGraphExtractor.from_proj_dir(proj_dir) without wrapping it in a try-except
block. If from_proj_dir raises an exception during initialization (e.g.,
IndexError, JSONDecodeError), the exception propagates to the caller instead
of being caught and returning None.

The specification requires that ALL initialization failures result in
returning None — not propagating an exception. The code only handles the case
where from_proj_dir returns None (codegraph index absent), but does not
handle the case where from_proj_dir raises.
"""

import os
import sys
import tempfile
from unittest.mock import patch


def main() -> int:
    tmpdir = tempfile.mkdtemp(prefix="probe_javascript_")
    try:
        from src.languages.javascript import call_edges

        # Monkey-patch CodeGraphExtractor.from_proj_dir to simulate an
        # initialization failure.  The specification requires that any
        # exception raised during initialization causes call_edges to return
        # None.  The actual code propagates the exception.
        with patch(
            "src.languages.codegraph.CodeGraphExtractor.from_proj_dir",
            side_effect=IndexError(
                "Simulated codegraph index initialization failure"
            ),
        ):
            result = call_edges(tmpdir)
            # If we reach here, call_edges() returned a value instead of
            # raising — the bug was NOT triggered.
            print(
                "NOT CONFIRMED — call_edges() returned {!r} instead of "
                "propagating IndexError. The code correctly handled the "
                "initialization failure (returned None as spec requires).".format(
                    result
                )
            )
        return 0

    except IndexError as exc:
        # Bug CONFIRMED: call_edges() propagated the exception from
        # from_proj_dir instead of catching it and returning None.
        print(
            "CONFIRMED — call_edges() propagated IndexError from "
            "CodeGraphExtractor.from_proj_dir instead of catching it and "
            "returning None. The specification requires that ALL "
            "initialization failures cause call_edges() to return None. "
            "Raised: {}".format(exc)
        )
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
