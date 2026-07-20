"""Probe script for bug: _http_status_from_exc raises AttributeError when code attr deleted."""
import sys
import os
import urllib.error

# Ensure the repo root is on sys.path so `src` package can be imported
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

from src.llm_client import _http_status_from_exc

# Create an HTTPError and delete its 'code' attribute
exc = urllib.error.HTTPError('http://example.com', 404, 'Not Found', {}, None)
del exc.code

# Spec requires: Never raises an exception regardless of input
# Actual behavior: accesses exc.code unconditionally, so del exc.code → AttributeError
bug_confirmed = False
try:
    result = _http_status_from_exc(exc)
    # No exception raised — spec satisfied (bug NOT reproduced)
    print(f'NOT CONFIRMED — function returned {result!r} without raising')
except AttributeError as e:
    # Bug reproduced: spec says never raise, but AttributeError was raised
    bug_confirmed = True
    print(f'CONFIRMED — AttributeError raised: {e} | Spec requires: never raise regardless of input')
except Exception as e:
    print(f'ERROR: unexpected exception: {type(e).__name__}: {e}')
    sys.exit(1)
