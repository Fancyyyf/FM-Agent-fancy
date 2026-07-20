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
