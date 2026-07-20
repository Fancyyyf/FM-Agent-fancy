import sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot')

try:
    from src.cli_backend import messages_to_prompt

    # Trigger: content block's 'text' field is a non-string (integer)
    messages = [
        {"role": "user", "content": [{"text": 42}]}
    ]
    expected = "USER:\n42"

    try:
        actual = messages_to_prompt(messages)
        # If we get here, no exception was raised — bug is NOT confirmed
        passed = actual != expected
    except TypeError as e:
        # Bug confirmed: str.join rejects non-string elements
        actual = f"TypeError({e})"
        passed = True

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
