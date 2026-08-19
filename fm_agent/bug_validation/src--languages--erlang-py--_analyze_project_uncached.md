# Bug Report: _analyze_project_uncached

**Source file:** `src/languages/erlang-py/_analyze_project_uncached.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the fully populated Erlang analysis record, built fresh from the project's current on-disk Erlang sources at call time without consulting any previously recorded or cached analysis state. The record's .functions maps the absolute path of each Erlang source file under the call-graph root that defines at least one detected function to that file's list of (function_id, body) pairs, where each function_id is the canonicalized, filesystem-safe and FQN-safe, module-qualified identifier of a function defined in that file and each identifier appears at most once within its file's list, and where each body is the decoded source text of that function extracted from the file's current contents, spanning exactly the function's reported source range; files with no detected functions have no entry at all in .functions, never an empty list. The record's .edges maps each detected caller function's canonicalized, module-qualified identity to the collection of canonicalized callee FQNs that the caller invokes, with caller and callee identifiers following the same canonicalized FQN scheme used for extracted function file names and only edges between functions defined under the project's call-graph root included; every detected function appears as a caller key, and its callee collection is empty exactly when the function invokes no known project function. The record's .spans maps the absolute path of each analyzed source file with detected functions to a non-empty list of (function identifier, start line, end line) triples using 0-based, inclusive line numbers, covering exactly the functions attributed to that file with one triple matching each corresponding entry of .functions by identifier; files with no detected functions have no entry at all in .spans, never an empty list. The record additionally carries the backend's self-reported server information when the analysis was produced through the backend and the backend supplied that information, and none when it was not. When the project contains no Erlang source files, returns a record whose .functions and .edges are empty dicts and whose .spans has no entries, and producing this empty record does not depend on backend availability. When analysis cannot be produced  the backend is unavailable, tooling is missing or incompatible, a protocol or analysis failure occurs, or any internal error arises  raises an exception rather than returning, and a partially populated record never surfaces through the return path. Does not modify the project's source files.

---

### Actual Behavior

The function _analyze_project_uncached terminates in exactly one of the following ways:

**Path 1  No Erlang source files (early return, lines 4-5):**
If _erlang_files(proj_dir) returns an empty list, the function immediately returns ErlangAnalysis(functions={}, edges={}). No analysis backend is contacted, no files are read beyond the directory enumeration, and no state external to the call is modified.

**Path 2  Normal completion with one or more Erlang source files:**
The function returns an ErlangAnalysis instance whose fields are populated as follows:
 Every Erlang source file under proj_dir (as enumerated by _erlang_files) is read exactly once into memory with UTF-8 decoding (replacement on error) and is registered in a single ELP analysis session.
 For each file, the analysis backend is queried for document symbols; only symbols whose kind equals _FUNCTION_KIND and that carry a usable source range are considered. Symbols yielding a malformed function identifier (ValueError from _function_id) are logged as warnings and skipped. Duplicate function identifiers within a single file (tracked via the per-file 'seen' set) are skipped.
 The returned ErlangAnalysis encodes (a) a 'functions' mapping from canonical function identifiers to their definition metadata, (b) an 'edges' mapping capturing caller-to-callee call-graph relationships, and (c) source-span information associating each function with its file and line range, all derived exclusively from the in-memory source texts supplied to the session.
 The result is deterministic for a fixed set of source-file contents: identical file contents yield identical ErlangAnalysis structures.
 The project directory tree is not modified; no files are created, written, or deleted.
 The ELP session is fully closed (the 'with' block guarantees __exit__ is called), releasing all backend resources.

**Path 3  Exception during file reading (lines 9-12):**
If any Path(path).read_text() raises OSError (e.g., permission denied, file deleted between enumeration and read), the exception propagates to the caller. No ELP session is opened. The project directory is unmodified.

**Path 4  Exception during ELP session establishment or document registration (lines 13-16):**
If ElpClient construction, client.initialize, or any client.open_document call raises (backend unavailable, incompatible tooling, protocol failure, readiness timeout, or transport error), the exception propagates. The 'with' statement ensures any partially constructed session is cleaned up. The project directory is unmodified. No ErlangAnalysis is returned.

**Path 5  Exception during per-file symbol queries or call-hierarchy resolution (lines 17 onward):**
If any client.request call raises (protocol error, transport/pipe I/O failure, server process termination, or response timeout), the exception propagates. The 'with' statement ensures session cleanup. The project directory is unmodified. No ErlangAnalysis is returned.

**Invariants holding on every path:**
 proj_dir is not modified; no files under it are created, altered, or removed.
 The local variable proj_dir is rebound to os.path.abspath(proj_dir), which equals the original value since the pre-condition states it is already absolute.
 No previously cached analysis result is consulted or updated (the function is explicitly 'uncached').
 The 'sources' dictionary, when constructed, maps each enumerated file path to its complete decoded text; this mapping is used verbatim for all backend interactions and is not persisted beyond the call.

Formally:
 termination of _analyze_project_uncached(proj_dir):
  ( f  _erlang_files(proj_dir))  result = ErlangAnalysis(functions={}, edges={})
   ( files  no exception)  result  ErlangAnalysis  result.functions  {fid | fid = _function_id(uri, name) for well-formed function symbols}  result.edges reflects resolved call-hierarchy edges  project_tree_unchanged(proj_dir)
   (exception raised)  project_tree_unchanged(proj_dir)  session_cleaned_up
    path: result does not depend on any prior cached state

---

## Code Evidence

Line 7:     edges: dict[tuple[str, str], set[str]] = {}

---

## Trigger Condition

The specification (Condition B) states: 'The record's .edges maps each detected caller function's canonicalized, module-qualified identity to the collection of canonicalized callee FQNs.' The _function_id post-condition confirms this identity is 'the single canonicalized, filesystem-safe and FQN-safe, module-qualified identifier string.' Thus the edges key must be a single str. However, line 7 declares edges as dict[tuple[str, str], set[str]], using a tuple of two strings as the key. This structural mismatch means the returned ErlangAnalysis.edges does not conform to the specified mapping type: a consumer expecting edges[function_id_string] will fail, because the code stores entries under tuple keys. No transformation back to a single-string key is visible in the code, and the type annotation governs the data structure that will be passed into the ErlangAnalysis constructor.

---

## How to trigger the bug

Any project containing at least one Erlang source file with at least one detected function triggers the bug: `_analyze_project_uncached` stores every caller entry of the returned `ErlangAnalysis.edges` under a `(function_id, caller_module)` tuple key (constructed at line 49 of the actual source `src/languages/erlang.py` as `caller_key = (function_id, caller_module)` and inserted at line 50 via `edges.setdefault(caller_key, set())`) instead of the single canonicalized, module-qualified FQN string required by the specification. The probe drives the real function through the package's public entry point (`src.languages.registry`, the central language dispatch registry whose erlang handler documents `call_edges(proj_dir) -> {caller_fqn: {callee_fqns}}`), using a mock `ElpClient` fixture because ELP is an external Erlang LSP binary (the FM-Agent self-validation guard requires testing the smallest unit with mocks, and no FM-Agent workflow is started). The fixture project contains one file, `greeter.erl`, defining `hello/0` which calls `world/0`; the mock backend reports the corresponding document symbol and call-hierarchy responses. The resulting edges mapping has exactly one key, and that key is the tuple `('greeter__hello__0', 'greeter-erl')` rather than the spec-required string `'greeter__hello__0'`. A consumer indexing edges by the canonical function-id string (as the spec and the registry contract both prescribe) finds no entry.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Fresh temporary directory containing a single Erlang fixture file |
| Fixture file | `greeter.erl`: `-module(greeter).` exporting `hello/0` and `world/0`, with `hello() -> world().` |
| ELP backend | Mock `ElpClient` returning: one function symbol (`name="hello/0"`, `kind=12` with valid range), `prepareCallHierarchy` item `{"uri": <greeter.erl uri>, "name": "hello/0"}`, and one outgoing call `{"to": {"uri": <greeter.erl uri>, "name": "world/0"}}` |
| Entry point | `registry.REGISTRY["erlang"].call_edges(proj_dir)` (public API of `src.languages.registry`) |

### Expected (spec-correct) Output

`{'greeter__hello__0': {'greeter__world__0'}}` — every edges key is a single canonicalized, filesystem-safe and FQN-safe, module-qualified identifier string.

### Actual (buggy) Output

`{('greeter__hello__0', 'greeter-erl'): {'greeter__world__0'}}` — the edges key is a `tuple[str, str]`, so `edges['greeter__hello__0']` raises `KeyError`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import os, tempfile
from pathlib import Path
from src.languages import registry
from src.languages import erlang as erlang_backend

proj_dir = tempfile.mkdtemp(prefix="fm_probe_erl_")
Path(proj_dir, "greeter.erl").write_text(
    "-module(greeter).\n-export([hello/0, world/0]).\n\n"
    "hello() -> world().\n\nworld() -> ok.\n", encoding="utf-8"
)

class FakeElpClient:  # stand-in for the external ELP LSP backend
    def __init__(self, proj_dir): self._uri = None
    def __enter__(self): return self
    def __exit__(self, *exc): return False
    def initialize(self, path, source=None):
        self._uri = Path(path).as_uri()
        return {"name": "fake-elp", "version": "0.0.0"}
    def open_document(self, path, source=None): pass
    def request(self, method, params=None):
        if method == "textDocument/documentSymbol":
            return [{"name": "hello/0", "kind": 12,
                     "range": {"start": {"line": 3, "character": 0}, "end": {"line": 3, "character": 19}},
                     "selectionRange": {"start": {"line": 3, "character": 0}, "end": {"line": 3, "character": 11}}}]
        if method == "textDocument/prepareCallHierarchy":
            return [{"uri": self._uri, "name": "hello/0"}]
        if method == "callHierarchy/outgoingCalls":
            return [{"to": {"uri": self._uri, "name": "world/0"}}]
        return None

erlang_backend.ElpClient = FakeElpClient  # no real ELP binary needed
edges = registry.REGISTRY["erlang"].call_edges(proj_dir)
print(list(edges))
// actual (buggy) output: [('greeter__hello__0', 'greeter-erl')]
// expected (correct) output: ['greeter__hello__0']
```

---

## Probe Script

```py
"""Probe for bug src--languages--erlang-py--_analyze_project_uncached.

Spec claim: ErlangAnalysis.edges maps each detected caller function's
canonicalized, module-qualified identity — a single canonicalized,
filesystem-safe/FQN-safe string (the same scheme used for extracted-function
file names, e.g. module__name__arity) — to the set of callee FQNs it invokes,
i.e. edges should be keyed by str.

Reported actual behavior: _analyze_project_uncached declares and populates
`edges` as dict[tuple[str, str], set[str]] — each caller entry is stored under
a (function_id, caller_module) tuple key, never a single string key.

Method: ELP is an external Erlang LSP binary (not installed here, and the
FM-Agent self-validation guard forbids launching FM-Agent workflows), so the
smallest relevant unit is exercised with a mock ElpClient fixture driven
through the package's public entry point: src.languages.registry, the central
language dispatch registry whose erlang handler documents
call_edges(proj_dir) -> {caller_fqn: {callee_fqns}} with string FQN keys.
All fixture/runtime files live in a fresh temporary directory owned by the
probe; no FM-Agent pipeline, CLI, or subprocess workflow is started.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

ERLANG_SOURCE = """-module(greeter).
-export([hello/0, world/0]).

hello() -> world().

world() -> ok.
"""


class FakeElpClient:
    """Mock of src.languages.erlang.ElpClient (LSP conversation only)."""

    def __init__(self, proj_dir):
        self.proj_dir = os.path.abspath(proj_dir)
        self._file_uri = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def initialize(self, bootstrap_path, bootstrap_source=None):
        self._file_uri = Path(bootstrap_path).as_uri()
        return {"name": "fake-elp", "version": "0.0.0"}

    def open_document(self, path, source=None):
        return None

    def request(self, method, params=None):
        if method == "initialize":
            return {"serverInfo": {"name": "fake-elp", "version": "0.0.0"}}
        if method == "textDocument/documentSymbol":
            # One detected function: hello/0 in greeter.erl (kind 12 = Function)
            return [
                {
                    "name": "hello/0",
                    "kind": 12,
                    "range": {
                        "start": {"line": 3, "character": 0},
                        "end": {"line": 3, "character": 19},
                    },
                    "selectionRange": {
                        "start": {"line": 3, "character": 0},
                        "end": {"line": 3, "character": 11},
                    },
                }
            ]
        if method == "textDocument/prepareCallHierarchy":
            return [{"uri": self._file_uri, "name": "hello/0"}]
        if method == "callHierarchy/outgoingCalls":
            # hello/0 calls world/0 in the same module
            return [{"to": {"uri": self._file_uri, "name": "world/0"}}]
        return None


def main():
    from src.languages import registry  # public entry point (language registry)
    from src.languages import erlang as erlang_backend

    proj_dir = tempfile.mkdtemp(prefix="fm_probe_erl_")
    try:
        erl_path = os.path.join(proj_dir, "greeter.erl")
        with open(erl_path, "w", encoding="utf-8") as stream:
            stream.write(ERLANG_SOURCE)

        original_client = erlang_backend.ElpClient
        erlang_backend.ElpClient = FakeElpClient
        try:
            edges = registry.REGISTRY["erlang"].call_edges(proj_dir)
            functions = registry.REGISTRY["erlang"].batch_extract(proj_dir)
        finally:
            erlang_backend.ElpClient = original_client

        if not functions or not edges:
            print(
                "ERROR: fixture did not reach the edges-building path; "
                f"functions={functions!r} edges={edges!r}"
            )
            return 1

        expected_key = "greeter__hello__0"  # single canonicalized FQN string
        actual_keys = [repr(key) for key in edges]
        non_string_keys = [key for key in edges if not isinstance(key, str)]

        if non_string_keys:
            print(
                "CONFIRMED — actual: edges keys are non-string tuples "
                f"{actual_keys} | expected: every edges key is the single "
                f"canonicalized FQN string, e.g. {expected_key!r}"
            )
            return 0

        print(
            "NOT CONFIRMED — actual matched expected: all edges keys are "
            f"canonicalized FQN strings {actual_keys}"
        )
        return 0
    finally:
        shutil.rmtree(proj_dir, ignore_errors=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: edges keys are non-string tuples ["('greeter__hello__0', 'greeter-erl')"] | expected: every edges key is the single canonicalized FQN string, e.g. 'greeter__hello__0'
```
