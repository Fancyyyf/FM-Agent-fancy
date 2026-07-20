# Bug Report: load_staged_domain_knowledge_text

**Source file:** `src/domain_knowledge-py/load_staged_domain_knowledge_text.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a string containing the concatenated UTF-8 Markdown contents of all
    staged domain knowledge files, formatted for injection into an LLM context
  - Returns an empty string when no domain knowledge files are staged
  - Each file's content is introduced by a level-3 Markdown heading of the form
    "### {relative_path}" in the order list_staged_domain_knowledge_relpaths
    produces them
  - Files whose content cannot be read (OSError during open/read) are silently
    excluded from the output
  - Files whose content is empty or whitespace-only after stripping are silently
    excluded from the output
  - Bytes in file content that cannot be decoded as UTF-8 are replaced with the
    Unicode replacement character
  - The output has no leading or trailing whitespace beyond the concatenated
    file contents and headings

---

### Actual Behavior

If `list_staged_domain_knowledge_relpaths(work_dir)` returns an empty list, the function returns an empty string. Otherwise, let `P` be the nonempty sorted list of relative paths returned by that call, and let `ROOT = os.path.dirname(os.path.abspath(work_dir))`. For each path `p` in `P`, attempt to open and read the file at `os.path.join(ROOT, p)` using UTF8 encoding with replacement on decoding errors. If the file is successfully opened, let `content` be the result of `f.read().strip()`. A path `p` *contributes* iff `content` is nonempty. Let `C` be the list of contributing pairs `(p, content)` in the order they appear in `P`. Define `HEADER = 'User-provided domain knowledge:\nUse these Markdown notes as additional context for intended behavior, terminology, data encodings, and invariants.'`. Then: if `C` is empty, the function returns `HEADER` (with no trailing whitespace). Otherwise, it builds a string by starting with `HEADER`, appending a blank line, and then for each pair in `C` appending the line `### {p}` followed by `content` and a blank line. The final string is stripped of leading and trailing whitespace (effectively removing any trailing newline). Formally, the return value `R` is given by: let `S = list_staged_domain_knowledge_relpaths(work_dir)`. If `S = []` then `R = ''`. Else let `CONTRIB = [ (p, c) | p  S, such that the file at `join(ROOT, p)` can be opened and its stripped content `c` is nonempty ]`. If `CONTRIB = []` then `R = HEADER`. Else `R = (HEADER + '\n\n' + '\n\n'.join( [ f'### {p}\n{c}' for (p,c) in CONTRIB ] )).strip()`.

---

## Code Evidence

Line 6: sections = [
Line 7:         "User-provided domain knowledge:",
Line 8:         "Use these Markdown notes as additional context for intended behavior, "
Line 9:         "terminology, data encodings, and invariants.",
Line 10:         "",
Line 11:     ]

---

## Trigger Condition

The specification requires the output to contain only the concatenated file contents with headings, without any extra preamble. The code incorrectly adds a 'User-provided domain knowledge:' header that is not part of the specification, producing an incorrect output for any non-empty list of staged files.

---

## How to trigger the bug

Call `load_staged_domain_knowledge_text(work_dir)` with a `work_dir` that contains staged domain knowledge files. The returned string will include an unspec'd preamble.

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | A path to an fm_agent workspace directory containing at least one `.md` file under `spec_prompts/domain_context/user_knowledge/` |

### Expected (spec-correct) Output

```
### fm_agent/spec_prompts/domain_context/user_knowledge/test_knowledge.md
This is a test domain knowledge note.
```

### Actual (buggy) Output

```
User-provided domain knowledge:
Use these Markdown notes as additional context for intended behavior, terminology, data encodings, and invariants.

### fm_agent/spec_prompts/domain_context/user_knowledge/test_knowledge.md
This is a test domain knowledge note.
```

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
from src.domain_knowledge import load_staged_domain_knowledge_text

# Set up a work_dir with a staged domain knowledge file
# (work_dir must have spec_prompts/domain_context/user_knowledge/ with a .md file)
result = load_staged_domain_knowledge_text(work_dir)

# actual (buggy) output: contains "User-provided domain knowledge:" preamble
# expected (correct) output: only ### heading + file content, no extra preamble
print("BUG" if "User-provided domain knowledge:" in result else "OK")
```

---

## Probe Script

```py
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
```

### Probe Output

```
CONFIRMED — preamble 'User-provided domain knowledge:...' found in output. actual(259 chars) != expected(111 chars)
```
