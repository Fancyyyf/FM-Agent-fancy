"""Probe for bug `src--entry_reasoning_pipeline-py--_select_functions_by_source`.

Attempt 3 — different inputs: entry_func='bar' is the BARE name of a real
function in the fixture (baz.py defines bar), while extracted identities are
FQNs ('baz-py::bar'), so 'bar' is not among the extracted functions; the
strict-membership check must still raise ValueError. end_funcs is non-empty to
prove the entry_func validation fires before any chain restriction.

Spec claim under test: the pipeline MUST raise ValueError when entry_func is
not among the extracted functions. Reported actual behavior: no validation —
the function proceeds and either returns an empty keep_by_source or raises
KeyError.

FM-Agent self-validation guard: main.run_pipeline is stubbed with a recording
no-op so no FM-Agent workflow (LLM/OpenCode) can start. All fixtures live in a
fresh temporary directory owned by this probe.
"""
import os
import shutil
import sys
import tempfile

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

probe_tmp = None
try:
    import main

    workflow_calls = []

    def _workflow_stub(*args, **kwargs):
        workflow_calls.append((args, kwargs))
        return None

    main.run_pipeline = _workflow_stub

    # Fresh fixture project: foo.py calls bar(), defined in baz.py.
    probe_tmp = tempfile.mkdtemp(prefix="fm_probe_entry_select_")
    proj_dir = os.path.join(probe_tmp, "proj")
    os.makedirs(proj_dir)
    with open(os.path.join(proj_dir, "foo.py"), "w") as f:
        f.write("def foo():\n    return bar()\n")
    with open(os.path.join(proj_dir, "baz.py"), "w") as f:
        f.write("def bar():\n    return 42\n")
except Exception as e:
    print(f"ERROR: probe setup failed: {type(e).__name__}: {e}")
    sys.exit(1)

expected = "ValueError stating entry_func is not among the extracted functions"
passed = False
outcome = None
try:
    result = main.run_entry_pipeline(
        proj_dir, entry_func="bar", end_funcs=["foo-py::foo"]
    )
    outcome = (
        f"returned normally: {result!r} "
        f"(workflow stub invocations: {len(workflow_calls)})"
    )
    passed = True  # spec mandates ValueError; a plain return reproduces the bug
except ValueError as e:
    msg = str(e)
    if "entry_func" in msg:
        outcome = f"raised ValueError: {msg}"
        passed = False  # spec-correct behavior
    else:
        print(f"ERROR: unrelated ValueError before reaching the check: {msg}")
        shutil.rmtree(probe_tmp, ignore_errors=True)
        sys.exit(1)
except Exception as e:
    outcome = f"raised {type(e).__name__} instead of ValueError: {e}"
    passed = True  # spec mandates ValueError; any other outcome reproduces the bug
finally:
    shutil.rmtree(probe_tmp, ignore_errors=True)

if passed:
    print(f"CONFIRMED — actual: {outcome} | expected: {expected}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {outcome}")
