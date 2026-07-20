import os
import re
import sys

# Ensure the repo root is on sys.path so the "src" package is importable.
# The package does not define setuptools entry points; importing via
# its public module path is the correct public entry point.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from src.trace_writer import utc_now_iso

    # The spec requires ISO 8601 with microsecond precision ending in "Z"
    # Expected format: YYYY-MM-DDTHH:MM:SS.ffffffZ
    iso_with_micros = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$')

    confirmed = False
    failure_value = None
    iterations = 0

    for i in range(500_000):
        result = utc_now_iso()
        iterations = i + 1
        if not iso_with_micros.match(result):
            confirmed = True
            failure_value = result
            break

    if confirmed:
        print(f'CONFIRMED — after {iterations} iterations, output missing microsecond precision: {failure_value!r}')
    else:
        print(f'NOT CONFIRMED — all {iterations} outputs included microsecond precision (YYYY-MM-DDTHH:MM:SS.ffffffZ)')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
