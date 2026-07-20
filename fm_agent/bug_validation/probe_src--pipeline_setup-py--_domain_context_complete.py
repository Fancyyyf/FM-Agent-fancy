import sys
import os
import json
import tempfile
import shutil

# Add repo root to path so `src` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.pipeline_setup import _domain_context_complete
except ImportError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

work_dir = tempfile.mkdtemp()
try:
    # phases.json: first phase is numeric (valid), second phase has non-numeric key
    phases = {
        "phases": [
            {"phase": 1},
            {"phase": "not_a_number"}
        ]
    }
    phases_path = os.path.join(work_dir, "phases.json")
    with open(phases_path, "w") as f:
        json.dump(phases, f)

    domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
    os.makedirs(domain_dir, exist_ok=True)

    with open(os.path.join(domain_dir, "engine_overview.txt"), "w") as f:
        f.write("overview")

    with open(os.path.join(domain_dir, "phase_01_types.txt"), "w") as f:
        f.write("types")

    expected = False  # spec: return False when phase key is non-numeric

    try:
        actual = _domain_context_complete(work_dir)
        # No exception: value was returned
        if actual != expected:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r} (spec says return False for non-numeric phase key)")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
    except ValueError as e:
        # ValueError from f"{phase_num:02d}" when phase_num is non-numeric
        print(f"CONFIRMED — ValueError: {e} | spec says return False (no exception)")
    except Exception as e:
        print(f"ERROR: Unexpected {type(e).__name__}: {e}")
        sys.exit(1)
finally:
    shutil.rmtree(work_dir, ignore_errors=True)
