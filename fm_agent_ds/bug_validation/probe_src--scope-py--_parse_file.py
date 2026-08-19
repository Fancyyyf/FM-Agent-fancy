#!/usr/bin/env python3
"""Probe script for bug src--scope-py--_parse_file.

Tests whether _parse_file correctly preserves class information
for a .py file containing a class but no top-level functions.
"""
import sys
import tempfile
from pathlib import Path

# Ensure the repo root is on sys.path so that 'src.scope' (and its
# relative imports like .extract) resolve correctly.
_repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_repo_root))

# Also ensure src.__init__.py is importable by adding the repo root.
# When run via `python3 fm_agent/bug_validation/probe_...py`, the
# script dir is on sys.path[0] but not the repo root.

try:
    from src.scope import _parse_file
except Exception as exc:
    print(f"ERROR: cannot import _parse_file: {exc}")
    sys.exit(1)

# ── Probe: .py file with a class but no top-level functions ──

# FM-Agent self-validation guard: all test fixtures live in a fresh
# temporary directory, never in the active-run fm_agent/ tree.
with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    test_file = tmp_path / "test_class_only.py"
    test_file.write_text("""
class MyExampleClass:
    \"\"\"A test class with no standalone functions in the module.\"\"\"
    pass

class AnotherClass:
    \"\"\"Second class, also no functions.\"\"\"
    pass
""", encoding="utf-8")

    try:
        result = _parse_file(test_file)
    except Exception as exc:
        print(f"ERROR: _parse_file raised: {exc}")
        sys.exit(1)

    funcs, source_lines, classes = result

    # ── Oracle ──
    # Spec claim: when AST parsing succeeds, funcs is a list (possibly empty),
    # source_lines is a list of strings, classes is a list (possibly empty).
    # The bug report claims that funcs can be None when there are no functions,
    # causing an incorrect fallback to _parse_generic_file and loss of classes.
    #
    # Expected (correct) behavior: funcs = [] (empty list, not None),
    # classes = [{'name': 'MyExampleClass', ...}, {'name': 'AnotherClass', ...}]

    bug_hit = (
        funcs is None
        or classes is None
        or (funcs is not None and classes is not None and len(classes) != 2)
    )

    if bug_hit:
        print(
            f"CONFIRMED — Bug reproduced: funcs={funcs!r}, "
            f"classes={classes!r}"
        )
        print(f"  funcs is None: {funcs is None}")
        print(f"  classes is None: {classes is None}")
        if classes is not None:
            print(f"  len(classes): {len(classes)}")
    else:
        class_names = [c['name'] for c in classes]
        print(
            f"NOT CONFIRMED — Class info correctly preserved. "
            f"funcs={funcs!r} (type={type(funcs).__name__}), "
            f"classes={class_names}"
        )
        print(f"  source_lines count: {len(source_lines)}")
