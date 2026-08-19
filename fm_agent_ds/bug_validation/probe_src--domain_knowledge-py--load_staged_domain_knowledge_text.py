"""Probe script for bug: list_staged_domain_knowledge_relpaths called with
only one argument (work_dir) - claimed to raise TypeError.

Bug ID: src--domain_knowledge-py--load_staged_domain_knowledge_text
"""
import sys
import tempfile
import os

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

try:
    from domain_knowledge import load_staged_domain_knowledge_text, list_staged_domain_knowledge_relpaths

    # The bug claim: list_staged_domain_knowledge_relpaths(work_dir) raises TypeError
    # because it requires a second argument 'prefix'.
    # In reality, 'prefix' has a default value "fm_agent", so the call is valid.

    with tempfile.TemporaryDirectory() as tmpdir:
        # Verify the core claim: calling with just work_dir does NOT raise TypeError
        try:
            result = list_staged_domain_knowledge_relpaths(tmpdir)
            # No TypeError raised — the bug claim is false
            actual_single_arg_ok = True
        except TypeError:
            actual_single_arg_ok = False

        # Also verify load_staged_domain_knowledge_text works end-to-end
        try:
            text_result = load_staged_domain_knowledge_text(tmpdir)
            load_ok = True
        except TypeError:
            load_ok = False

    # The spec claim says it returns a string; actual behavior matches spec
    # The bug claim was that it would raise TypeError — it doesn't
    if actual_single_arg_ok and load_ok:
        print("NOT CONFIRMED — list_staged_domain_knowledge_relpaths accepts single arg (prefix defaults to 'fm_agent'), no TypeError raised")
    else:
        print("CONFIRMED — TypeError occurred (unexpected)")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
