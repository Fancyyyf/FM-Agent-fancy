import sys
import os
import tempfile

try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep + "..")
    import dashboard
except SyntaxError as e:
    print(f"CONFIRMED — SyntaxError during import: {e}")
    sys.exit(0)
except Exception as e:
    print(f"ERROR: Import failed: {type(e).__name__}: {e}")
    sys.exit(1)

# Import succeeded without SyntaxError — the bug claim is already disproven.
# The claim states: "A SyntaxError exception is raised during the execution
# of the `def` statement because the function body is syntactically incomplete
# (missing closing parenthesis of the _push_llm_status call)."
# A SyntaxError at def-time would prevent the module from importing entirely.

if not hasattr(dashboard.State, '_ingest_opencode'):
    print("NOT CONFIRMED — State._ingest_opencode does not exist (but no SyntaxError)")
    sys.exit(0)

# Further verification: instantiate State and call the method to confirm
# it's not just imported but also functional.
syntax_error_raised = False
callable_msg = ""
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        state = dashboard.State(str(tmpdir))
        rec = {"_kind": "response", "_status": 200, "_ts": "2024-01-01T00:00:00Z"}
        state._ingest_opencode(rec)
        callable_msg = "function defined and callable; no SyntaxError raised"
except SyntaxError:
    syntax_error_raised = True
    callable_msg = "SyntaxError raised during method call"
except Exception as e:
    callable_msg = f"function defined and callable (runtime {type(e).__name__}: {e})"
    syntax_error_raised = False

if syntax_error_raised:
    print(f"CONFIRMED — actual: {callable_msg!r}")
else:
    print(f"NOT CONFIRMED — actual: {callable_msg!r}")
