"""Probe: _llm_rerank accepts LLM-returned names not in funcs_info.

Spec claim: returned names must be drawn exclusively from funcs_info.
Bug: only validates "JSON array of non-empty strings", not membership in funcs_info.
"""
import sys
import json
from pathlib import Path

# Ensure the repo root is on sys.path so `from src.xxx` imports work
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    # Import via the package module (not internal file path)
    from src.scope import _llm_rerank

    # --- Setup: funcs_info with only "foo" ---
    funcs_info = [
        {
            "name": "foo",
            "start": 1,
            "end": 3,
            "calls": set(),
            "idents": set(),
            "body_words": set(),
            "exc_types": set(),
            "docstring": "",
        }
    ]
    source_lines = ["def foo():", "    pass", ""]
    filepath = "test.py"
    issue = "test issue for bug reproduction"
    top_k = 3

    # --- Mock LLM client: returns ["baz"], a name NOT in funcs_info ---
    class MockMessage:
        content = json.dumps(["baz"])

    class MockChoice:
        message = MockMessage()

    class MockResponse:
        choices = [MockChoice()]

    class MockCompletions:
        @staticmethod
        def create(model, messages, max_tokens, temperature):
            return MockResponse()

    class MockChat:
        completions = MockCompletions()

    class MockLLMClient:
        chat = MockChat()

    mock_client = MockLLMClient()

    # --- Call _llm_rerank ---
    result = _llm_rerank(
        funcs_info=funcs_info,
        source_lines=source_lines,
        filepath=filepath,
        issue=issue,
        top_k=top_k,
        llm_client=mock_client,
        model="test-model",
    )

    # --- Verify against spec ---
    spec_names = {f["name"] for f in funcs_info}  # {"foo"}

    if result is None:
        # No valid result — this would be spec-compliant if LLM returned invalid names
        print(f"NOT CONFIRMED — _llm_rerank returned None (spec-compliant, no foreign names leaked)")
    else:
        foreign = [n for n in result if n not in spec_names]
        if foreign:
            # Bug reproduced: foreign name accepted
            print(f"CONFIRMED — _llm_rerank returned foreign names: {foreign}")
            print(f"  spec names in funcs_info: {list(spec_names)}")
            print(f"  actual returned names: {result}")
        else:
            # All names are valid — spec-compliant
            print(f"NOT CONFIRMED — all returned names in funcs_info: {result}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
