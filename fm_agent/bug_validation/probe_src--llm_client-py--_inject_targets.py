"""Probe for bug: _inject_targets reads from settings.inject.hosts instead of INJECT_HOST env var."""
import sys
import os

sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot')

try:
    # Set INJECT_HOST before importing config so it's available in the environment.
    os.environ['INJECT_HOST'] = 'alpha, beta , ,gamma'

    import config
    from src.llm_client import _inject_targets

    # config has already mapped INJECT_HOST → settings.inject.hosts via _ENV_MAP.
    # To prove the bug, break the link by clearing settings.inject.hosts so the
    # function reads an empty value while INJECT_HOST is still set.
    config.settings.inject.hosts = ""

    actual = _inject_targets()
    # Per spec: parse INJECT_HOST env var, strip, discard empties.
    expected = ['alpha', 'beta', 'gamma']

    bug_reproduced = actual != expected

    if bug_reproduced:
        print(f'CONFIRMED — reads from settings.inject.hosts instead of INJECT_HOST env var | actual: {actual!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    print(f'ERROR: {e}')
    sys.exit(1)
