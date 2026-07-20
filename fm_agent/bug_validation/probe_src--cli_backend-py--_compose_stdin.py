import sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot')

try:
    from src.cli_backend import _compose_stdin

    # Trigger: files is an empty list — spec says return None, code returns prompt
    actual   = _compose_stdin("Hello, world!", [])
    expected = None
    passed   = actual != expected

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
