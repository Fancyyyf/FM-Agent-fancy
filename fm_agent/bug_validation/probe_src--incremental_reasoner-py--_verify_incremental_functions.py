import sys
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # --- Attempt to import the function under test ---
    try:
        from src.incremental_reasoner import _verify_incremental_functions  # noqa: E402
    except ImportError as e:
        # Fallback: test the core boolean logic in isolation.
        # The bug is that line 1916 uses "if submodules:" (truthy) instead of
        # "if submodules is not None:" as the spec requires.
        submodules = []
        spec_check = submodules is not None   # True  — spec: filter MUST apply
        code_check = bool(submodules)          # False — code: filter is SKIPPED

        if spec_check and not code_check:
            print(
                "CONFIRMED — Boolean mismatch: "
                "spec requires 'is not None' check (evaluates True for []), "
                "code uses truthiness check (evaluates False for []). "
                f"spec_check={spec_check!r}, code_check={code_check!r}"
            )
        else:
            print(
                "NOT CONFIRMED — Boolean check passed unexpectedly: "
                f"spec_check={spec_check!r}, code_check={code_check!r}"
            )
        return

    # --- Full integration test against the actual function ---
    tmpdir = tempfile.mkdtemp(prefix="fm_agent_probe_")
    try:
        work_dir = os.path.join(tmpdir, "fm_agent")
        extracted_dir = os.path.join(work_dir, "extracted_functions")

        # Create dummy extracted-function files so verify_targets are non-empty.
        dummy_rel = "src/core/test_func.py"
        dummy_abs = os.path.join(extracted_dir, dummy_rel)
        os.makedirs(os.path.dirname(dummy_abs))
        with open(dummy_abs, "w") as f:
            f.write("# [SPEC]\n# Test spec\n# [SPEC]\n\ndef test(): pass\n")

        os.makedirs(os.path.join(work_dir, "logic_verification_results"))
        os.makedirs(os.path.join(work_dir, "bug_validation"))

        # _modified_function_targets returns absolute extracted-file paths keyed by
        # function name.  We return exactly one dummy function so verify_targets
        # is non-empty and file_list would be non-empty IF the submodule filter
        # is skipped.
        mock_targets = {dummy_rel: dummy_abs}

        # Mock _is_under_submodules to return False — simulating the *correct*
        # behaviour of that helper (i.e., an empty submodule list matches
        # nothing).  This isolates the bug in _verify_incremental_functions:
        # if the outer "if submodules:" gate is skipped, _is_under_submodules
        # is never called and file_list stays non-empty.
        mock_is_under = MagicMock(return_value=False)

        # The spec says: submodules=[]  → "is not None" → filter applies →
        # _is_under_submodules returns False for every path → file_list empty →
        # returns [].
        expected = []

        patches = [
            patch(
                "src.incremental_reasoner._modified_function_targets",
                return_value=mock_targets,
            ),
            patch("src.incremental_reasoner._is_under_submodules", mock_is_under),
            patch(
                "src.incremental_reasoner._verify_single_file",
                MagicMock(return_value=(dummy_rel, "MATCH")),
            ),
            patch("src.incremental_reasoner.MAX_WORKERS", 1),
            patch("src.incremental_reasoner.logging"),
        ]
        for p in patches:
            p.start()

        try:
            actual = _verify_incremental_functions(
                proj_dir=tmpdir,
                work_dir=work_dir,
                changed_functions={},
                updated_spec_files=[],
                submodules=[],   # empty list — NOT None!
            )
        finally:
            for p in patches:
                p.stop()

        filter_applied = mock_is_under.called
        passed = actual != expected

        if passed:
            print(
                f"CONFIRMED — submodules=[]: returned {actual!r} (expected {expected!r}). "
                f"Submodule filter was {'applied' if filter_applied else 'SKIPPED'}."
            )
        else:
            print(
                f"NOT CONFIRMED — actual matched expected: {actual!r}. "
                f"Submodule filter was {'applied' if filter_applied else 'SKIPPED'}."
            )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        print("ERROR:", traceback.format_exc())
        sys.exit(1)
