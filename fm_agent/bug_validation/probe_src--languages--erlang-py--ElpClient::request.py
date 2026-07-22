"""Probe for ElpClient::request -- _MAX_CONTENT_MODIFIED_RETRIES=0 triggers AssertionError not in spec."""

import os
import sys
import tempfile

# Add repo root to path so the entry-point import works
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

# --- Create a temporary workspace for this probe (per FM-Agent guard) ---
tmpdir = tempfile.mkdtemp(prefix="probe_ElpClient_request_")
os.chdir(tmpdir)

try:
    import src.languages.erlang as erlang_module

    # Monkey-patch the retry constant to zero to trigger the unreachable path
    original_retries = erlang_module._MAX_CONTENT_MODIFIED_RETRIES
    erlang_module._MAX_CONTENT_MODIFIED_RETRIES = 0

    # Instantiate ElpClient without __enter__ (no subprocess spawned)
    client = erlang_module.ElpClient("/tmp")
    client.timeout = 5.0

    try:
        result = client.request("test_method", {"key": "value"})
        print(f"NOT CONFIRMED — method returned result: {result!r}")
    except AssertionError as e:
        print(f"CONFIRMED — AssertionError raised (spec violation): {e}")
    except TimeoutError:
        print("NOT CONFIRMED — TimeoutError raised (spec-compliant)")
    except RuntimeError:
        print("NOT CONFIRMED — RuntimeError raised (spec-compliant)")
    except Exception as e:
        print(f"CONFIRMED — unexpected exception type {type(e).__name__}: {e}")
    finally:
        erlang_module._MAX_CONTENT_MODIFIED_RETRIES = original_retries

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
