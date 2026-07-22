# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::languages::erlang-py::ElpClient::_send` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: flush, write.

## Developer intent

# Incremental self-validation intent

Validate all behavioral and correctness impacts introduced between the recorded
FM-Agent baseline and the current checked-out main-derived revision. Regenerate
specifications for changed or relevant functions and verify affected callers.
Pay particular attention to file readiness, incremental reasoning, CLI backend,
codegraph integration, tracing, environment checks, and pipeline setup changes.
Do not modify project source files; write validation artifacts only under the
FM-Agent workspace.

## Function source

```python
def _send(self, message: dict):
        if self._proc is None or self._proc.stdin is None:
            raise RuntimeError("ELP client is not running")
        payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        frame = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii") + payload
        with self._write_lock:
            self._proc.stdin.write(frame)
            self._proc.stdin.flush()
```

## Specs of this function's callers

### src::languages::erlang-py::ElpClient::_handle_server_message

# [SPEC]
# Unit: src/languages/erlang.py
#
# ElpClient._handle_server_message(self, message: dict)
#
# Pre-condition:
#   - self is an ElpClient whose __enter__ has been called (ELP subprocess
#     is running and the JSON-RPC message reader thread is active)
#   - message is a dict representing a parsed JSON-RPC message received
#     from the ELP server
#
# Post-condition:
#   - When message.method is "elp/status", updates self._status to the
#     value of message.params.status; if the params dict is absent or lacks
#     a "status" key, self._status is unchanged
#   - When message lacks an "id" field, or message.method is absent or
#     falsy, no response is sent (the message is treated as a notification)
#   - When message carries both a non-empty "method" and an "id" (a server
#     request), sends a JSON-RPC response with jsonrpc "2.0" and the same
#     id; the result value satisfies the protocol-defined expectation for
#     that method:
#     - For workspace configuration queries: result is a list whose length
#       equals the number of requested configuration items, each element
#       being null
#     - For workspace folder queries: result is a singleton list containing
#       the workspace-folder descriptor with the project root URI and
#       directory name
#     - For workspace edit requests: result indicates the edit was declined
#       (applied is false)
#     - For any other method the client does not handle: result is null
# [SPEC]

### src::languages::erlang-py::ElpClient::notify

# [SPEC]
# Unit: src/languages/erlang.py
#
# ElpClient.notify(self, method: str, params: dict | list | None = None)
#
# Pre-condition:
#   - self._proc is not None and self._proc.stdin is open and writable
#   - method is a non-empty string identifying a known LSP notification method
#   - params, when not None, is a JSON-serializable dict or list
#
# Post-condition:
#   - Transmits a JSON-RPC 2.0 notification message to the ELP subprocess's
#     standard input
#   - The transmitted message is a JSON object containing "jsonrpc": "2.0",
#     "method" set to the method argument, and no "id" member
#   - When params is None, the transmitted "params" is an empty JSON object;
#     otherwise "params" is set to the params argument value unchanged
#   - No response from the server is awaited
#   - Raises RuntimeError when the ELP subprocess is not running or stdin
#     is unavailable
# [SPEC]

### src::languages::erlang-py::ElpClient::request

# [SPEC]
# Unit: src/languages/erlang.py
#
# ElpClient.request(self, method: str, params: dict | list | None = None) -> Any
#
# Pre-condition:
#   - self is an ElpClient whose underlying JSON-RPC communication channel
#     is open and operational
#   - method is a non-empty string
#   - params, when not None, is a JSON-serializable dict or list
#
# Post-condition:
#   - Transmits a JSON-RPC 2.0 request to the server with the given method
#     and params (where None params is treated as an empty object), tagged
#     with a unique integer identifier that is strictly increasing across
#     successive calls on the same client instance
#   - Blocks the caller until the server returns a response matching that
#     identifier or until the total elapsed time since entry reaches
#     self.timeout seconds, whichever occurs first
#   - On success: returns the value of the "result" field from the matching
#     response
#   - When the server indicates a transient ContentModified error: re-issues
#     the request up to a fixed maximum number of total attempts, bounded in
#     total duration by self.timeout seconds from entry; when all attempts
#     are exhausted without success, raises RuntimeError identifying the
#     failing method
#   - When no matching response arrives before self.timeout seconds elapse
#     from entry: raises TimeoutError
#   - When the server responds with an error whose semantics are not covered
#     by the retry policy: raises RuntimeError
# [SPEC]

## What callers expect from this function (from their [INFO] blocks)

Your generated [SPEC] must be consistent with these expectations.

### According to src::languages::erlang-py::ElpClient::_handle_server_message

# _send(self, message: dict)
#   Pre-condition: self is an ElpClient whose stdin pipe to the ELP
#     subprocess is open and writable; message is a dict representing a
#     well-formed JSON-RPC message to be delivered to the server
#   Post-condition: The JSON-serialized form of message has been written
#     to the subprocess's stdin, following the LSP transport protocol
#     framing; the server will receive the complete message as its next
#     input

### According to src::languages::erlang-py::ElpClient::notify

# _send(self, message: dict)
#   Pre-condition: self._proc is not None and self._proc.stdin is open and
#     writable; message is a JSON-serializable dict
#   Post-condition: The message is serialized to UTF-8 JSON, framed with a
#     Content-Length header, and written to the ELP subprocess's standard input
#     stream; raises RuntimeError when the subprocess is not running or stdin
#     is unavailable

### According to src::languages::erlang-py::ElpClient::request

# _send(self, request: dict)
#   Pre-condition: The underlying JSON-RPC output channel is open and
#     writable; request is a dict representing a complete JSON-RPC 2.0
#     request message
#   Post-condition: The request is serialized to JSON and transmitted over
#     the output channel; on return the server has received the request

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. Because this function has callees, also produce an [INFO] block recording the expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` block only, markers included, every line prefixed with `#`), and list the names of the callees you recorded.
4. Write your answer to `fm_agent/spec_generate_220.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
