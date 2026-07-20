"""Probe for _extracted_func_dir: verify that the last dot in a basename is always
replaced with a hyphen, including when it is the first character (e.g. '.gitignore').

Bug claim: when the basename starts with a dot and has no other dots,
rfind('.') returns 0, but the code only replaces when last_dot > 0.
So '.gitignore' remains '.gitignore' instead of becoming '-gitignore'.

Spec claim (from [SPEC] post-condition):
  "the last dot in the source file basename is replaced with a hyphen"
"""
import sys
import os

_script_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(os.path.dirname(_script_dir))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

error_occurred = False
error_msg = ""

try:
    from src.incremental_reasoner import _extracted_func_dir

    extracted_base = "/fake/extracted_functions"
    src_rel = ".gitignore"

    actual = _extracted_func_dir(extracted_base, src_rel)

    # Expected: basename ".gitignore" -> "-gitignore" (last dot at index 0 replaced)
    # So the full path should end with "-gitignore"
    expected_tail = "gitignore"   # we just check the tail contains, not full path
    # Actually, expected: basename after transformation is "-gitignore"
    # So os.path.basename(actual) should be "-gitignore"
    actual_basename = os.path.basename(actual)

    # Spec says: the last dot is replaced with a hyphen
    # For ".gitignore", that means: "" + "-" + "gitignore" = "-gitignore"
    expected_basename = "-gitignore"

    passed = actual_basename != expected_basename  # True -> bug reproduced (mismatch)

    if passed:
        print(
            f"CONFIRMED — actual basename: {actual_basename!r} | "
            f"expected basename (per spec): {expected_basename!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — actual basename matched expected: {actual_basename!r}"
        )

except Exception as exc:
    error_occurred = True
    error_msg = str(exc)
    print(f"ERROR: {type(exc).__name__}: {exc}")
