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
