# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::languages::erlang-py::ElpClient::_handle_server_message` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: _send.

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
def _handle_server_message(self, message: dict):
        method = message.get("method")
        params = message.get("params")
        if params is None:
            params = {}
        if method == "elp/status":
            self._status = params.get("status")
        if "id" not in message or not method:
            return

        if method == "workspace/configuration":
            result = [None for _ in params.get("items", [])]
        elif method == "workspace/workspaceFolders":
            result = [{"uri": self.root_uri, "name": os.path.basename(self.proj_dir)}]
        elif method == "workspace/applyEdit":
            result = {"applied": False}
        else:
            result = None
        self._send({"jsonrpc": "2.0", "id": message["id"], "result": result})
```

## Specs of this function's callers

### src::languages::erlang-py::ElpClient::initialize

# [SPEC]
# Unit: src/languages/erlang.py
#
# ElpClient.initialize(self, bootstrap_path: str, bootstrap_source: str | None = None)
#
# Pre-condition:
#   - self is an ElpClient whose __enter__ has been called (ELP subprocess is
#     running, stdin/stdout pipes are open, and the JSON-RPC message reader
#     thread is active)
#   - bootstrap_path is a non-empty string identifying a filesystem path; if
#     bootstrap_source is None, bootstrap_path must resolve to an existing,
#     readable text file
#   - bootstrap_source, when provided, is a string containing the document
#     content to use instead of reading from bootstrap_path
#
# Post-condition:
#   - Completes the LSP initialization handshake: sends the "initialize"
#     request with client capabilities, then sends the "initialized"
#     notification
#   - Opens the document at bootstrap_path on the server with the text content
#     matching bootstrap_source (or the file contents of bootstrap_path when
#     bootstrap_source is None)
#   - Blocks until the server's reported status indicates it has reached a
#     running state, or raises TimeoutError when that does not occur within
#     self.timeout seconds measured from the call entry
#   - Returns the "serverInfo" sub-dict from the server's "initialize"
#     response, or None when the response is missing, is not a dict, or does
#     not contain a "serverInfo" key
#   - Raises RuntimeError when the ELP subprocess is not running (stdin
#     unavailable) or the JSON-RPC channel encounters an unrecoverable error
#   - Raises TimeoutError when the server fails to reach the running state
#     within the deadline or the subprocess stops producing messages
# [SPEC]

## What callers expect from this function (from their [INFO] blocks)

Your generated [SPEC] must be consistent with these expectations.

### According to src::languages::erlang-py::ElpClient::initialize

# _handle_server_message(self, message: dict)
#   Pre-condition: message is a dict representing a parsed JSON-RPC
#     message received from the server
#   Post-condition: If the message method is "elp/status", updates
#     self._status to the value of params.status (retaining the previous
#     value when params is absent or lacks a "status" key); when the
#     message carries both an "id" and a "method" (a server request),
#     sends back a JSON-RPC response whose "result" value satisfies the
#     server's expectation for that request method; when the message has
#     no "id" (a notification), no response is sent

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. Because this function has callees, also produce an [INFO] block recording the expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` block only, markers included, every line prefixed with `#`), and list the names of the callees you recorded.
4. Write your answer to `fm_agent/spec_generate_131.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
