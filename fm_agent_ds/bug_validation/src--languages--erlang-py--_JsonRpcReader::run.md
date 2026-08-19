# Bug Report: _JsonRpcReader::run

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Each complete JSON-RPC message received on self._stream (framed by HTTP-style headers that terminate with an empty line and contain a Content-Length field) is decoded from JSON and placed as a Python object onto self._messages, in the order received. When self._stream reaches EOF, or when a payload is shorter than its declared Content-Length, an EOFError is placed on self._messages and the method returns. When any other exception is raised during processing, that exception is placed on self._messages and the method returns. The method never raises an exception to its caller.

---

### Actual Behavior

If the method `run()` returns (it may never return if no exception occurs), then the following holds. The binary stream `self._stream` remains open but its read position is advanced to an indeterminate point after the last read operation (successful or failed). The thread-safe queue `self._messages` now contains all elements it had before `run()` was called, followed by zero or more successfully parsed JSON messages (each a Python object obtained from a complete `content-length` delimited payload read after a set of HTTP-like headers), then followed by a single exception object `exc` that caused the loop to terminate. This exception is an instance of `BaseException` (or a subclass) and was placed into the queue by the `except` block. Formally, let `Q_before` be the sequence of items in `self._messages` before the call. After the call, the queue contains the sequence `Q_after = Q_before + [m_1, ..., m_k, exc]` where `k >= 0`, each `m_i` is the result of `json.loads(payload_i.decode('utf-8'))` for some `payload_i` read from the stream exactly after correctly parsing a header set that included a `content-length` field whose value was a non-negative integer, and `exc` is the exception instance that was caught in the `except BaseException as exc` block.

---

## Code Evidence

Line 20: self._messages.put(exc)

---

## Trigger Condition

The specification (B) states 'The method never raises an exception to its caller.' The code's except block calls self._messages.put(exc) without a try/except. If that put() call raises an exception, it will propagate to the caller, directly contradicting the specification.

---

## How to trigger the bug

The `except BaseException as exc:` handler on line 89-90 of `src/languages/erlang.py` calls `self._messages.put(exc)` without any error handling around it. If that `put()` call itself raises an exception (e.g., if the queue is unexpectedly full, its underlying lock is corrupted, or the queue object rejects the item), the exception propagates uncaught to the caller of `run()`, directly violating the specification's guarantee that "The method never raises an exception to its caller."

The probe demonstrates this by substituting a queue-like object whose `put()` method always raises `RuntimeError`. When a valid JSON-RPC payload is read and `put()` is called normally (line 88), it raises. This is caught by the `except BaseException as exc:` block (line 89). The handler then attempts `self._messages.put(exc)` on line 90, which raises again — and this time there is no try/except around it, so the `RuntimeError` propagates to the caller.

### Inputs

| Parameter | Value |
|-----------|-------|
| `stream` | `BytesIO(b"Content-Length: 4\r\n\r\nnull")` — a valid minimal JSON-RPC frame |
| `messages` | `FailingQueue()` — a queue mock whose `put()` always raises `RuntimeError` |

### Expected (spec-correct) Output

The method should **never raise** an exception to its caller. When `put()` fails inside the except block, the exception should be absorbed (e.g., silently dropped or the method should still return without propagating).

### Actual (buggy) Output

A `RuntimeError("queue put failure")` propagates out of `run()` to its caller, violating the specification.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import io
from src.languages.erlang import _JsonRpcReader

class FailingQueue:
    def put(self, item):
        raise RuntimeError("queue put failure")

stream = io.BytesIO(b"Content-Length: 4\r\n\r\nnull")
reader = _JsonRpcReader(stream, FailingQueue())
reader.run()
# Raises RuntimeError("queue put failure") — spec says this should never happen
```

---

## Probe Script

```python
import io
import sys

# Allow importing from repo root
sys.path.insert(0, ".")

# ---------- fixture: queue whose put() always raises ----------

class FailingQueue:
    """A queue-like object whose put() always raises RuntimeError.

    This simulates a scenario where queue.put(exc) fails inside the
    except handler of _JsonRpcReader.run(), testing whether the
    exception propagates to the caller in violation of the spec.
    """

    def put(self, item):
        raise RuntimeError("queue put failure")


# ---------- fixture: minimal valid JSON-RPC frame ----------

# Content-Length: 4, payload "null"  (json.loads("null") returns None)
RPC_FRAME = b"Content-Length: 4\r\n\r\nnull"


# ---------- exercise _JsonRpcReader.run ----------

try:
    from src.languages.erlang import _JsonRpcReader

    stream = io.BytesIO(RPC_FRAME)
    bad_queue = FailingQueue()

    reader = _JsonRpcReader(stream, bad_queue)
    # Call run() directly (not via Thread.start) so exceptions propagate
    reader.run()

    # If we got here, run() returned without raising
    print("NOT CONFIRMED — run() completed without raising an exception to the caller")

except RuntimeError as exc:
    msg = str(exc)
    if "queue put failure" in msg:
        print(f"CONFIRMED — RuntimeError propagated to caller: {msg}")
    else:
        print(f"NOT CONFIRMED — unexpected RuntimeError: {msg}")

except ImportError as exc:
    print(f"ERROR: import failed — {exc}")
    sys.exit(1)

except Exception as exc:
    print(f"NOT CONFIRMED — unexpected exception type {type(exc).__name__}: {exc}")

```

### Probe Output

```
CONFIRMED — RuntimeError propagated to caller: queue put failure
```
