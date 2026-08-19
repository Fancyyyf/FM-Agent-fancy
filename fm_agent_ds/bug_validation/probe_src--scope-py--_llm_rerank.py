"""Probe for bug: _llm_rerank does not validate len <= top_k, uniqueness, or funcs_info membership."""
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock

# Ensure repo root is on sys.path so `from src.scope import ...` resolves.
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))


def main() -> str:
    import src.scope as scope
    _llm_rerank = scope._llm_rerank

    # Create minimal funcs_info with 3 functions: foo, bar, baz
    # start/end must be within source_lines range (1-indexed)
    funcs_info = [
        {
            "name": "foo",
            "start": 1,
            "end": 1,
            "calls": [],
            "idents": [],
            "body_words": [],
            "exc_types": [],
            "docstring": "Function foo",
        },
        {
            "name": "bar",
            "start": 2,
            "end": 2,
            "calls": [],
            "idents": [],
            "body_words": [],
            "exc_types": [],
            "docstring": "Function bar",
        },
        {
            "name": "baz",
            "start": 3,
            "end": 3,
            "calls": [],
            "idents": [],
            "body_words": [],
            "exc_types": [],
            "docstring": "Function baz",
        },
    ]
    source_lines = [
        "def foo(): pass",
        "def bar(): pass",
        "def baz(): pass",
    ]
    filepath = "/tmp/test.py"
    issue = "test issue"
    top_k = 2  # spec requires at most 2 names returned

    # Bug 1: LLM returns more names than top_k (4 names > top_k=2)
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps(["foo", "bar", "baz", "qux"])))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    result = _llm_rerank(
        funcs_info=funcs_info,
        source_lines=source_lines,
        filepath=filepath,
        issue=issue,
        top_k=top_k,
        llm_client=mock_client,
        model="test-model",
    )

    # The spec requires len(result) <= top_k when not None.
    # Since top_k=2 but result has 4 names, this is a confirmed bug.
    if result is None:
        return "NOT CONFIRMED — function returned None (unexpected)"
    if len(result) > top_k:
        return (
            f"CONFIRMED — spec requires len <= {top_k}, "
            f"but got {len(result)} names: {result}"
        )
    return f"NOT CONFIRMED — result length {len(result)} <= top_k {top_k}: {result}"


if __name__ == "__main__":
    try:
        output = main()
        print(output)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        import traceback; traceback.print_exc()
        sys.exit(1)
