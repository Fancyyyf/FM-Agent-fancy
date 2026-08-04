import os
import sys
import tempfile
import shutil

try:
    from src.domain_knowledge import stage_domain_knowledge_files
    from src.domain_knowledge import USER_KNOWLEDGE_REL_DIR
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# All fixtures in a fresh temp directory (not under fm_agent/)
tmpdir = tempfile.mkdtemp(prefix='bug_probe_')
work_dir = os.path.join(tmpdir, 'fm_agent')

test_md = os.path.join(tmpdir, 'test.md')
with open(test_md, 'w') as f:
    f.write('# Test Knowledge\n\nThis is test content.\n')

# First call: set up the staged directory so target_dir exists on disk
stage_domain_knowledge_files(tmpdir, work_dir, [test_md])

target_dir = os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR)
if not os.path.isdir(target_dir):
    print('ERROR: target_dir not created after first call')
    sys.exit(1)

# Track rmtree calls and atomicity violation
_orig_rmtree = shutil.rmtree
_orig_replace = os.replace
_rmtree_called_for_target = [False]
_dir_missing_before_replace = [False]

def _patched_rmtree(path, *a, **kw):
    r = _orig_rmtree(path, *a, **kw)
    if os.path.normpath(path) == os.path.normpath(target_dir):
        _rmtree_called_for_target[0] = True
    return r

def _patched_replace(src, dst):
    if _rmtree_called_for_target[0] and os.path.normpath(dst) == os.path.normpath(target_dir):
        if not os.path.exists(dst):
            _dir_missing_before_replace[0] = True
    return _orig_replace(src, dst)

shutil.rmtree = _patched_rmtree
os.replace = _patched_replace

# Second call triggers the rmtree+replace code path (target_dir exists from first call)
stage_domain_knowledge_files(tmpdir, work_dir, [test_md])

# Restore original functions
shutil.rmtree = _orig_rmtree
os.replace = _orig_replace

expected = 'atomically cleared and repopulated (no window where directory missing)'
if _dir_missing_before_replace[0]:
    actual = 'directory was missing between rmtree and replace (atomicity violated)'
else:
    actual = 'no observable window detected'

if _dir_missing_before_replace[0]:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual: {actual!r} | expected: {expected!r}')

# Cleanup
shutil.rmtree(tmpdir, ignore_errors=True)
