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
