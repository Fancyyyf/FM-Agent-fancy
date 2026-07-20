import sys
import os

sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot')

from src.languages.codegraph import CodeGraphExtractor
from src.languages.rust import function_spans

proj_dir = '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot'
expected = None
any_bug = False

def test(label, proj, fpath):
    global any_bug
    try:
        actual = function_spans(proj, fpath)
    except Exception as e:
        print(f'EXCEPTION in "{label}": {type(e).__name__}: {e}', file=sys.stderr)
        any_bug = True
        return
    if actual != expected:
        print(f'BUG in "{label}": actual={actual!r} expected={expected!r}', file=sys.stderr)
        any_bug = True
    else:
        print(f'OK: "{label}" -> {actual!r}', file=sys.stderr)

# Key insight: from_proj_dir checks BOTH proj_dir AND os.path.dirname(proj_dir).
# If proj_dir is a subdir, the DB is found at the parent, but get_function_spans
# derives root from the DB path, which is the parent — NOT proj_dir.
# This means relpath(filepath, root) could produce a DIFFERENT relative path
# than if root were proj_dir. Let's test this mismatch.

# Verify from_proj_dir behavior
cg_direct = CodeGraphExtractor.from_proj_dir(proj_dir)
cg_from_subdir = CodeGraphExtractor.from_proj_dir(os.path.join(proj_dir, 'fm_agent'))
print(f'cg from proj_dir: {cg_direct is not None}', file=sys.stderr)
print(f'cg from subdir:  {cg_from_subdir is not None}', file=sys.stderr)

if cg_from_subdir:
    # DB root (from get_function_spans) = dirname(dirname(abspath(db))) = proj_dir
    # proj_dir passed to from_proj_dir = fm_agent/
    # These differ. Let's compute the actual root.
    db_path = os.path.join(proj_dir, '.codegraph', 'codegraph.db')
    db_root = os.path.dirname(os.path.dirname(os.path.abspath(db_path)))
    print(f'DB root = {db_root}', file=sys.stderr)

    # Scenario A: filepath that is WITHIN the DB-root project but NOT relative
    # to proj_dir (fm_agent/). The DB indexes e.g. config.py at project root.
    # If we call function_spans(proj_dir=fm_agent/, filepath=config.py):
    # rel = relpath(config.py, db_root) = 'config.py' (which IS in DB for python)
    # But the query is for language='rust', so no rows → None (correct)
    # The bug would manifest if a Rust file were indexed and this path trick worked.

    # Scenario B: filepath is within fm_agent/ but NOT in the DB.
    # rel = relpath(fm_agent/something.rs, db_root) = 'fm_agent/something.rs'
    # Not in DB → None (correct)

    # Scenario C: test with proj_dir=fm_agent and an fm_agent file
    test('subdir proj, internal file', os.path.join(proj_dir, 'fm_agent'),
         os.path.join(proj_dir, 'fm_agent', 'bug_validation', 'summary.json'))

    # Scenario D: the crucial test — proj_dir != db_root, filepath at db_root
    # Call with proj_dir=fm_agent, filepath=config.py (at project root)
    # rel = relpath(config.py, db_root) = 'config.py'
    # DB has config.py indexed as Python, but lang_key is "rust" → no rust rows → None
    test('subdir proj, root file', os.path.join(proj_dir, 'fm_agent'),
         os.path.join(proj_dir, 'config.py'))

# Scenario E: What if we accidentally indexed a Rust file? Let's check if ANY
# Rust file in the project matches a DB entry when relativized.
import sqlite3
db_path = os.path.join(proj_dir, '.codegraph', 'codegraph.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT file_path FROM nodes WHERE language IN ('rust', 'python')")
all_files = [r[0] for r in cur.fetchall()]
conn.close()
print(f'DB indexed files (first 5): {all_files[:5]}', file=sys.stderr)

# Check: can we craft a filepath outside the project that relativizes to one of these?
# db_root = proj_dir = /tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot
# any path /tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/OTHER/../../snapshot/config.py
# would normalize to /tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/config.py
# then rel = 'config.py' — but this IS the same file! Not a bug.

# The real potential bug: what if os.path.relpath normalizes differently than
# os.path.abspath? Let's test with a symlink scenario.
# We don't have symlinks to test, but the theoretical concern is:
# - filepath passes through os.path.abspath (string normalization only)
# - codegraph stores os.path.relpath(normalized_path, root)
# - These should be consistent.

# Final verdict
if any_bug:
    print('CONFIRMED — bug triggered')
else:
    print('NOT CONFIRMED — function_spans correctly returns None for unindexed files')
