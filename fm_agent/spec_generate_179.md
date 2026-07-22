# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::languages::erlang-py::ElpClient::_wait_for_response` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: __init__, _handle_server_message, _next_message.

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
def _wait_for_response(self, request_id: int, deadline: float):
        while True:
            message = self._next_message(deadline)
            if message.get("id") == request_id and "method" not in message:
                error = message.get("error")
                if error:
                    if isinstance(error, dict) and error.get("code") == _CONTENT_MODIFIED_ERROR:
                        raise _ContentModifiedError(error)
                    raise RuntimeError(f"ELP request failed: {error}")
                return message.get("result")
            self._handle_server_message(message)
```

## Specs of this function's callers

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

### According to src::languages::erlang-py::ElpClient::request

# _wait_for_response(self, request_id: int, deadline: float) -> dict
#   Pre-condition: A request with the given integer request_id was
#     previously transmitted over the same channel; deadline is a monotonic
#     time value representing an absolute time point
#   Post-condition: Blocks until a JSON-RPC response message carrying a
#     matching id field arrives from the server; returns the parsed response
#     as a dict; when the channel closes or the server produces no matching
#     response before deadline, raises TimeoutError; when the server reports
#     a protocol error, raises _ContentModifiedError for transient errors or
#     RuntimeError for other errors, with the error details attached

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. Because this function has callees, also produce an [INFO] block recording the expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` block only, markers included, every line prefixed with `#`), and list the names of the callees you recorded.
4. Write your answer to `fm_agent/spec_generate_179.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
