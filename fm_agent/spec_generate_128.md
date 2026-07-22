# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::languages::erlang-py::ElpClient::open_document` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: notify.

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
def open_document(self, path: str, source: str | None = None):
        document = Path(path).resolve()
        if source is None:
            source = document.read_text(encoding="utf-8", errors="replace")
        self.notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": document.as_uri(),
                    "languageId": "erlang",
                    "version": 1,
                    "text": source,
                }
            },
        )
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

# open_document(self, path: str, source: str | None = None)
#   Pre-condition: self._proc.stdin is open and writable; path is a
#     non-empty string identifying a filesystem path; when source is None,
#     path must resolve to an existing readable text file
#   Post-condition: The document at path is registered with the ELP server
#     via a "textDocument/didOpen" notification carrying the resolved
#     absolute URI, language identifier "erlang", version 1, and the text
#     content (source when provided, otherwise the UTF-8 contents of the
#     file at path); when source is None and the file cannot be read, the
#     underlying IOError propagates

### According to src::languages::erlang-py::_analyze_project_uncached

# ElpClient.open_document(path: str, text: str) -> None
#   Pre-condition: path is a file path, text is the document source
#   Post-condition: Notifies the language server that the document is open

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. Because this function has callees, also produce an [INFO] block recording the expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` block only, markers included, every line prefixed with `#`), and list the names of the callees you recorded.
4. Write your answer to `fm_agent/spec_generate_128.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
