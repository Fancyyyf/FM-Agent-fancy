# Bug Report: ElpClient._wait_for_response

**Source file:** `/tmp/fm_agent_wt_FM-Agent_l5vkw0lv/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/ElpClient::_wait_for_response.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Blocks until either the server's response to the request identified by request_id arrives or the deadline passes, whichever occurs first. A message qualifies as the awaited response only if it carries the identifier request_id and is a response rather than a server-initiated request or notification. When the matching response arrives and reports success, the call returns the decoded result payload carried by that response  exactly what the server reported as the result of that request  and returns None when the response carries no result; a None or otherwise falsy return never signals failure, only the absence of server-reported data. Server-to-client traffic carrying other identities that arrives while waiting is consumed, and answered where the protocol requires an answer, so such traffic can never block, indefinitely delay, or be mistaken for the awaited response. Error contract: an exception is raised when the deadline passes before the matching response arrives; when the matching response reports a server error for the request  where a content-modification conflict (the server observed the document content changed while serving the request) is raised as a distinct exception class that identifies exactly that condition, so the caller can retry only that class, while every other server error is raised under a different exception class; and when the transport fails, the message reader fails, or the server process terminates, in which case the corresponding exception propagates to the caller. Failure is never signaled through a sentinel return value. On every exit path, every transport message that arrived before the wait ended has been consumed, and no client-side state is left that would prevent a subsequent wait for a different request identifier.

---

### Actual Behavior

The method terminates (it cannot loop indefinitely) because every iteration calls _next_message(deadline), which enforces the absolute monotonic-clock bound and raises on expiry. Exactly one of the following outcomes holds upon exit:

1. NORMAL RETURN: A transport message m was received such that m.get('id') == request_id, 'method' is not a key of m, and m.get('error') is falsy (None or absent). The method returns m.get('result'), which is the decoded result payload of the awaited response. The response message is fully consumed and not re-presented.

2. CONTENT-MODIFIED ERROR: A matching response m (same id, no 'method' key) was received whose m.get('error') is a dict e with e.get('code') == _CONTENT_MODIFIED_ERROR. The method raises _ContentModifiedError(e). No value is returned.

3. GENERIC SERVER ERROR: A matching response m was received whose m.get('error') is truthy but does not satisfy the content-modified predicate above. The method raises RuntimeError with message f'ELP request failed: {error}'. No value is returned.

4. TIMEOUT / TRANSPORT FAILURE: Before any matching response arrived, _next_message raised an exception (deadline elapsed, transport error, reader failure, or server-process termination). That exception propagates unmodified out of _wait_for_response. No value is returned.

In all cases:
 Every message received by _next_message prior to the terminating message (or prior to the exception in case 4) that did NOT match the awaited response (i.e., whose id differed from request_id or which contained a 'method' key) was passed to self._handle_server_message and fully consumed, so no unprocessed message remains queued on the transport.
 The absolute monotonic-clock time at the point of return or exception does not exceed deadline; the method never blocks past the caller-supplied bound.
 The transport pipe and server-process liveness assumptions that held at entry are unchanged by this method itself; any transport-level failure is surfaced solely via the exception path of _next_message.
 self is otherwise unmodified (no new attributes, no mutation of internal state beyond what _handle_server_message performs on dispatched messages).

Formally: let R be the set of messages yielded by successive _next_message calls before termination.  k  0 such that messages R[0..k-1] are non-matching ( i < k: R[i].get('id')  request_id  'method'  R[i]) and each was consumed by _handle_server_message, and either (a) R[k] matches and error is falsy  return R[k].get('result'), or (b) R[k] matches and error is the content-modified dict  raise _ContentModifiedError, or (c) R[k] matches and error is otherwise truthy  raise RuntimeError, or (d) no R[k] exists because _next_message raised before yielding it  that exception propagates. In all branches, wall-clock(monotonic)  deadline at the instant of exit.

---

## Code Evidence

Line 6: if error:

---

## Trigger Condition

The truthiness guard `if error:` on Line 6 conflates 'the error key is absent' (message.get returns None) with 'the error key is present but holds a falsy value' (e.g. {}, 0, "", [], False). In JSON-RPC a response carries either a "result" member (success) or an "error" member (failure); the presence of the "error" key is what makes the response an error response. When the server sends {"id": 1, "error": {}}, the empty dict is falsy in Python, so the code skips both the _ContentModifiedError and RuntimeError branches and returns message.get("result")  None, silently treating a server-error response as a successful result-less reply. The specification requires every server error to be raised as an exception ('every other server error is raised under a different exception class') and explicitly states 'Failure is never signaled through a sentinel return value.' The fix would be to test for key presence (e.g. `if "error" in message:`) rather than truthiness of the value.

---

## How to trigger the bug

`ElpClient._wait_for_response` (reachable through the public `ElpClient.request`
API in `src/languages/erlang.py`) decides whether a received JSON-RPC message is
an error response by testing the **truthiness** of `message.get("error")`
instead of the **presence** of the `"error"` key. When the ELP server replies
with an error response whose `error` value is falsy (here the empty dict `{}`),
the guard `if error:` fails, both error branches (`_ContentModifiedError` for
code `-32801` and the generic `RuntimeError`) are skipped, and the method
returns `message.get("result")` — `None` — silently reporting a server error as
a successful result-less reply. The specification requires that every server
error be raised as an exception and that failure is never signaled through a
sentinel return value.

### Inputs

| Parameter | Value |
|-----------|-------|
| Server message queued on the client transport | `{"jsonrpc": "2.0", "id": 1, "error": {}}` |
| `request_id` assigned by `ElpClient.request` | `1` (first request) |
| `method` passed to `request()` | `"elp/version"` |
| `deadline` | `time.monotonic() + 5` (no timeout involvement) |

### Expected (spec-correct) Output

`raises RuntimeError("ELP request failed: {}")` (any exception class distinct from `_ContentModifiedError`) — every server error must be raised; failure is never a sentinel return value.

### Actual (buggy) Output

`None` — the error response is consumed and treated as a successful result-less reply.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point; the transport is mocked so no ELP subprocess or FM-Agent workflow is started):

```python
import sys
import tempfile

sys.path.insert(0, ".")
from src.languages.erlang import ElpClient


class FakeStdin:
    def write(self, d): return len(d)
    def flush(self): pass


class FakeProc:
    def __init__(self): self.stdin = FakeStdin()


client = ElpClient(tempfile.mkdtemp(prefix="elp_repro_"))
client.timeout = 5
client._proc = FakeProc()  # mocked transport sink (no real ELP process)
client._messages.put({"jsonrpc": "2.0", "id": 1, "error": {}})
result = client.request("elp/version", {})
print(result)
# actual (buggy) output: None
# expected (correct) output: RuntimeError raised ("ELP request failed: {}")
```

---

## Probe Script

```py
"""Probe for bug src--languages--erlang-py--ElpClient::_wait_for_response.

Trigger (from gap report): the guard `if error:` in ElpClient._wait_for_response
tests the truthiness of message.get("error") instead of the presence of the
"error" key. When the ELP server replies with a JSON-RPC error response whose
error value is falsy — e.g. {"jsonrpc": "2.0", "id": 1, "error": {}} — the empty
dict is falsy, so both error branches (content-modified and generic RuntimeError)
are skipped and the method returns message.get("result") == None, silently
treating a server-error response as a successful result-less reply.

Spec oracle: every server error must be raised as an exception ("every other
server error is raised under a different exception class") and "Failure is never
signaled through a sentinel return value."

This probe drives the public ElpClient.request() API (the smallest public method
that reaches _wait_for_response) with the transport mocked — no ELP subprocess,
no FM-Agent workflow is started. The fixture response is injected into the
client's message queue; all fixtures live in a fresh temporary directory.
"""

import sys
import tempfile
from pathlib import Path

# Repo root = two levels above fm_agent/bug_validation/ (this probe lives there).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.languages.erlang import ElpClient

# Fresh probe-owned workspace (never the active repo / fm_agent directory).
WORKDIR = tempfile.mkdtemp(prefix="elp_wait_probe_")


class _FakeStdin:
    """Captures frames the client would send to the ELP server."""

    def __init__(self):
        self.data = bytearray()

    def write(self, chunk):
        self.data.extend(chunk)
        return len(chunk)

    def flush(self):
        pass


class _FakeProc:
    def __init__(self):
        self.stdin = _FakeStdin()


def request_with_server_response(server_message):
    """Run ElpClient.request() end-to-end without spawning a real ELP process."""
    client = ElpClient(WORKDIR)
    client.timeout = 5
    client._proc = _FakeProc()  # mocked transport sink
    client._messages.put(server_message)  # pre-queue the server's reply
    return client.request("elp/version", {"probe": True})


def main():
    # JSON-RPC response with the "error" key present but holding a falsy
    # empty dict — per JSON-RPC the presence of "error" makes it an error
    # response, so the client must raise.
    try:
        actual = request_with_server_response(
            {"jsonrpc": "2.0", "id": 1, "error": {}}
        )
    except TimeoutError as exc:
        print(f"ERROR: unexpected timeout (probe fixture problem): {exc}")
        sys.exit(1)
    except Exception as exc:
        # Spec-correct outcome: the server error is raised as an exception.
        print(
            "NOT CONFIRMED — server error response {'error': {}} raised "
            f"{type(exc).__name__}: {exc}"
        )
        return

    # Buggy outcome: no exception, sentinel None returned for an error response.
    if actual is None:
        print(
            "CONFIRMED — actual: None (silent sentinel for a server-error "
            "response) | expected: an exception raised for "
            "{'jsonrpc': '2.0', 'id': 1, 'error': {}}"
        )
    else:
        print(f"NOT CONFIRMED — actual: {actual!r}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: None (silent sentinel for a server-error response) | expected: an exception raised for {'jsonrpc': '2.0', 'id': 1, 'error': {}}
```
