"""Probe for bug: src--incremental_reasoner-py--run_incremental_pipeline

Verifies whether run_incremental_pipeline's cleanup code removes prefixed artifacts
(select_relevant_*, relevant_*, spec_update_*) as required by the specification.

Uses static analysis of the source code, per the FM-Agent self-validation guard
(no pipeline invocation allowed).
"""
import ast
import sys
import os


def find_stale_artifact_globs(source_path):
    """Parse the source and extract the stale_artifact_globs tuple definition."""
    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)

    class GlobsVisitor(ast.NodeVisitor):
        def __init__(self):
            self.found = None

        def visit_Assign(self, node):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "stale_artifact_globs":
                    if isinstance(node.value, ast.Tuple):
                        self.found = [
                            elt.value if isinstance(elt, ast.Constant) else None
                            for elt in node.value.elts
                        ]
                    return

    visitor = GlobsVisitor()
    visitor.visit(tree)
    return visitor.found


def check_prefix_coverage(globs, required_prefixes):
    """Check that each required prefix has at least one glob pattern covering it."""
    missing = []
    for prefix in required_prefixes:
        covered = any(g.startswith(prefix) for g in globs if g)
        if not covered:
            missing.append(prefix)
    return missing


def main():
    # The actual source file (not the extracted function copy)
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    source_file = os.path.join(repo_root, "src", "incremental_reasoner.py")

    try:
        globs = find_stale_artifact_globs(source_file)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    expected_globs = [
        "select_relevant_modules.md",
        "relevant_modules.json",
        "select_relevant_files_*.md",
        "relevant_files_*.json",
        "spec_update_*.md",
        "spec_update_*.json",
    ]

    required_prefixes = ["select_relevant_", "relevant_", "spec_update_"]

    if globs is None:
        print(
            "CONFIRMED — stale_artifact_globs not found in source; "
            "prefixed artifacts are not cleaned."
        )
        return

    missing = check_prefix_coverage(globs, required_prefixes)

    if missing:
        print(
            f"CONFIRMED — stale_artifact_globs found ({globs}) "
            f"but missing prefix(es): {missing}. "
            f"Spec requires cleanup of prefixes: {required_prefixes}"
        )
    elif globs != expected_globs:
        # Coverage is good but globs don't match exactly
        print(
            f"NOT CONFIRMED — stale_artifact_globs ({globs}) "
            f"covers all required prefixes {required_prefixes}. "
            f"Spec-compliant (exact patterns may differ)."
        )
    else:
        print(
            f"NOT CONFIRMED — stale_artifact_globs ({globs}) "
            f"covers all required prefixes {required_prefixes}. "
            f"Spec-compliant and patterns match expected."
        )


if __name__ == "__main__":
    main()
