"""Probe script for bug src--incremental_reasoner-py--extract_existing_specs.

Bug: extract_existing_specs reconstructs INFO block markers using
_detect_comment_prefix(spec_block) with .strip(), losing indentation
that was present in the original file's comment markers. The spec requires
the complete text of the file's [INFO] block including original markers.
"""
import sys
import os
import tempfile
import shutil

# Ensure repo root is on the path so 'src' and 'config' imports resolve
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

from src.incremental_reasoner import extract_existing_specs


def main():
    # Create <tmpdir>/fm_agent/extracted_functions/test_pkg/test_probe.py
    tmpdir = tempfile.mkdtemp()
    try:
        extracted_base = os.path.join(tmpdir, "fm_agent", "extracted_functions")
        pkg_dir = os.path.join(extracted_base, "test_pkg")
        os.makedirs(pkg_dir)

        test_file = os.path.join(pkg_dir, "test_probe.py")
        file_content = (
            "   # [SPEC]\n"
            "   # spec line one\n"
            "   # spec line two\n"
            "   # [SPEC]\n"
            "\n"
            "   # [INFO]\n"
            "   # info line one\n"
            "   # info line two\n"
            "   # [INFO]\n"
        )
        with open(test_file, "w") as f:
            f.write(file_content)

        # Expected per spec: complete text of the file's [INFO] block
        # including ORIGINAL markers (with indentation).
        expected_info = (
            "   # [INFO]\n"
            "   # info line one\n"
            "   # info line two\n"
            "   # [INFO]"
        )

        result = extract_existing_specs(tmpdir)
        # Key is relative to fm_agent/extracted_functions/ → "test_pkg/test_probe.py"
        rel_path = os.path.join("test_pkg", "test_probe.py")
        entry = result.get(rel_path)
        if entry is None:
            print("ERROR: test file not found in result dict (keys: %r)" % list(result.keys()))
            sys.exit(1)
        actual_info = entry.get("info")

        # The spec says info should be the complete text of the file's [INFO]
        # block including ORIGINAL markers. The buggy code strips indentation
        # via .strip() on the reconstructed info_tag, producing markers without
        # the leading spaces.
        passed = actual_info != expected_info

        if passed:
            print(
                "CONFIRMED — actual: %r | expected: %r"
                % (actual_info, expected_info)
            )
        else:
            print(
                "NOT CONFIRMED — actual matched expected: %r"
                % (actual_info,)
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
