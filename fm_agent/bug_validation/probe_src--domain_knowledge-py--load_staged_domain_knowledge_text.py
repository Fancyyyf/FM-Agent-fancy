"""Probe script for bug: src--domain_knowledge-py--load_staged_domain_knowledge_text.

Bug: load_staged_domain_knowledge_text adds a "User-provided domain knowledge:"
preamble that is not part of the specification. The spec requires output to contain
only concatenated file contents with ### {relpath} headings, with no extra preamble.
"""

import os
import sys
import tempfile

# Ensure the repo root is on sys.path so the package import resolves
# Script is at fm_agent/bug_validation/probe_*.py — go up 3 levels to repo root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from src.domain_knowledge import load_staged_domain_knowledge_text
except ImportError as e:
    print(f"ERROR: Failed to import load_staged_domain_knowledge_text: {e}")
    sys.exit(1)

# Create a temporary work_dir with staged domain knowledge files
outer_tmp = tempfile.mkdtemp(prefix="bug_probe_")
work_dir = os.path.join(outer_tmp, "fm_agent")
os.makedirs(work_dir, exist_ok=True)

# Set up the staged knowledge directory with a test markdown file
knowledge_dir = os.path.join(
    work_dir, "spec_prompts", "domain_context", "user_knowledge"
)
os.makedirs(knowledge_dir, exist_ok=True)

test_md_path = os.path.join(knowledge_dir, "test_knowledge.md")
with open(test_md_path, "w", encoding="utf-8") as f:
    f.write("This is a test domain knowledge note.\n")

# Create a dummy project root above work_dir so file reads work
# (load_staged_domain_knowledge_text computes project_root as 
#  os.path.dirname(os.path.abspath(work_dir)))
project_root = os.path.dirname(os.path.abspath(outer_tmp))
# The relpaths include "fm_agent/" prefix, so we need the project_root to
# contain the full path. Since work_dir = outer_tmp/fm_agent, project_root
# = outer_tmp, so abs_path = os.path.join(outer_tmp, "fm_agent/spec_prompts/...")
# which resolves correctly.

# Re-create the structure so it's accessible from the computed project_root
full_target_dir = os.path.join(
    outer_tmp, "fm_agent", "spec_prompts", "domain_context", "user_knowledge"
)
os.makedirs(full_target_dir, exist_ok=True)
full_test_md = os.path.join(full_target_dir, "test_knowledge.md")
with open(full_test_md, "w", encoding="utf-8") as f:
    f.write("This is a test domain knowledge note.\n")

# Also cleanup the nested temp we created first (use the one at outer level)
import shutil
shutil.rmtree(os.path.join(work_dir, "spec_prompts"), ignore_errors=True)
os.makedirs(os.path.join(work_dir, "spec_prompts", "domain_context", "user_knowledge"), exist_ok=True)
with open(os.path.join(work_dir, "spec_prompts", "domain_context", "user_knowledge", "test_knowledge.md"), "w", encoding="utf-8") as f:
    f.write("This is a test domain knowledge note.\n")

try:
    actual = load_staged_domain_knowledge_text(work_dir)

    # Expected (spec-correct): only file contents with ### heading, no preamble
    # The relpath will be like "fm_agent/spec_prompts/domain_context/user_knowledge/test_knowledge.md"
    expected_lines = []
    for root, _dirs, files in os.walk(knowledge_dir):
        for fname in sorted(files):
            if fname == "manifest.json":
                continue
            abs_p = os.path.join(root, fname)
            rel_to_work = os.path.relpath(abs_p, work_dir).replace(os.sep, "/")
            relpath_key = f"fm_agent/{rel_to_work}"
            with open(abs_p, "r", encoding="utf-8", errors="replace") as fp:
                c = fp.read().strip()
            if c:
                expected_lines.append(f"### {relpath_key}")
                expected_lines.append(c)
    expected = "\n".join(expected_lines).strip()

    # Check if the buggy preamble is present in the actual output
    preamble = "User-provided domain knowledge:"
    bug_reproduced = preamble in actual

    if bug_reproduced:
        print(
            f"CONFIRMED — preamble '{preamble}...' found in output. "
            f"actual({len(actual)} chars) != expected({len(expected)} chars)"
        )
    else:
        print(f"NOT CONFIRMED — preamble not found. actual matched expected")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    # Cleanup temp directory
    import shutil
    shutil.rmtree(outer_tmp, ignore_errors=True)
