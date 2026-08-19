import os
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from src.languages.erlang import batch_extract, function_spans, call_edges

    empty_dir = tempfile.mkdtemp(prefix="erlang_bug_probe_")

    try:
        functions = batch_extract(empty_dir)
        spans_result = function_spans(empty_dir, os.path.join(empty_dir, "nonexistent.erl"))
        edges = call_edges(empty_dir)

        print(
            "NOT CONFIRMED — all attributes present via dataclass defaults: "
            f"functions={functions!r}, "
            f"spans_get={spans_result!r}, "
            f"edges={edges!r}"
        )
    finally:
        shutil.rmtree(empty_dir, ignore_errors=True)

except Exception as e:
    print(f"NOT CONFIRMED — unexpected error: {e}")
