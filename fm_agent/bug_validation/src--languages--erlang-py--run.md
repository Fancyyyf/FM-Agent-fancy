# Bug Report: _JsonRpcReader.run

**Source file:** `src/languages/erlang-py/run.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- This method never returns; it runs an indefinite loop that consumes LSP
    JSON-RPC messages from self._stream and places decoded message objects or
    termination exceptions onto self._messages.
  - Each complete message consists of a header block (ASCII key-value lines
    terminated by an empty line) containing a Content-Length field, followed by
    a body of exactly Content-Length bytes containing a UTF-8-encoded JSON
    payload.
  - For each complete message fully received: the JSON payload is decoded and
    the resulting Python object is placed onto self._messages.
  - When self._stream reaches EOF before the empty-line terminator of the
    header block: an EOFError is placed onto self._messages.
  - When self._stream delivers fewer than Content-Length payload bytes after
    the header block: an EOFError is placed onto self._messages.
  - When any BaseException is raised during reading, header parsing, or JSON
    decoding: the exception object itself (not a wrapper) is placed onto
    self._messages.
  - After a termination object (EOFError or other exception) is placed onto
    self._messages, the method performs no further reads from self._stream and
    no further puts to self._messages.

---

### Actual Behavior

After the `run` method returns (which can only happen if an exception terminates the infinite loop), `self._messages` contains all Python objects that were successfully parsed from well-formed JSON-RPC payloads received before the error, followed by the exception instance that caused termination. The stream may be in an inconsistent or closed state. The original contents of the queue (if any) remain before the newly enqueued items.

---

## Code Evidence

Line 2:         try:
Line 19:         except BaseException as exc:
Line 20:             self._messages.put(exc)

---

## Trigger Condition

Condition B explicitly states 'This method never returns', yet the code is structured so that any BaseException ends the try block and causes the method to return after putting the exception on the queue. A concrete input where the stream returns empty bytes on the first readline triggers the EOFError path, leading to an immediate return, which violates the requirement.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| `self._stream` | `io.BytesIO(b"")` — an empty byte stream, simulating an ELP process that closes stdout without producing any output |
| `self._messages` | `queue.Queue()` — an empty thread-safe queue |

### Expected (spec-correct) Output

The method should never return. When the stream EOF is detected, an `EOFError("ELP closed its stdout")` should be placed onto `self._messages` and the method should continue looping (or block indefinitely) without returning.

### Actual (buggy) Output

The method returns immediately. `self._messages` contains a single `EOFError("ELP closed its stdout")` instance.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import io
import queue
import sys
sys.path.insert(0, ".")

import src.languages.erlang as erlang

stream = io.BytesIO(b"")
messages = queue.Queue()
reader = erlang._JsonRpcReader(stream, messages)
reader.run()
# actual (buggy) output: run() returns, messages.get() == EOFError('ELP closed its stdout')
# expected (correct) output: run() should never return
```

---

## Probe Script

```py
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
```

### Probe Output

```
CONFIRMED — run() returned, but spec claims 'This method never returns'. Queue now contains: ["EOFError('ELP closed its stdout')"]
```
