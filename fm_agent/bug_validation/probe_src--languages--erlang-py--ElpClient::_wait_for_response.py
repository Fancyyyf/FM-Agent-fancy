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
