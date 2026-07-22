"""Probe script for bug ID: src--languages--rust-py--batch_extract
Tests whether batch_extract filters out empty-list values from get_functions_by_file.
Spec requires non-empty lists; code passes through whatever get_functions_by_file returns.
"""
import sys
import os

# The probe workspace is a temp dir; add snapshot to path to import the package.
sys.path.insert(0, "/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot")


def main():
    from unittest.mock import MagicMock, patch

    # Mock CodeGraphExtractor so from_proj_dir returns a mock with
    # get_functions_by_file returning a dict containing an empty-list entry.
    mock_extractor = MagicMock()
    mock_extractor.get_functions_by_file.return_value = {
        "/fake/proj/src/main.rs": [
            ("main", "fn main() {\n    println!(\"hello\");\n}\n"),
        ],
        "/fake/proj/src/empty_mod.rs": [],   # <-- spec violation: non-empty required
    }

    with patch(
        "src.languages.rust.CodeGraphExtractor"
    ) as mock_cls:
        mock_cls.from_proj_dir.return_value = mock_extractor

        from src.languages.rust import batch_extract

        result = batch_extract("/fake/proj")

    # Check: does the result contain the empty-list entry?
    empty_key = "/fake/proj/src/empty_mod.rs"
    spec_nonempty = "Each value must be a non-empty list of (function_name, function_body) tuples"

    if empty_key in result and result[empty_key] == []:
        confirmed = True
        print(
            f"CONFIRMED — batch_extract does not filter empty-list values."
            f" File '{empty_key}' maps to [] but spec requires {spec_nonempty}"
        )
    else:
        confirmed = False
        if empty_key not in result:
            print(
                f"NOT CONFIRMED — empty-list entry was filtered out"
                f" (key '{empty_key}' not in result)"
            )
        else:
            print(
                f"NOT CONFIRMED — empty-list entry was not empty:"
                f" result[{empty_key!r}] = {result[empty_key]!r}"
            )

    sys.exit(0 if confirmed else 0)  # always exit 0; verdict is in stdout


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
