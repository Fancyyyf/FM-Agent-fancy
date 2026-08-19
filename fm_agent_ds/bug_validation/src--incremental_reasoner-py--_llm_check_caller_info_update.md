# Bug Report: _llm_check_caller_info_update

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_llm_check_caller_info_update.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dict when a consistency determination is made. The returned dict has key 'info_updated' (bool). When info_updated is true, the dict also has key 'new_info' whose value is a dict conforming to the .info.json schema. In that new_info dict, every callee entry whose name is not equal to callee_name has the same 'signature', 'pre_condition', and 'post_condition' values as its counterpart in caller_info_block; the entry whose name equals callee_name has a pre-condition and post-condition that do not contradict any assertion in callee_new_spec's pre-condition or post-condition. When info_updated is false, the entry for callee_name in caller_info_block is already consistent with callee_new_spec and no revision is required. Returns None when no determination can be made.

---

### Actual Behavior

Upon successful execution, the function delegates to _llm_select_json and returns its result. No side-effects other than those of _llm_select_json (which may include an LLM call) are produced. If all implicit pre-conditions on the parameters work_dir, comment_prefix, and proj_dir are satisfied (work_dir is a valid directory path, comment_prefix is a string, etc.), no exceptions are raised.

Let result = _llm_check_caller_info_update(proj_dir, work_dir, idx, caller_fqn, callee_name, lang_key, comment_prefix, callee_new_spec, caller_info_block, caller_source).

Natural language: The function returns either None or a dictionary. If the configured LLM generates a response that is valid JSON, conforms to the schema {"info_updated": boolean, "new_info": object|null}, and passes the _validate_caller_info_update validator, then result is that parsed dictionary; otherwise, result is None.

Formal logic:
( result = None )

( result  Dict  hasKeys(result, {"info_updated", "new_info"}) 
  result["info_updated"]  Bool 
  ( result["new_info"] = None  result["new_info"]  Dict )
    alt_result ( alt_result = _llm_select_json(...)  (alt_result = None  result = None)  (alt_result  None  result = alt_result) )
)

(The final conjunct captures that result is exactly the return of _llm_select_json.)

---

## Code Evidence

Line 43: return _llm_select_json(
Line 44:     work_dir,
Line 45:     prompt_content,
Line 46:     stage="update_caller_info",
Line 47:     validator=_validate_caller_info_update,
Line 48:     schema_description='{"info_updated": boolean, "new_info": object|null}',
Line 49:     trace_meta={"caller_fqn": caller_fqn, "callee_name": callee_name, "idx": idx},
Line 50: )

---

## Trigger Condition

The function unconditionally returns the result of _llm_select_json after only structural validation. It does not verify that the returned dict satisfies the semantic constraints required by the specification (e.g., that when info_updated is false the existing entry is actually consistent, or when info_updated is true the new_info preserves other callee entries and makes the named entry consistent). An LLM could produce a structurally valid response that violates these constraints, and the function would deliver it, breaking Condition B.

---

## How to trigger the bug

The function `_llm_check_caller_info_update` delegates the entire decision to an LLM (via `_llm_select_json`) and validates only the structural shape of the response via `_validate_caller_info_update`. When the LLM returns a structurally valid JSON object (correct keys, correct types) but with semantically wrong content — e.g., `info_updated: true` with a `new_info` that drops pre-existing callee entries — the function passes it through without detecting the semantic violation.

### Inputs

| Parameter | Value |
|-----------|-------|
| `caller_info_block` | `{"callees": [{"name": "target_callee", "signature": "int target(int a)", "pre_condition": "a > 0", "post_condition": "return == a * 2"}, {"name": "other_callee", "signature": "void other(void)", "pre_condition": "true", "post_condition": "true"}]}` |
| `callee_name` | `"target_callee"` |
| `callee_new_spec` | `{"signature": "int target(int a)", "pre_condition": "a > 0", "post_condition": "return == a * 3"}` |
| Mocked LLM response | `{"info_updated": true, "new_info": {"callees": [{"name": "target_callee", "signature": "int target(int a)", "pre_condition": "a > 0", "post_condition": "return == a * 42"}]}}` |

### Expected (spec-correct) Output

The function should either:
- Return `None` (cannot determine consistency), or
- Return a dict where `info_updated` is true AND `new_info` preserves the `"other_callee"` entry unchanged AND the `"target_callee"` entry does not contradict `callee_new_spec`.

In this case, the LLM response is semantically wrong (it drops `"other_callee"`), so a spec-correct implementation would reject it (return `None` or raise an error).

### Actual (buggy) Output

The function returns `{"info_updated": True, "new_info": {"callees": [{"name": "target_callee", "signature": "int target(int a)", "pre_condition": "a > 0", "post_condition": "return == a * 42"}]}}` — the structurally valid but semantically wrong LLM response — because `_validate_caller_info_update` only checks the presence and types of `info_updated` and `new_info`, not the semantic constraints the specification requires.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.incremental_reasoner import _llm_check_caller_info_update

caller_info_block = {
    "callees": [
        {"name": "target_callee", "signature": "int target(int a)",
         "pre_condition": "a > 0", "post_condition": "return == a * 2"},
        {"name": "other_callee", "signature": "void other(void)",
         "pre_condition": "true", "post_condition": "true"},
    ]
}
callee_new_spec = {
    "signature": "int target(int a)",
    "pre_condition": "a > 0",
    "post_condition": "return == a * 3",
}

# The LLM might return structurally valid JSON that drops "other_callee":
# {"info_updated": true, "new_info": {"callees": [{"name": "target_callee", ...}]}}
# _validate_caller_info_update only checks structure, not that "other_callee" is preserved.
# The function returns this wrong response without semantic validation.
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — function returned the structurally valid but semantically wrong response: other_callee entry was dropped from new_info
```
