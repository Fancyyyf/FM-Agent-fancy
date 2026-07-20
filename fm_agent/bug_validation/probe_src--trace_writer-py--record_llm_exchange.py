import sys
import os

# Add repo root to sys.path so we can import 'src'
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

import tempfile
import shutil

try:
    from src.trace_writer import record_llm_exchange

    # Setup: an event dict WITHOUT a "metadata" key
    event = {"id": "evt_test_001", "type": "llm_exchange"}
    event_copy_before = dict(event)  # snapshot before call
    messages = [{"role": "user", "content": "hello"}]

    # Use a temp dir as trace_dir (truthy)
    tmpdir = tempfile.mkdtemp()

    record_llm_exchange(
        trace_dir=tmpdir,
        event_id="test_001",
        event=event,
        messages=messages,
        response=None,
    )

    # Check side effect: was "metadata" key ADDED to the event dict?
    had_metadata_before = "metadata" in event_copy_before
    has_metadata_after = "metadata" in event

    # The bug: setdefault("metadata", {}) adds "metadata" key even when absent.
    # The spec only permits removing "parsed" from event.metadata — NOT adding
    # a metadata key where one didn't exist.
    if not had_metadata_before and has_metadata_after:
        print(f"CONFIRMED — event had no 'metadata' key before call (keys: {list(event_copy_before.keys())}), "
              f"but after call has metadata={event['metadata']!r}. "
              f"The setdefault() on line 51 added an unauthorized key to the event dict.")
    else:
        print(f"NOT CONFIRMED — event had_metadata_before={had_metadata_before}, "
              f"has_metadata_after={has_metadata_after}, "
              f"before keys: {list(event_copy_before.keys())}, "
              f"after keys: {list(event.keys())}")

    # Cleanup
    shutil.rmtree(tmpdir)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
