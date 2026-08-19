import sys
import os

# Add the repo root to sys.path so imports work from repo root
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

from io import StringIO

try:
    from src.incremental_reasoner import _StdoutTee

    console = StringIO()
    log_stream = StringIO()

    # Construct the instance per the __init__ call under test
    tee = _StdoutTee(console, log_stream)

    # The spec claim: subsequent write() calls on this instance must forward
    # to both the stored console and log_stream objects.
    # The trigger condition claims: "calling instance.write('test') raises
    # AttributeError, failing to forward to console and log_stream as required."
    tee.write("test")

    console_content = console.getvalue()
    log_content = log_stream.getvalue()

    # The bug claim says write() should raise AttributeError. If it does NOT
    # raise and successfully forwards to BOTH streams, the bug is NOT CONFIRMED.
    forwarded_to_console = "test" in console_content
    forwarded_to_log = "test" in log_content

    if not forwarded_to_console or not forwarded_to_log:
        print(
            "CONFIRMED — write() did not forward correctly: "
            f"console={console_content!r} log_stream={log_content!r}"
        )
    else:
        print(
            "NOT CONFIRMED — write() forwarded correctly to both streams: "
            f"console={console_content!r} log_stream={log_content!r}"
        )

except AttributeError as e:
    print(f"CONFIRMED — AttributeError raised: {e}")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
