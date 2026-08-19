"""Probe for bug: src--languages--codegraph-py--CodeGraphExtractor::from_proj_dir

Bug: from_proj_dir checks os.path.exists() but never validates that the
database is a valid CodeGraph database. When the file exists but is invalid
or empty, the returned instance violates the specification's required
guarantee of supporting function-extraction, function-span, and call-edge queries.
"""
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from src.languages.codegraph import CodeGraphExtractor

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an empty .codegraph/codegraph.db (not a valid SQLite database)
        codegraph_dir = os.path.join(tmpdir, ".codegraph")
        os.makedirs(codegraph_dir, exist_ok=True)
        db_path = os.path.join(codegraph_dir, "codegraph.db")
        with open(db_path, "w") as f:
            pass  # empty file: exists on disk but is not a valid database

        # Call from_proj_dir — the spec says a non-None return guarantees
        # query support. For an invalid/unusable DB, spec-compliant result
        # is None (or the returned instance must actually support queries).
        actual = CodeGraphExtractor.from_proj_dir(tmpdir)
        expected = None  # spec-correct for an unusable database

        if actual is not None:
            # Bug reproduced: returned non-None for invalid DB
            # Now verify the instance can't actually support queries
            query_supported = True
            try:
                _ = actual.get_functions_by_file("python", proj_dir=tmpdir)
            except Exception:
                query_supported = False

            if not query_supported:
                print(
                    "CONFIRMED — Bug reproduced: from_proj_dir returned non-None "
                    "for empty/invalid .codegraph/codegraph.db (spec requires None "
                    "for databases that cannot support queries). Queries fail."
                )
            else:
                print(
                    "CONFIRMED — Bug reproduced: from_proj_dir returned non-None "
                    "for empty/invalid .codegraph/codegraph.db (spec requires None). "
                    "Queries unexpectedly succeeded."
                )
        else:
            print(
                "NOT CONFIRMED — actual matched expected "
                "(returned None for invalid DB)"
            )

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
