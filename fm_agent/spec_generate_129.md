# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::languages::erlang-py::ElpClient::request` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: _send, _wait_for_response.

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
def request(self, method: str, params: dict | list | None = None):
        actual_params = {} if params is None else params
        deadline = time.monotonic() + self.timeout
        for attempt in range(_MAX_CONTENT_MODIFIED_RETRIES):
            request_id = self._next_id
            self._next_id += 1
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": method,
                    "params": actual_params,
                }
            )
            try:
                return self._wait_for_response(request_id, deadline)
            except _ContentModifiedError as exc:
                if attempt + 1 == _MAX_CONTENT_MODIFIED_RETRIES:
                    raise RuntimeError(
                        f"ELP request {method} repeatedly failed: {exc.error}"
                    ) from exc
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"timed out retrying ELP request {method}") from exc
                time.sleep(min(0.5 * (2**attempt), 5.0, remaining))
        raise AssertionError("unreachable")
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

### src::languages::erlang-py::_analyze_project_uncached

# [SPEC]
# Unit: src/languages/erlang-py/_analyze_project_uncached.py
#
# _analyze_project_uncached(proj_dir: str) -> ErlangAnalysis
#
# Pre-condition:
#   - proj_dir is a non-empty string representing a filesystem path
#
# Post-condition:
#   - Returns an ErlangAnalysis object whose .functions attribute is a dict
#     mapping each .erl file absolute path to a list of (function_id, source_text)
#     tuples, where function_id is a canonical string identifier and source_text
#     is the source code of that function
#   - Returns an ErlangAnalysis whose .edges attribute is a dict mapping
#     (function_id, caller_module) tuples to sets of callee function_ids
#   - Returns an ErlangAnalysis whose .spans attribute is a dict mapping each
#     .erl file absolute path to a list of (function_id, start_line, end_line)
#     tuples, where start_line and end_line are 1-based inclusive line numbers
#   - Returns an ErlangAnalysis whose .server_info attribute is populated from
#     the ELP server initialization response
#   - When no .erl files exist under the directory tree rooted at proj_dir after
#     resolution to an absolute path, returns an ErlangAnalysis with all three
#     dict attributes empty
#   - Raises an exception when the ELP backend process cannot be started, the LSP
#     communication channel fails, or the project at proj_dir cannot be analyzed
# [SPEC]

## What callers expect from this function (from their [INFO] blocks)

Your generated [SPEC] must be consistent with these expectations.

### According to src::languages::erlang-py::ElpClient::initialize

# request(self, method: str, params: dict | list | None = None)
#   Pre-condition: self._proc.stdin is open and writable; method is a
#     non-empty string; params, when provided, is a JSON-serializable
#     dict or list
#   Post-condition: Sends a JSON-RPC request with a unique monotonically
#     increasing integer id and the given method and params (defaulting to
#     {} when params is None); blocks until the matching response arrives;
#     returns the "result" field of the response; raises RuntimeError when
#     the server responds with a non-ContentModified error; raises
#     TimeoutError when the response does not arrive within self.timeout
#     seconds; retries automatically up to a fixed maximum on
#     ContentModified errors and raises RuntimeError when all retries are
#     exhausted

### According to src::languages::erlang-py::_analyze_project_uncached

# ElpClient.request(method: str, params: dict) -> Any | None
#   Pre-condition: method is an LSP method name, params is a payload dict
#   Post-condition: Returns the parsed JSON response from the server, or None when no response/error

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. Because this function has callees, also produce an [INFO] block recording the expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` block only, markers included, every line prefixed with `#`), and list the names of the callees you recorded.
4. Write your answer to `fm_agent/spec_generate_129.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
