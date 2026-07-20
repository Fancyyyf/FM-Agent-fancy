import sys
import tempfile

try:
    from src.languages.erlang import _analyze_project_uncached
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Attempt 3: Test empty directory — verify span/server_info existence
with tempfile.TemporaryDirectory() as tmpdir:
    try:
        result = _analyze_project_uncached(tmpdir)
    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)

    # Bug claim: early return ErlangAnalysis(functions={}, edges={}) omits spans/server_info
    # Dataclass defaults: spans=field(default_factory=dict), server_info=None
    missing = []
    if not hasattr(result, 'spans'):
        missing.append('spans')
    if not hasattr(result, 'server_info'):
        missing.append('server_info')
    if hasattr(result, 'spans') and not isinstance(result.spans, dict):
        missing.append('spans(wrong_type)')

    if missing:
        print(f'CONFIRMED — missing/malformed attributes: {missing}')
    else:
        print(f'NOT CONFIRMED — all required attributes present (spans={result.spans!r}, server_info={result.server_info!r})')
