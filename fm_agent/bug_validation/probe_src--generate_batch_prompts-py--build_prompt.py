"""Probe script for bug ID src--generate_batch_prompts-py--build_prompt.

Tests whether build_prompt() includes the "## CALLEE EXPECTATIONS FROM CALLERS"
section header when caller expectations exist for functions in the batch.
"""
import sys
import tempfile
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root))

from src.generate_batch_prompts import build_prompt


def create_caller_file(callee_fqn: str, expectation: str) -> str:
    """Create a minimal extracted-function file with a [INFO] block that
    contains an expectation for callee_fqn."""
    return f"""# [SPEC]
# Unit: some/caller.py
#
# caller_func(params) -> ReturnType
#   Pre-condition: ...
#   Post-condition: ...
# [SPEC]
# [INFO]
# {callee_fqn}(params) -> ReturnType
#   Pre-condition: input is valid
#   Post-condition: {expectation}
# [SPLIT]
# other_func(params) -> ReturnType
#   Pre-condition: ...
#   Post-condition: ...
# [INFO]
"""


def test_build_prompt_includes_callee_expectations_header() -> bool:
    """Return True if the section header IS present (bug NOT reproduced)."""

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)

        # --- Create a caller's extracted function file with a callee expectation ---
        callee_fqn = "target_module::target_func"
        expectation = "returns a string representing the complete prompt"
        caller_file_content = create_caller_file(callee_fqn, expectation)

        caller_relpath = "extracted_functions/src/caller/caller_func.py"
        caller_abs = work_dir / caller_relpath
        caller_abs.parent.mkdir(parents=True)
        caller_abs.write_text(caller_file_content)

        # --- Build test data that triggers the caller_expectations branch ---
        functions = [
            {
                "name": callee_fqn,
                "file": "extracted_functions/target_func.py",
                "phase1_callers": ["caller_func"],
                "phase1_callee_info_names_by_caller": {"caller_func": []},
            }
        ]

        func_to_layer = {"caller_func": 0}  # caller at layer 0 → lower than layer_idx
        all_funcs = {
            "caller_func": {
                "name": "caller_func",
                "file": caller_relpath,
            }
        }

        ext_to_lang = {".py": "python"}

        # --- Call build_prompt — target at layer 1, caller at layer 0 ---
        result = build_prompt(
            phase=1,
            layer_idx=1,
            is_cycle=False,
            functions=functions,
            func_to_layer=func_to_layer,
            all_funcs=all_funcs,
            work_dir=work_dir,
            fm_agent_prefix="fm_agent/",
            ext_to_lang=ext_to_lang,
        )

        # --- Check results ---
        has_section_header = "## CALLEE EXPECTATIONS FROM CALLERS" in result
        return has_section_header


try:
    header_present = test_build_prompt_includes_callee_expectations_header()

    if header_present:
        print(
            "NOT CONFIRMED — section header '## CALLEE EXPECTATIONS FROM CALLERS' "
            "IS present; bug cannot be reproduced."
        )
    else:
        print(
            "CONFIRMED — section header '## CALLEE EXPECTATIONS FROM CALLERS' "
            "is MISSING; bug reproduced!"
        )

except Exception as e:
    import traceback

    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
