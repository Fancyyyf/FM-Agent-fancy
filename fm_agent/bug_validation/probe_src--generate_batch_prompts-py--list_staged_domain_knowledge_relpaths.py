import sys
import os
import tempfile
import shutil

# Ensure the repo root (cwd) is on sys.path so 'src' package resolves
sys.path.insert(0, os.getcwd())

try:
    from src.domain_knowledge import list_staged_domain_knowledge_relpaths

    # Create a temporary work_dir with the expected structure
    work_dir = tempfile.mkdtemp(prefix="bug_probe_")
    knowledge_dir = os.path.join(
        work_dir, "spec_prompts", "domain_context", "user_knowledge"
    )
    os.makedirs(knowledge_dir, exist_ok=True)

    # Create a real .md file
    real_md = os.path.join(knowledge_dir, "real.md")
    with open(real_md, "w") as f:
        f.write("# Real markdown file\n")

    # Create a symlink pointing to the real .md file
    # (also .md extension to pass the suffix filter)
    symlink_md = os.path.join(knowledge_dir, "linked.md")
    os.symlink("real.md", symlink_md)

    # Call the function under test
    result = list_staged_domain_knowledge_relpaths(work_dir)
    basenames = [os.path.basename(p) for p in result]

    # Expected (per spec): only real.md — symlinks must be excluded
    # Actual (buggy): both real.md and linked.md (symlink included via is_file)
    spec_includes_symlinks = False  # spec says "regular file (not a symlink)"
    buggy_includes_symlinks = "linked.md" in basenames
    passed = buggy_includes_symlinks  # True = bug reproduced (CONFIRMED)

    spec_expected = ["real.md"]
    actual = sorted(basenames)

    if passed:
        print(
            f"CONFIRMED — actual: {actual!r} | expected (per spec): {spec_expected!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — actual matched expected: {actual!r}"
        )

    # Cleanup
    shutil.rmtree(work_dir, ignore_errors=True)

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
