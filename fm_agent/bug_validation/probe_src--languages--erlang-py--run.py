import io
import queue
import sys

# Ensure the repo root is on sys.path so the src package resolves.
sys.path.insert(0, ".")

try:
    import src.languages.erlang as erlang
except ImportError as e:
    print(f"ERROR: Cannot import src.languages.erlang: {e}")
    sys.exit(1)

# The spec for _JsonRpcReader.run() claims "This method never returns".
# The bug: the except BaseException at the module-scope try/except catches
# any exception (including EOFError) and then the method falls through,
# returning. A concrete trigger: a stream that returns empty bytes on the
# first readline(), which raises EOFError.

mock_stream = io.BytesIO(b"")       # empty → readline() returns b"" → EOFError
messages = queue.Queue()

reader = erlang._JsonRpcReader(mock_stream, messages)

# According to the spec, run() should never return.
# If it does return, the bug is confirmed.
run_returned = False
try:
    reader.run()
    run_returned = True
except BaseException as exc:
    print(f"ERROR: run() raised {type(exc).__name__}: {exc}")
    sys.exit(1)

if run_returned:
    # run() returned — the spec says it should never return
    queue_contents = []
    while not messages.empty():
        queue_contents.append(repr(messages.get()))
    print(f"CONFIRMED — run() returned, but spec claims 'This method never returns'."
          f" Queue now contains: {queue_contents}")
else:
    print("NOT CONFIRMED — run() did not return (as expected per spec)")
