import os
import sys
import tempfile
from pathlib import Path

try:
    from src.generate_topdown_layers import _file_to_fqn

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directory: extracted_functions/src::engine/loader-cpp/
        # "src::engine" contains "::" — spec says no segment may contain "::"
        extracted_base = os.path.join(tmpdir, "extracted_functions")
        buggy_dir = os.path.join(extracted_base, "src::engine", "loader-cpp")
        os.makedirs(buggy_dir, exist_ok=True)

        filepath = os.path.join(buggy_dir, "loadData.cpp")
        with open(filepath, "w") as f:
            f.write("// dummy\n")

        actual = _file_to_fqn(filepath, tmpdir)

        # Reconstruct what the function internally computes as "parts"
        # (the actual FQN segments before joining with "::")
        rel = os.path.relpath(filepath, extracted_base)
        stem, _ = os.path.splitext(rel)
        parts = Path(stem).parts

        # Spec: "Each segment ... containing no '::' substrings"
        # The segments (parts from Path(stem).parts) must not contain "::"
        spec_violated = any("::" in part for part in parts)
        violating_parts = [p for p in parts if "::" in p]

        if spec_violated:
            print(
                f"CONFIRMED -- actual FQN: {actual!r} | "
                f"segment(s) containing '::': {violating_parts} | "
                f"spec requires no segment to contain '::'"
            )
        else:
            print(
                f"NOT CONFIRMED -- all path parts are '::'-free | "
                f"parts: {list(parts)!r} | "
                f"actual FQN: {actual!r}"
            )

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
