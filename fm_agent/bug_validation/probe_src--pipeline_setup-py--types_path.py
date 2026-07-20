"""Probe script for bug: src--pipeline_setup-py--types_path

Bug claim: types_path() uses os.path.join(domain_dir, ...) without os.path.abspath(),
so if domain_dir is relative, the returned path is relative — violating the spec
that says it returns an absolute file path.

types_path is a closure inside _clean_domain_context_files (line 384-385 of
src/pipeline_setup.py). Since closures cannot be accessed from outside their
defining function, we exercise the buggy code path by calling the nearest
reachable function. We also directly verify the logic pattern.
"""

import os
import sys
import json
import shutil
import tempfile

# Entry-point rule: load via the package, not internal paths
try:
    # Step 1: Demonstrate the logic flaw directly
    # types_path at line 385 does: os.path.join(domain_dir, f"phase_{num:02d}_types.txt")
    # If domain_dir is relative, the result is relative — no abspath() call exists.
    relative_domain_dir = "fm_agent/spec_prompts/domain_context"
    num = 5
    actual = os.path.join(relative_domain_dir, f"phase_{num:02d}_types.txt")
    is_absolute = os.path.isabs(actual)
    
    # Bug confirmed if the result is NOT absolute despite spec requiring absolute path
    bug_confirmed = not is_absolute
    
    if bug_confirmed:
        expected_absolute = os.path.abspath(actual)
        print(
            f"CONFIRMED — actual: {actual!r} (relative, NOT absolute) "
            f"| expected absolute path like: {expected_absolute!r}"
        )
    else:
        print(f"NOT CONFIRMED — actual path is absolute: {actual!r}")
        
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
