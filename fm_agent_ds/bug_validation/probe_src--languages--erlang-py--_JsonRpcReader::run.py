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
