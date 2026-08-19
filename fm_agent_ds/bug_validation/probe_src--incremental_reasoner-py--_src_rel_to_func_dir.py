import sys
import os
import tempfile

# Ensure repo root is on sys.path so that `config` and `src` resolve
_repo_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.incremental_reasoner import _src_rel_to_func_dir
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

try:
    with tempfile.TemporaryDirectory() as proj_dir:
        # Create a source file whose basename starts with a period (dotfile)
        abs_src = os.path.join(proj_dir, "src", ".env")
        os.makedirs(os.path.dirname(abs_src), exist_ok=True)
        with open(abs_src, "w") as f:
            f.write("FOO=bar\n")

        actual_func_dir, actual_ext = _src_rel_to_func_dir(proj_dir, abs_src)

        # Per spec: basename `.env` contains a period, so:
        #   portion before last period = "" (empty)
        #   portion after last period  = "env"
        #   dir_name = "" + "-" + "env" = "-env"
        #   ext = "env"
        expected_dir_name = "-env"
        expected_ext = "env"

        actual_dir_name = os.path.basename(actual_func_dir)
        passed = actual_dir_name != expected_dir_name or actual_ext != expected_ext

        if passed:
            print(
                f"CONFIRMED — actual: dir_name={actual_dir_name!r}, ext={actual_ext!r}"
                f" | expected: dir_name={expected_dir_name!r}, ext={expected_ext!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — actual matched expected:"
                f" dir_name={actual_dir_name!r}, ext={actual_ext!r}"
            )
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
