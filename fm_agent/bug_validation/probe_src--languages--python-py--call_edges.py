import sys
import os

# Ensure the repo root is on sys.path so 'import src' resolves
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from src.languages.python import call_edges
    from src.languages.codegraph import CodeGraphExtractor

    # ── Bug Description ────────────────────────────────────────────────
    # Spec claim: "Returns a dict when the CodeGraph backend can index
    #   the project directory; returns None when the backend is
    #   unavailable or the project cannot be indexed."
    # Code:       return cg.get_call_edges("python") if cg else None
    # Gap:        When cg is truthy (backend available) but
    #             cg.get_call_edges("python") returns None, the function
    #             returns None — violating the spec which demands a dict.
    # ────────────────────────────────────────────────────────────────────

    proj_dir = REPO_ROOT   # has .codegraph/codegraph.db — backend available

    # Verify the backend IS available (cg should be truthy)
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    backend_available = cg is not None

    # Call the function under test via its public entry point
    result = call_edges(proj_dir)

    # ── Verification ───────────────────────────────────────────────────
    # Spec says: when backend can index → MUST return a dict
    # Code says:  return cg.get_call_edges("python") if cg else None
    # If result is a dict → function behaves per spec (bug NOT reproduced)
    # If result is None → function violates spec (bug CONFIRMED)

    if not backend_available:
        # Backend not available — spec expects None, code returns None → correct
        if result is None:
            print("NOT CONFIRMED — backend unavailable, returned None as expected")
        else:
            print(f"UNEXPECTED: backend unavailable but result is {type(result).__name__}")
            sys.exit(1)
    else:
        # Backend IS available — spec demands a dict
        if isinstance(result, dict):
            num_edges = len(result)
            print("NOT CONFIRMED")
            print(f"  reason: backend available (cg is truthy), call_edges returned a dict ({num_edges} callers)")
            print(f"  spec: Returns a dict when backend can index — satisfied")
            print(f"  code: get_call_edges('python') returned a dict, not None")
            print("  note: CodeGraphExtractor.get_call_edges() always returns dict for 'python';")
            print("        the None-return code path in call_edges is unreachable with the current backend")
        else:
            bug_desc = f"backend available but call_edges returned {type(result).__name__} instead of dict"
            actual_desc = repr(result)
            expected_desc = "dict"
            print("CONFIRMED")
            print(f"  actual:   {actual_desc!r}")
            print(f"  expected: {expected_desc!r}")
            print(f"  description: {bug_desc}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
