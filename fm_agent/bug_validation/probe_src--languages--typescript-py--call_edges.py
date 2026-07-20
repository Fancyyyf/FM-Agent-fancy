"""Probe script for bug src--languages--typescript-py--call_edges.

The spec requires that every callee stem in the returned call_edges dict
corresponds to a function reachable from at least one TypeScript source file
in the project. But CodeGraphExtractor.get_call_edges may include callee
stems for external functions that are not defined in any project source file.

This probe tests with a project where a TypeScript file imports from a
symlinked external TypeScript file. If the callee is included in the result,
the bug is confirmed.
"""

import os
import sys

# Ensure the repo root is on the import path
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.languages.typescript import call_edges
except ImportError as e:
    print(f'ERROR: could not import src.languages.typescript: {e}')
    sys.exit(1)

# Use a pre-prepared test project at /tmp/ts_test_proj
# It contains:
#   main.ts — imports externalHelper from ./linked/external
#   linked/external.ts — symlink to /tmp/external_ts/external.ts (OUTSIDE project)
# A codegraph index has been built for this project.

TEST_PROJ_DIR = '/tmp/ts_test_proj'
EXTERNAL_FILE = '/tmp/external_ts/external.ts'

passed = False
actual = None
error_msg = None

try:
    actual = call_edges(TEST_PROJ_DIR)

    if actual is None:
        print('NOT CONFIRMED — call_edges returned None (no codegraph backend)')
        sys.exit(0)

    if not actual:
        print('NOT CONFIRMED — call_edges returned empty dict')
        sys.exit(0)

    # Check if any callee FQN refers to the external file
    # The external file is linked/external.ts but its real path is outside the project
    # The FQN for externalHelper would be something like:
    #   linked::external-ts::externalHelper
    for caller_fqn, callee_set in actual.items():
        for callee_fqn in callee_set:
            if 'external' in callee_fqn.lower():
                # Found a callee that refers to the symlinked external file
                # Verify it's actually external by checking the real path
                from src.languages.codegraph import CodeGraphExtractor
                cg = CodeGraphExtractor.from_proj_dir(TEST_PROJ_DIR)
                if cg:
                    import sqlite3
                    conn = sqlite3.connect(cg._db)
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT file_path FROM nodes WHERE kind IN ('function','method') AND name='externalHelper'"
                    )
                    rows = cur.fetchall()
                    conn.close()
                    for (file_path,) in rows:
                        abs_path = os.path.join(TEST_PROJ_DIR, file_path)
                        real_path = os.path.realpath(abs_path)
                        if real_path == os.path.realpath(EXTERNAL_FILE):
                            passed = True
                            print(
                                f'CONFIRMED — callee "{callee_fqn}" resolved to '
                                f'external file {real_path} (not in project)'
                            )
                break
        if passed:
            break

    if not passed:
        print('NOT CONFIRMED — no external callee stems found in result')

except Exception as e:
    error_msg = f'{type(e).__name__}: {e}'
    print(f'ERROR: {error_msg}')
    sys.exit(1)
