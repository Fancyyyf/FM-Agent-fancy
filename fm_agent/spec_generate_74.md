# Generate Function Specification

A modification has been applied to a codebase to achieve the developer intent below, adding a function that has no behavioral specification yet. Generate its specification from scratch.

- Function fully-qualified name: `src::languages::erlang-py::ElpClient::__init__` (language: `python`).
- Comment prefix for this language: `#`.
- Known callees of this function: _timeout_seconds.

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
def __init__(self, proj_dir: str):
        self.proj_dir = os.path.abspath(proj_dir)
        self.root_uri = Path(self.proj_dir).as_uri()
        self.timeout = _timeout_seconds()
        self._messages: queue.Queue = queue.Queue()
        self._next_id = 1
        self._status = None
        self._write_lock = threading.Lock()
        self._proc = None
        self._reader = None
```

## Specs of this function's callers

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

### According to src::languages::erlang-py::_analyze_project_uncached

# ErlangAnalysis.__init__(functions: dict = {}, edges: dict = {}, spans: dict = {}, server_info: Any = None) -> ErlangAnalysis
#   Pre-condition: parameters are valid dicts and optional server info
#   Post-condition: creates an ErlangAnalysis instance with the given attributes

## Steps

1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format rules used by this project.
2. Produce the COMPLETE [SPEC] block describing this function's behavior — the `[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with `#`, and NO source code.
3. Because this function has callees, also produce an [INFO] block recording the expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` block only, markers included, every line prefixed with `#`), and list the names of the callees you recorded.
4. Write your answer to `fm_agent/spec_generate_74.json` as a JSON object with keys:
   - "spec_updated": boolean — true when you produced a [SPEC] block.
   - "new_spec": string — the full [SPEC] block.
   - "info_updated": boolean — true when you produced an [INFO] block.
   - "new_info": string — the full [INFO] block, or "" if none.
   - "updated_callees": array of callee name strings recorded in [INFO], or [].
   Write ONLY that JSON file; do not modify any other project files.
