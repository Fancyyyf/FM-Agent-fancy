"""Probe for _persist_analysis bug: caller_file becomes null when edge caller is absent from functions."""
import os
import sys
import json
import tempfile

# The module is in src/languages/erlang.py
# We need to add the repo root to sys.path so the import resolves.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.languages.erlang import _persist_analysis, ErlangAnalysis
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Build an analysis where edges references a caller NOT in functions.
# functions: {"caller_function", "callee_function"} both present
# edges: caller "orphan_caller" → callee "some_callee" — orphan_caller NOT in functions
analysis = ErlangAnalysis(
    functions={
        "/tmp/fake_src/callee.erl": [("callee_function", "some-source")]
    },
    edges={
        ("orphan_caller", "orphan_module"): {"some_callee"}
    },
    spans={},
    server_info={"version": "1.0"}
)
fingerprint = ("test", 1)

with tempfile.TemporaryDirectory() as proj_dir:
    try:
        _persist_analysis(proj_dir, fingerprint, analysis)
    except Exception as e:
        print(f'ERROR calling _persist_analysis: {e}')
        sys.exit(1)

    output_path = os.path.join(proj_dir, ".codegraph", "erlang_callgraph.json")
    if not os.path.isfile(output_path):
        print(f'ERROR: output file not found at {output_path}')
        sys.exit(1)

    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    edges = data.get("edges", [])
    bug_found = False
    for edge in edges:
        if edge.get("caller") == "orphan_caller" and edge.get("caller_file") is None:
            bug_found = True
            break

    expected = "CONFIRMED"
    if bug_found:
        print(f'CONFIRMED — caller_file is null for edge with orphan caller. Edge: {json.dumps(edge)}')
    else:
        print(f'NOT CONFIRMED — caller_file was not null or edge not found. Edges: {json.dumps(edges)}')
