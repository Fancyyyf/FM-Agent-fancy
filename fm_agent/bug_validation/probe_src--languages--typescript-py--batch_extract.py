import sys
import os
import tempfile
import subprocess
import shutil

BUG_ID = "src--languages--typescript-py--batch_extract"

def main():
    # Add the repo root to sys.path so we can import from src.languages.typescript
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Create a temp TypeScript project with a nested function
    tmpdir = tempfile.mkdtemp(prefix="bug_probe_")
    try:
        # Write a TypeScript file with both top-level and nested functions
        ts_content = """\
function topLevel(): void {
  console.log("top level");
}

function outer(): void {
  function nestedInner(): void {
    console.log("nested");
  }
  nestedInner();
}

const arrowTop = (): void => {
  console.log("arrow top");
};
"""
        ts_path = os.path.join(tmpdir, "index.ts")
        with open(ts_path, "w") as f:
            f.write(ts_content)

        # Run codegraph init to index the project
        result = subprocess.run(
            ["codegraph", "init"], cwd=tmpdir, capture_output=True, text=True
        )
        if result.returncode != 0:
            print("ERROR: codegraph init failed:", result.stderr[:300])
            sys.exit(1)

        # Check that codegraph.db was created
        db_path = os.path.join(tmpdir, ".codegraph", "codegraph.db")
        if not os.path.exists(db_path):
            print("ERROR: codegraph did not produce codegraph.db")
            sys.exit(1)

        # Import batch_extract from the public API
        from src.languages.typescript import batch_extract

        # Call batch_extract on the temp project
        result = batch_extract(tmpdir)

        # Find all function names extracted
        all_func_names = []
        for filepath, funcs in result.items():
            for name, body in funcs:
                all_func_names.append(name)

        # Spec says: only TOP-LEVEL functions should be returned
        # "nestedInner" is a nested function and should NOT appear
        # "topLevel", "outer", "arrowTop" are top-level and SHOULD appear

        top_level_expected = {"topLevel", "outer", "arrowTop"}
        nested_names = set(all_func_names) - top_level_expected

        if nested_names:
            # Bug confirmed: nested functions were included
            nested_list = sorted(nested_names)
            expected_output = "topLevel, outer, arrowTop (top-level only)"
            actual_output = ", ".join(sorted(all_func_names))
            print(f"CONFIRMED — actual includes nested function(s): {nested_list!r} "
                  f"| expected only top-level: {sorted(top_level_expected)!r}")
            print(f"  full output: {actual_output}")
            print(f"  expected:     {expected_output}")
        else:
            actual_output = sorted(all_func_names)
            print(f"NOT CONFIRMED — actual matched expected (only top-level): {actual_output}")

    except ImportError as e:
        print(f"ERROR: Import failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        shutil.rmtree(tmpdir, ignore_errors=True)

if __name__ == "__main__":
    main()
