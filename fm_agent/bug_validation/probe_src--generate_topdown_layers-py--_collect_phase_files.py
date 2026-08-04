import sys
import os
import tempfile

# Ensure the repo root is on sys.path so 'src' is importable
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from src.generate_topdown_layers import _collect_phase_files

    with tempfile.TemporaryDirectory() as proj_dir:
        # Create mock extracted_function directory
        extracted_base = os.path.join(proj_dir, "extracted_functions")
        func_subdir = os.path.join(extracted_base, "foo", "bar-cpp")
        os.makedirs(func_subdir)

        # Create mock extracted function files
        func_a = os.path.join(func_subdir, "func_a.cpp")
        func_b = os.path.join(func_subdir, "func_b.cpp")
        for f in (func_a, func_b):
            with open(f, "w") as fh:
                fh.write("// extracted function\n")

        # Phase data where the same source_file appears in TWO different modules
        phase_data = {
            "modules": [
                {"name": "module_A", "source_files": ["foo/bar.cpp"]},
                {"name": "module_B", "source_files": ["foo/bar.cpp"]},
            ]
        }

        results = _collect_phase_files(proj_dir, phase_data)

        # Check uniqueness by fpath
        fpaths = [r[0] for r in results]
        seen = set()
        duplicates = set()
        for fp in fpaths:
            if fp in seen:
                duplicates.add(fp)
            seen.add(fp)

        if duplicates:
            print(
                "CONFIRMED — duplicate fpaths found in result:",
                [os.path.relpath(d, proj_dir) for d in duplicates],
            )
            print("Results:")
            for fpath, mod in results:
                print(f"  {os.path.relpath(fpath, proj_dir)} -> module={mod}")
        else:
            print(f"NOT CONFIRMED — all fpaths unique ({len(fpaths)} entries)")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
