import sys
try:
    from src.languages.registry import function_spans_for_file, REGISTRY

    # Monkey-patch the python handler to simulate an internal codegraph failure
    # that raises instead of returning None — triggering the exception-propagation bug.
    class _BrokenHandler:
        def batch_extract(self, proj_dir):
            return {}
        def call_edges(self, proj_dir):
            return {}
        def function_spans(self, proj_dir, filepath):
            raise RuntimeError("Simulated codegraph internal failure")

    original = REGISTRY.get("python")
    REGISTRY["python"] = _BrokenHandler()

    exception_raised = False
    actual = None
    try:
        result = function_spans_for_file(
            "/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot",
            "src/languages/registry.py",
            "python",
        )
        actual = result
    except RuntimeError as e:
        exception_raised = True
        actual = f"{type(e).__name__}: {e}"
    except Exception as e:
        exception_raised = True
        actual = f"{type(e).__name__}: {e}"
    finally:
        if original is not None:
            REGISTRY["python"] = original
        else:
            del REGISTRY["python"]

    expected = None  # spec: "None signals codegraph unavailability; the caller must fall back"

    if exception_raised:
        print(f"CONFIRMED — exception propagated instead of returning None: {actual}")
    elif actual != expected:
        print(f"NOT CONFIRMED — returned {actual!r} instead of {expected!r}")
    else:
        print(f"NOT CONFIRMED — returned None (spec-correct behavior)")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
