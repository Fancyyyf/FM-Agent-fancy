import sys
import os
import json
import tempfile
import shutil

# Use the package entry point (src.trace_writer)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.trace_writer import append_event

tmpdir = None
try:
    tmpdir = tempfile.mkdtemp()
    events_path = os.path.join(tmpdir, "events.jsonl")

    # Trigger condition: write content that does NOT end with a newline
    with open(events_path, "w", encoding="utf-8") as f:
        f.write('{"partial": ')

    # Call append_event with a new event
    new_event = {"event": "new", "data": "test"}
    append_event(tmpdir, new_event)

    # Read back the file content
    with open(events_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify: spec says each event occupies exactly one complete line.
    # If bug exists, new event is concatenated onto the same line as the partial content.
    new_event_json = json.dumps(new_event, ensure_ascii=False)

    if '\n' + new_event_json in content:
        print(f'NOT CONFIRMED — new event is on its own line: {content!r}')
    else:
        print(f'CONFIRMED — new event concatenated to incomplete line: {content!r}')

except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    sys.exit(1)
finally:
    if tmpdir and os.path.exists(tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)
