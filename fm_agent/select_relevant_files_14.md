# Select Relevant Files

You are triaging which files of the module `languages` are relevant to a developer intent.

## Steps

1. Read each of the module source files listed below.
2. Decide which files are relevant to the developer intent -- a file is relevant if the developer intent is likely to affect it or depend on its behavior.
3. Write your answer to `fm_agent/relevant_files_14.json` as a JSON array of the relevant file paths, each copied verbatim from the list below. Write `[]` if no file is relevant. Write ONLY that file; do not modify any other project files.

## Module source files

- `src/languages/__init__.py`
- `src/languages/c.py`
- `src/languages/cpp.py`
- `src/languages/python.py`
- `src/languages/rust.py`
- `src/languages/go.py`
- `src/languages/java.py`
- `src/languages/javascript.py`
- `src/languages/typescript.py`
- `src/languages/erlang.py`
- `src/languages/codegraph.py`
- `src/languages/registry.py`

## Developer intent

# Incremental self-validation intent

Validate all behavioral and correctness impacts introduced between the recorded
FM-Agent baseline and the current checked-out main-derived revision. Regenerate
specifications for changed or relevant functions and verify affected callers.
Pay particular attention to file readiness, incremental reasoning, CLI backend,
codegraph integration, tracing, environment checks, and pipeline setup changes.
Do not modify project source files; write validation artifacts only under the
FM-Agent workspace.
