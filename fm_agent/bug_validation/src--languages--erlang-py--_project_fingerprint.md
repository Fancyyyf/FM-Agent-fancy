# Bug Report: _project_fingerprint

**Source file:** `src/languages/erlang-py/_project_fingerprint.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a 2-tuple (tool_config, file_records)
  - tool_config captures the ELP tool invocation configuration; it is identical
    across calls with the same ELP environment and differs when the configuration
    changes
  - file_records is a tuple of (relative_path, file_size_bytes, modification_time_ns)
    entries, one per file under proj_dir that constitutes Erlang project content —
    Erlang source files, Erlang header files, and project-level build configuration
    files that exist at the project root — and no files outside that set
  - Each relative_path is relative to the project root, using the OS path separator
  - No file path appears more than once in file_records
  - file_records entries are sorted lexicographically by relative_path
  - The returned fingerprint is deterministic: given unchanged ELP configuration,
    unchanged set of Erlang project files, and unchanged size and modification time
    for every such file, repeated calls return a value that compares equal to prior
    results
  - The fingerprint changes if and only if any of the following change: the ELP
    tool configuration, the set of Erlang project files under proj_dir, or the
    size or modification time of any Erlang project file

---

### Actual Behavior

If the function completes normally (no exception), it returns a tuple `(argv_tuple, records_tuple)` where:
- `argv_tuple = _elp_argv()` (a tuple of strings, constant across calls in the same ELP environment).
- Let `root = os.path.abspath(proj_dir)`.
- Let `S` be the union of:
    * all absolute paths yielded by `_iter_project_files(root, {".erl", ".hrl"})` (regular files under `root` with `.erl` or `.hrl` extension, accessible at that moment);
    * those paths `os.path.join(root, name)` for `name` in `_PROJECT_CONFIG_FILES` that pass `os.path.isfile(...)` (i.e., exist as regular files at that moment).
- Let `ordered_paths` be the sorted list of the unique elements of `S` in ascending lexical string order.
- Then `records_tuple` is a tuple of the same length as `ordered_paths`, where the element at position `i` is `(os.path.relpath(p, root), stat.st_size, stat.st_mtime_ns)` with `p = ordered_paths[i]` and `stat = os.stat(p)`; all `os.stat` calls succeed.

If any I/O operation (e.g., during iteration, `os.path.isfile`, `os.stat`) raises an `OSError` (or derived exception), the function propagates that exception and does not return a value.

Formally, let `result` denote the function's return value if it returns normally, and `exception` denote a raised exception otherwise:
- `(exception = None) ⇒ result = (_elp_argv(), tuple((os.path.relpath(p, root), os.stat(p).st_size, os.stat(p).st_mtime_ns) for p in sorted(set(_iter_project_files(root, {".erl",".hrl"})) ∪ { os.path.join(root, n) for n in _PROJECT_CONFIG_FILES if os.path.isfile(os.path.join(root, n)) })))`
- `(exception ≠ None) ⇒ result is undefined`

---

## Code Evidence

```
Line 4:     paths.extend(
        Line 5:         os.path.join(root, name)
        Line 6:         for name in _PROJECT_CONFIG_FILES
        Line 7:         if os.path.isfile(os.path.join(root, name))
        Line 8:     )
```

---

## Trigger Condition

The specification requires one record per project-level build configuration file that exists at the project root. The code only includes those named in `_PROJECT_CONFIG_FILES`, ignoring any other configuration file that may be present. This results in missing entries in the returned file_records and a fingerprint that does not change when those files change, violating the "if and only if" condition.

---

## How to trigger the bug

The function uses a hardcoded tuple `_PROJECT_CONFIG_FILES = ("elp.toml", "rebar.config", "rebar.lock")` to determine which config files to include. Any project-level build configuration file at the project root that is NOT in this tuple (e.g., `sys.config`, `erlang.mk`, `Makefile`) is silently ignored. The fingerprint will not change when such files are added, modified, or removed, violating the spec's "if and only if" condition.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `/tmp/erlang_fp_probe_XXXXXX` (temp dir containing `main.erl`, `include.hrl`, `rebar.config`, `sys.config`) |

### Expected (spec-correct) Output

File records should include `sys.config` as a project-level build configuration file:
`('include.hrl', ..., ...), ('main.erl', ..., ...), ('rebar.config', ..., ...), ('sys.config', ..., ...)` sorted lexicographically.

### Actual (buggy) Output

File records only include `rebar.config` (the known config file) and omit `sys.config` (the unknown config file):
`('include.hrl', ..., ...), ('main.erl', ..., ...), ('rebar.config', ..., ...)`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, tempfile
from languages import erlang

tmpdir = tempfile.mkdtemp(prefix="erlang_fp_probe_")

# Create Erlang files
with open(os.path.join(tmpdir, "main.erl"), "w") as f:
    f.write("-module(main).\n-export([hello/0]).\nhello() -> ok.\n")
with open(os.path.join(tmpdir, "include.hrl"), "w") as f:
    f.write("-define(ANSWER, 42).\n")

# Known config file (in _PROJECT_CONFIG_FILES)
with open(os.path.join(tmpdir, "rebar.config"), "w") as f:
    f.write("{erl_opts, [debug_info]}.\n")

# Custom config file NOT in _PROJECT_CONFIG_FILES
with open(os.path.join(tmpdir, "sys.config"), "w") as f:
    f.write("[{kernel, [{logger_level, debug}]}].\n")

tool_config, file_records = erlang._project_fingerprint(tmpdir)
rel_paths = [r[0] for r in file_records]
print(rel_paths)
# actual (buggy) output: ['include.hrl', 'main.erl', 'rebar.config']
# expected (correct) output: ['include.hrl', 'main.erl', 'rebar.config', 'sys.config']
```

---

## Probe Script

```python
"""Probe script for bug: _project_fingerprint ignores config files not in _PROJECT_CONFIG_FILES."""
import os
import sys
import tempfile

# Ensure the src directory is importable
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from languages import erlang
except ImportError as e:
    print(f"ERROR: Failed to import erlang module: {e}")
    sys.exit(1)


def main():
    # Create a temp directory simulating an Erlang project with:
    # - an .erl source file
    # - an .hrl header file
    # - a known config file (rebar.config) that IS in _PROJECT_CONFIG_FILES
    # - a custom config file (sys.config) that is NOT in _PROJECT_CONFIG_FILES
    tmpdir = tempfile.mkdtemp(prefix="erlang_fp_probe_")

    try:
        # Create Erlang source and header files (needed for file iteration)
        with open(os.path.join(tmpdir, "main.erl"), "w") as f:
            f.write("-module(main).\n-export([hello/0]).\nhello() -> ok.\n")
        with open(os.path.join(tmpdir, "include.hrl"), "w") as f:
            f.write("-define(ANSWER, 42).\n")

        # Create a known config file (in _PROJECT_CONFIG_FILES)
        with open(os.path.join(tmpdir, "rebar.config"), "w") as f:
            f.write("{erl_opts, [debug_info]}.\n")

        # Create a custom config file NOT in _PROJECT_CONFIG_FILES
        # Per the spec, this should be included as a "project-level build
        # configuration file that exists at the project root", but the code
        # only checks the hardcoded _PROJECT_CONFIG_FILES tuple.
        with open(os.path.join(tmpdir, "sys.config"), "w") as f:
            f.write("[{kernel, [{logger_level, debug}]}].\n")

        # Call _project_fingerprint via the package entry point
        tool_config, file_records = erlang._project_fingerprint(tmpdir)

        # Extract relative paths from file_records
        rel_paths = [r[0] for r in file_records]

        # Check if sys.config appears — it should per spec, but won't per code
        has_erl = any(p == "main.erl" for p in rel_paths)
        has_hrl = any(p == "include.hrl" for p in rel_paths)
        has_rebar = any(p == "rebar.config" for p in rel_paths)
        has_sys = any("sys.config" in p for p in rel_paths)

        print(f"[DEBUG] Relative paths in fingerprint: {rel_paths}")
        print(f"[DEBUG] has_erl={has_erl}, has_hrl={has_hrl}, has_rebar={has_rebar}, has_sys_config={has_sys}")

        # CONFIRMED if sys.config is MISSING from the file_records
        # (spec says it should be there, code doesn't include it)
        if has_erl and has_hrl and has_rebar and not has_sys:
            print(
                "CONFIRMED — sys.config missing from file_records; "
                "only config files in _PROJECT_CONFIG_FILES are included. "
                f"File records: {rel_paths}"
            )
        elif has_sys:
            print(
                f"NOT CONFIRMED — sys.config was unexpectedly found in file_records: {rel_paths}"
            )
        else:
            print(
                f"NOT CONFIRMED — unexpected state: "
                f"has_erl={has_erl}, has_hrl={has_hrl}, has_rebar={has_rebar}, "
                f"has_sys={has_sys}, rel_paths={rel_paths}"
            )
    except Exception as exc:
        import traceback
        print(f"ERROR: {exc.__class__.__name__}: {exc}")
        traceback.print_exc()
    finally:
        # Cleanup temp files
        for fname in ["main.erl", "include.hrl", "rebar.config", "sys.config"]:
            try:
                os.remove(os.path.join(tmpdir, fname))
            except OSError:
                pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass


if __name__ == "__main__":
    main()
```

### Probe Output

```
[DEBUG] Relative paths in fingerprint: ['include.hrl', 'main.erl', 'rebar.config']
[DEBUG] has_erl=True, has_hrl=True, has_rebar=True, has_sys_config=False
CONFIRMED — sys.config missing from file_records; only config files in _PROJECT_CONFIG_FILES are included. File records: ['include.hrl', 'main.erl', 'rebar.config']
```
