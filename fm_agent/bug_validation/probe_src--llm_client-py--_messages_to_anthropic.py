import sys

try:
    from src.llm_client import _messages_to_anthropic

    # Single system message with surrounding whitespace — the code path on line 93
    # takes the "else content" branch (no strip), while the spec requires stripping.
    messages = [{"role": "system", "content": "  hello world  "}]
    system_text, an_msgs = _messages_to_anthropic(messages)

    # Spec: system_text must have leading/trailing whitespace removed.
    expected = "hello world"
    actual = system_text

    # Bug confirmed if actual does NOT match expected (whitespace was not stripped).
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
