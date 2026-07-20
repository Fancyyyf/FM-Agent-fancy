import sys
import os

# Ensure the repo root is on sys.path so 'src' can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.languages.codegraph import CodeGraphExtractor

    ext = CodeGraphExtractor(".codegraph/codegraph.db")
    result = ext.get_functions_by_file("python", proj_dir=None)

    if not result:
        print("NOT CONFIRMED — empty result, cannot test")
        sys.exit(0)

    # Specification requires absolute file paths.
    # The bug is that when proj_dir=None, file_path from DB is used as-is (relative).
    non_absolute = [k for k in result if not os.path.isabs(k)]

    if non_absolute:
        print(f"CONFIRMED — {len(non_absolute)} key(s) are relative instead of absolute: {non_absolute[0]!r}")
    else:
        print("NOT CONFIRMED — all keys are absolute")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
