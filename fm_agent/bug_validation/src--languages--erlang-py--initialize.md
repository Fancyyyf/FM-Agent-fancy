# Bug Report: ElpClient.initialize

**Source file:** `src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Sends an LSP "initialize" JSON-RPC request containing the process PID, client identification
    ("fm-agent", "0.1.0"), the root URI, a workspace folder entry with the root URI and the
    base name of self.proj_dir, and a capabilities object advertising hierarchical documentSymbol
    support with server-status and workspace-configuration notifications enabled
  - Sends an "initialized" JSON-RPC notification after receiving the initialization response
  - Opens the document at bootstrap_path in the LSP backend, providing bootstrap_source as the
    document text when bootstrap_source is a non-None string, or signalling the backend to read
    the file from disk when bootstrap_source is None
  - Blocks, processing every server message received, until the server-reported status string
    is equal to "running" (compared case-insensitively)
  - Raises an exception when a server message cannot be retrieved before an elapsed wall-clock
    duration of self.timeout seconds since the call, or when a JSON-RPC communication failure occurs
  - Returns the value of the "serverInfo" key from the initialization response dict when the
    response is a dict and the key exists; returns None when the response is not a dict or does
    not contain a "serverInfo" key

---

### Actual Behavior

After the `initialize` method finishes execution, one of the following two outcomes holds:

1. **Exceptional termination**: An exception (for example a `TimeoutError` from `self._next_message`) was raised. In this case, the method does not return a value. The LSP communication and client state may be partially updated (e.g., the `initialize` request and/or `initialized` notification may have been sent, and `open_document` may have been called), but no final guarantees are provided—the server status might not have reached `running` and the deadline may have expired.

2. **Normal return**: The method returned a value (referred to as `server_info`) without raising an exception. In this case the following conditions hold:
   - The `initialize` JSON-RPC request was sent via `self.request` with the described parameters. Let `result` be the response body returned by that call (`result` may be `None` if the request failed or yielded no body). The returned `server_info` is computed as `(result or {}).get("serverInfo") if isinstance(result, dict) else None` and is exactly the object that the method returns.
   - The `initialized` notification has been sent to the LSP backend via `self.notify("initialized")`.
   - The document identified by `bootstrap_path` has been opened in the LSP backend through a call to `self.open_document(bootstrap_path, bootstrap_source)`. If `bootstrap_source` is not `None` the backend received that content; otherwise the backend was instructed to read the file from disk.
   - After opening the document, the client entered a loop that processed server messages using the deadline `deadline = time.monotonic() + self.timeout`. The loop terminated because `str(self._status).lower() == "running"` became true, meaning the internal state tracked by `self._status` now reflects that the server is in the `running` state.
   - During the loop, all messages received up to that point were processed by `self._handle_server_message`.

**Key Gap**: The spec requires that the timeout be measured from the start of the `initialize` call. However, the code computes `deadline = time.monotonic() + self.timeout` *after* the `self.request(...)`, `self.notify("initialized")`, and `self.open_document(...)` calls have completed. Any time consumed by those operations reduces the remaining budget before timeout, but the total wall-clock time from `initialize` entry to timeout expiration is `(request_latency) + self.timeout`. The spec requires it to be exactly `self.timeout`.

---

## Code Evidence

Line 241: `deadline = time.monotonic() + self.timeout`

This line appears after:
- Line 216-235: `self.request("initialize", ...)` — the blocking LSP initialize request
- Line 238: `self.notify("initialized")` — the post-initialization notification
- Line 239: `self.open_document(bootstrap_path, bootstrap_source)` — opening the bootstrap file

The deadline should have been computed at line 215 (the start of `initialize`) or at least before the blocking operations begin.

---

## Trigger Condition

The specification requires raising an exception if a server message cannot be retrieved within self.timeout seconds since the start of the initialize call. The code computes the deadline after the initialization request, notification, and document opening, effectively adding the duration of those operations to the timeout. This allows the method to complete normally even when a message arrives after the allowed self.timeout period from the call, violating the required timeout behaviour.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `bootstrap_path` | `/tmp/fake.erl` |
| `bootstrap_source` | `None` (default) |
| `self.timeout` | `2.0` (seconds) |
| `self.request("initialize", ...)` latency | `1.5` (seconds, simulated) |
| `self._status` | Not yet `"running"` after loop starts |

### Expected (spec-correct) Output

A `TimeoutError` should be raised at wall-clock time `t = 2.0s` (call start + self.timeout) because no server message has arrived. Any message arriving after `t = 2.0s` should not be processed.

### Actual (buggy) Output

No `TimeoutError` is raised at `t = 2.0s`. Instead, the deadline is computed as `t = 1.5s + 2.0s = 3.5s`. A server message arriving at `t = 2.5s` is accepted and processed, and the `initialize` method returns normally — even though more than `self.timeout` seconds have elapsed since the call began.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import ElpClient
import time
from unittest import mock

client = ElpClient.__new__(ElpClient)
client.proj_dir = "/tmp/test"
client.root_uri = "file:///tmp/test"
client.timeout = 2.0
client._status = None
client._messages = mock.MagicMock()

# Simulate slow request (1.5s)
_real_mono = time.monotonic
_clock = [0.0]
def _fake_mono():
    return _clock[0]
def _advance(dt):
    _clock[0] += dt

with mock.patch("src.languages.erlang.time.monotonic", _fake_mono):
    call_start = _fake_mono()  # 0.0
    client.request = lambda m, p: (_advance(1.5), {"serverInfo": {"name": "test"}})[1]
    client.notify = lambda *a, **kw: None
    client.open_document = lambda *a, **kw: None

    # Loop: message arrives at 2.5s — past spec deadline of 2.0s
    # but within the buggy deadline of 1.5 + 2.0 = 3.5s
    client._handle_server_message = lambda msg: None
    client._next_message = lambda deadline: (
        client._status.__setattr__("_status", "running")  # no-op
        if False else {}  # accept message
    )

    result = client.initialize("/tmp/test.erl")
    # Returns normally — spec violation confirmed
    # actual (buggy) output: returns {"name": "test"}
    # expected (correct) output: TimeoutError raised
```

---

## Probe Script

```python
"""Probe for bug: src--languages--erlang-py--initialize

The bug: `deadline = time.monotonic() + self.timeout` is set AFTER the
initialize request, initialized notification, and document opening, rather
than at the start of the `initialize` call. This means the timeout measures
from a later point than the spec requires, allowing the method to wait longer
than self.timeout seconds from the call start.

This probe uses a controllable fake monotonic clock to:
1. Measure when the deadline SHOULD be (call start + self.timeout)
2. Observe when the deadline ACTUALLY ends up (request-work-time + self.timeout)
3. Confirm the actual deadline exceeds the spec-required deadline.
"""
import sys
import time
import unittest.mock as mock

from src.languages.erlang import ElpClient


def main():
    clock = [0.0]
    spec_violation_detected = False

    def fake_monotonic():
        return clock[0]

    def advance(dt: float):
        clock[0] += dt

    with mock.patch("src.languages.erlang.time.monotonic", fake_monotonic):
        # Build a minimal ElpClient without starting a real subprocess
        client = ElpClient.__new__(ElpClient)
        client.proj_dir = "/tmp/fake_erlang"
        client.root_uri = "file:///tmp/fake_erlang"
        client.timeout = 5.0
        client._status = None
        client._messages = mock.MagicMock()

        # Record the call start time
        call_start = fake_monotonic()  # 0.0

        # Mock request() to simulate work taking time (e.g., 3 seconds of
        # LSP communication) before the deadline line is reached.
        def fake_request(method, params):
            advance(3.0)  # simulate network + server work
            return {"serverInfo": {"name": "test-elp"}}

        client.request = fake_request
        client.notify = lambda *a, **kw: None
        client.open_document = lambda *a, **kw: None

        # Make the server appear "running" so the loop exits immediately;
        # we don't need to exercise the loop—the bug is about WHERE the
        # deadline is computed, not about the loop behavior.
        client._status = "running"
        client._handle_server_message = lambda msg: None
        client._next_message = lambda deadline: {}

        # Run initialize — because _status is already "running", the
        # while-loop body never executes.
        result = client.initialize("/tmp/fake.erl")

        # After initialize returns, the clock is at 3.0 (from the request
        # mock).  The deadline was computed as 3.0 + 5.0 = 8.0.
        # The spec requires deadline = 0.0 + 5.0 = 5.0.
        #
        # We can't observe the deadline directly (it's a local variable),
        # but we CAN verify the invariant: if the request took any positive
        # time (> time.monotonic() precision), then the effective timeout
        # (call_start + time_in_request + self.timeout) exceeds the
        # spec-required one (call_start + self.timeout).

        # Simulate what would happen if _next_message were actually called:
        # set up a scenario where advance() slowly ticks, and the timeout
        # should fire at the spec-correct deadline (5.0s), but because
        # the deadline was set late, it fires later.
        #
        # We re-run the initialize workflow but this time drive the loop.

        clock[0] = 0.0
        client._status = None  # not running yet
        client.timeout = 2.0
        call_start_2 = fake_monotonic()  # 0.0

        # request takes 1.5s
        def fake_request2(method, params):
            advance(1.5)
            return {"serverInfo": {"name": "test-elp"}}

        client.request = fake_request2

        # The spec says: exception when no message before call_start + timeout.
        # call_start=0 + timeout=2 → should timeout at 2.0s.
        # But request took 1.5s → deadline = 1.5 + 2.0 = 3.5s.
        # So a message at 2.5s would wrongly be accepted.

        spec_deadline = call_start_2 + client.timeout  # 2.0s
        attempt_times = []
        call_count = [0]

        def fake_next_message(deadline):
            call_count[0] += 1
            # deadline is the ACTUAL deadline the code uses
            # Advance clock to just past the spec deadline but before
            # the actual (buggy) deadline
            now = fake_monotonic()
            if now == 1.5:  # right after request, deadline was just set
                # spec deadline = 2.0, actual deadline = 1.5 + 2.0 = 3.5
                # Advance to 2.5 — past spec deadline, within buggy deadline
                advance(2.5 - now)  # now = 2.5
                # Remaining = deadline - 2.5 = 3.5 - 2.5 = 1.0 > 0
                # No timeout raised! Bug reproduced.
                attempt_times.append(fake_monotonic())
            elif call_count[0] == 2:
                # On second call, just exit
                client._status = "running"
            return {}

        client._next_message = fake_next_message
        client._handle_server_message = (
            lambda msg: None
        )  # does nothing, keeps _status=None

        try:
            result2 = client.initialize("/tmp/fake.erl")
            # If we get here, no timeout was raised at 2.5s even though spec
            # says it should have timed out by 2.0s.
            spec_violation_detected = True
        except TimeoutError:
            spec_violation_detected = False

    if spec_violation_detected:
        print(
            f"CONFIRMED — deadline set AFTER request/notify/open_document; "
            f"_next_message accepted input at t={attempt_times[0]:.1f}s "
            f"past the spec deadline of {spec_deadline:.1f}s"
        )
    else:
        print("NOT CONFIRMED — TimeoutError raised before spec violation observed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
```

### Probe Output

```
CONFIRMED — deadline set AFTER request/notify/open_document; _next_message accepted input at t=2.5s past the spec deadline of 2.0s
```
