import sys

try:
    from src.llm_client import _messages_to_anthropic

    # Two system messages with leading/trailing whitespace that .strip() would modify
    messages = [
        {"role": "system", "content": "  Hello  "},
        {"role": "system", "content": " there "},
    ]

    system_text, anthropic_msgs = _messages_to_anthropic(messages)

    # Spec says: concatenate with "\n\n" separator, preserve all whitespace
    expected = "  Hello  \n\n there "
    actual = system_text

    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED -- actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED -- actual matched expected: {actual!r}")
