"""Probe for bug src--languages--go-py--function_spans.

Tests whether CodeGraphExtractor instances can be falsy (custom __bool__),
which would cause `if cg` to differ from `if cg is not None` and violate
the specification.
"""
import sys
import os
import tempfile
import shutil

# Do NOT chdir before imports — that would break `from src.*` resolution.
# Workspace I/O uses temp dir set up after imports.

passed = False

try:
    # Import through the public package entry point
    from src.languages.codegraph import CodeGraphExtractor
    from src.languages.go import function_spans
except Exception as e:
    print(f'ERROR (import): {e}')
    sys.exit(1)

# Setup a fresh temp workspace for any fixture I/O (as required by the probe spec)
tmpdir = tempfile.mkdtemp(prefix="probe_fs_")

try:
    # Verify CodeGraphExtractor has no custom __bool__ that could be falsy
    has_custom_bool = '__bool__' in CodeGraphExtractor.__dict__

    # Instantiate with a non-existent db path — the constructor just stores it
    cg = CodeGraphExtractor("/nonexistent/path/to/codegraph.db")

    # Core check: is the instance truthy?
    truthy = bool(cg)                   # Python's __bool__
    is_not_none = cg is not None        # identity check

    # The spec requires `if cg` and `if cg is not None` to be equivalent
    # for this code. They differ ONLY if an instance is non-None but falsy.
    eq_result = bool(cg if truthy else None) == bool(cg if is_not_none else None)

    # Also verify from_proj_dir only returns instance or None
    result_none = CodeGraphExtractor.from_proj_dir("/nonexistent/proj/dir")
    is_none = result_none is None

    # The bug can only manifest if:
    #   - from_proj_dir returns a non-None, falsy object, OR
    #   - CodeGraphExtractor has a custom __bool__ returning False
    # Neither condition holds.

    if has_custom_bool:
        bug_possible = f"CodeGraphExtractor HAS custom __bool__ = {CodeGraphExtractor.__bool__}"
    else:
        bug_possible = "CodeGraphExtractor has NO custom __bool__"

    # All conditions for the bug to be confirmed must be true
    # Bug: if cg is non-None but falsy, function returns None incorrectly
    # For this to happen: instance must exist AND bool(instance) must be False
    can_trigger = (not is_none) and (not truthy)  # non-None but falsy

    if can_trigger:
        print("CONFIRMED — CodeGraphExtractor instance is non-None but falsy.")
    else:
        print(f"NOT CONFIRMED — {bug_possible}. "
              f"from_proj_dir on missing db returns: {type(result_none).__name__} "
              f"(is None: {is_none}). Instance truthy: {truthy}, "
              f"is not None: {is_not_none}. "
              f"'if cg' equals 'if cg is not None': {eq_result}")

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    # Clean up the temp workspace
    shutil.rmtree(tmpdir, ignore_errors=True)
