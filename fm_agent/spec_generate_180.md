# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::languages::erlang-py::ElpClient::notify` (language: `python`).
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
def notify(self, method: str, params: dict | list | None = None):
        actual_params = {} if params is None else params
        self._send({"jsonrpc": "2.0", "method": method, "params": actual_params})
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

### src::languages::erlang-py::ElpClient::open_document

# [SPEC]
# Unit: src/languages/erlang.py
#
# ElpClient.open_document(self, path: str, source: str | None = None)
#
# Pre-condition:
#   - self is an ElpClient whose underlying JSON-RPC communication channel
#     is open and writable
#   - path is a non-empty string identifying a filesystem path
#   - When source is None, path must resolve to an existing, readable
#     text file
#
# Post-condition:
#   - Transmits a "textDocument/didOpen" notification to the ELP server
#     whose textDocument field is a dict containing:
#       - uri: the absolute file:// URI representing the path argument
#       - languageId: "erlang"
#       - version: 1
#       - text: source when source is provided; otherwise the UTF-8 text
#         content of the file at path
#   - When source is None and the file at path cannot be read, the
#     underlying IOError propagates to the caller
# [SPEC]

## What callers expect from this function (from their [INFO] blocks)

Your generated [SPEC] must be consistent with these expectations.

### According to src::languages::erlang-py::ElpClient::initialize

# notify(self, method: str, params: dict | list | None = None)
#   Pre-condition: self._proc.stdin is open and writable; method is a
#     non-empty string; params, when provided, is a JSON-serializable
#     dict or list
#   Post-condition: Sends a JSON-RPC notification with the given method
#     and params (defaulting to {} when params is None) to the ELP server;
#     no response is expected or awaited; raises RuntimeError when the
#     client is not running

### According to src::languages::erlang-py::ElpClient::open_document

# notify(self, method: str, params: dict | list | None = None)
#   Pre-condition: The underlying JSON-RPC communication channel is open
#     and writable
#   Post-condition: A JSON-RPC 2.0 notification message (a message
#     without an id field) carrying the given method and params is
#     transmitted to the ELP server; when params is None, the transmitted
#     params is an empty dict

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. Because this function has callees, also produce an [INFO] block recording the expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` block only, markers included, every line prefixed with `#`), and list the names of the callees you recorded.
4. Write your answer to `fm_agent/spec_generate_180.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
