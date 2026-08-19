import sys
import os
import tempfile

# Ensure the repo root is on sys.path so 'src' can be imported
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.entry_reasoning_pipeline import _make_run_copy
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

tmpdir = tempfile.mkdtemp()
proj_dir = os.path.join(tmpdir, 'mock_proj')
run_dir = os.path.join(tmpdir, 'mock_run')

try:
    # Create a mock project with .svn and .git metadata, plus regular files
    os.makedirs(os.path.join(proj_dir, '.svn', 'pristine'))
    os.makedirs(os.path.join(proj_dir, '.git', 'objects'))
    os.makedirs(os.path.join(proj_dir, 'src'))
    with open(os.path.join(proj_dir, 'src', 'main.py'), 'w') as f:
        f.write('print("hello")')
    with open(os.path.join(proj_dir, 'README.md'), 'w') as f:
        f.write('# Test Project')

    # Call _make_run_copy
    _make_run_copy(proj_dir, run_dir)

    # Per spec, version-control metadata (.svn AND .git) should be excluded.
    # Per implementation, only .git is excluded.
    svn_exists = os.path.exists(os.path.join(run_dir, '.svn'))
    git_exists = os.path.exists(os.path.join(run_dir, '.git'))
    src_exists = os.path.exists(os.path.join(run_dir, 'src', 'main.py'))
    readme_exists = os.path.exists(os.path.join(run_dir, 'README.md'))

    # Bug is CONFIRMED if .svn exists in run_dir (spec says exclude, code does not)
    if svn_exists:
        print(
            'CONFIRMED — .svn was copied (present in run_dir) '
            'but specification requires excluding all version-control metadata directories. '
            f'git_exists={git_exists} svn_exists={svn_exists} '
            f'src_exists={src_exists} readme_exists={readme_exists}'
        )
    else:
        print(
            'NOT CONFIRMED — .svn was NOT copied to run_dir, '
            'which matches the specification. '
            f'git_exists={git_exists} svn_exists={svn_exists} '
            f'src_exists={src_exists} readme_exists={readme_exists}'
        )
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    # Cleanup: remove the temp workspace
    import shutil
    for path in (run_dir, run_dir + '.tmp', proj_dir):
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
    shutil.rmtree(tmpdir, ignore_errors=True)
