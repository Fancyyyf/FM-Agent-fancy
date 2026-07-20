"""Probe: verify _update_module_description uses hard-coded delay, not configurable.

Bug claim: _update_module_description uses hard-coded time.sleep(10) on the retry
path instead of a configurable fixed interval as required by the spec.

Spec requirement: Between consecutive failed attempts, the function waits a
configurable fixed interval.
"""

import sys
import os
import inspect

# ── setup: import the package via its public entry point ──────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    import src.pipeline_setup as pkg
except Exception as e:
    print(f'ERROR: could not import src.pipeline_setup: {e}')
    sys.exit(1)

CONFIRMED_MSG = "CONFIRMED"
NOT_CONFIRMED_MSG = "NOT CONFIRMED"


def main():
    try:
        source = inspect.getsource(pkg._update_module_description)
    except Exception as e:
        print(f'ERROR: could not get source of _update_module_description: {e}')
        sys.exit(1)

    # The bug: a hard-coded `time.sleep(10)` literal on the retry path
    has_hardcoded_sleep_10 = 'time.sleep(10)' in source

    # Does the function use any configurable (non-literal) delay?
    # Look for time.sleep with a non-digit argument
    import re
    sleep_pattern = re.compile(r'time\.sleep\(([^)]+)\)')
    sleep_args = [m.group(1).strip() for m in sleep_pattern.finditer(source)]
    all_literal_numbers = all(
        arg.isdigit() or (arg.replace('.', '', 1).isdigit() and arg.count('.') <= 1)
        for arg in sleep_args
    )

    # Check whether config.py provides a configurable retry-delay variable
    import config
    has_configurable_delay = hasattr(config, 'OPENCODE_RETRY_DELAY_SECONDS')

    if has_hardcoded_sleep_10 and not has_configurable_delay:
        lines = []
        for i, line in enumerate(source.splitlines(), 1):
            if 'time.sleep(10)' in line:
                lines.append(f"  line {i} (approx): {line.strip()}")
        print(
            f'{CONFIRMED_MSG} — _update_module_description uses hard-coded '
            f'time.sleep(10) on the retry path:\n'
            + '\n'.join(lines)
            + '\n  No configurable retry-delay variable found in config.py. '
            'Spec requires a configurable fixed interval between failed attempts.'
        )
    elif not has_hardcoded_sleep_10:
        print(
            f'{NOT_CONFIRMED_MSG} — no hard-coded time.sleep(10) found in '
            f'_update_module_description. Sleep args: {sleep_args}'
        )
    else:
        print(
            f'{NOT_CONFIRMED_MSG} — configurable retry delay exists in config.py: '
            f'OPENCODE_RETRY_DELAY_SECONDS'
        )


if __name__ == '__main__':
    main()
