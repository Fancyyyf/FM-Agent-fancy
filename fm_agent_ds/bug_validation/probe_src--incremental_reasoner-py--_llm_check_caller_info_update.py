"""Probe for bug: _llm_check_caller_info_update lacks semantic validation.

The function delegates to _llm_select_json and returns its result after only
structural validation. It does NOT verify that:
  - other callee entries are preserved unchanged when info_updated=true
  - the named callee entry does not contradict callee_new_spec
  - when info_updated=false, the existing entry is actually consistent

This probe mocks _llm_select_json to return a structurally valid response where
info_updated=true but new_info drops a pre-existing callee entry ("other_callee").
If the function returns this semantically wrong response, the bug is confirmed.
"""

import sys
import os
import tempfile
from unittest.mock import patch

# Add repo root to path so 'src' package is importable.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)


def main():
    # --- test inputs ---
    caller_info_block = {
        "callees": [
            {
                "name": "target_callee",
                "signature": "int target(int a)",
                "pre_condition": "a > 0",
                "post_condition": "return == a * 2",
            },
            {
                "name": "other_callee",
                "signature": "void other(void)",
                "pre_condition": "true",
                "post_condition": "true",
            },
        ]
    }

    callee_new_spec = {
        "signature": "int target(int a)",
        "pre_condition": "a > 0",
        "post_condition": "return == a * 3",
    }

    # Structurally valid but semantically WRONG response:
    # - info_updated is true, so new_info must be non-null  (structurally ok)
    # - new_info is a valid .info.json shape               (structurally ok)
    # - BUT "other_callee" is missing — spec requires other entries preserved
    bad_response = {
        "info_updated": True,
        "new_info": {
            "callees": [
                {
                    "name": "target_callee",
                    "signature": "int target(int a)",
                    "pre_condition": "a > 0",
                    "post_condition": "return == a * 42",
                }
            ]
        },
    }

    passed = False
    detail = ""

    try:
        from src.incremental_reasoner import _llm_check_caller_info_update

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "src.incremental_reasoner._llm_select_json",
                return_value=bad_response,
            ):
                result = _llm_check_caller_info_update(
                    proj_dir=tmpdir,
                    work_dir=tmpdir,
                    idx=1,
                    caller_fqn="test::caller",
                    callee_name="target_callee",
                    lang_key="c",
                    comment_prefix="//",
                    callee_new_spec=callee_new_spec,
                    caller_info_block=caller_info_block,
                    caller_source="void caller(void) { target(1); other(); }",
                )

        if result is None:
            detail = "function returned None — no result passed through"
        elif not result.get("info_updated"):
            detail = (
                f"function returned info_updated=False (result={result!r}) — "
                "not the injected bad response"
            )
        else:
            new_info = result.get("new_info", {})
            callee_names = [c["name"] for c in new_info.get("callees", [])]
            other_preserved = "other_callee" in callee_names
            if not other_preserved:
                passed = True
                detail = (
                    "function returned the structurally valid but semantically "
                    "wrong response: other_callee entry was dropped from new_info"
                )
            else:
                detail = (
                    f"function returned result with other_callee preserved "
                    f"(result={result!r}) — semantic check somehow passed"
                )

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    if passed:
        print(f"CONFIRMED — {detail}")
    else:
        print(f"NOT CONFIRMED — {detail}")


if __name__ == "__main__":
    main()
