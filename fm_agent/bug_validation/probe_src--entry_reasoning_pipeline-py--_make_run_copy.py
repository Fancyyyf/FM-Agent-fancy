import sys
import os
import tempfile
import shutil

# Ensure the repo root is on sys.path so 'src' package is importable
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.entry_reasoning_pipeline import _make_run_copy
except ImportError as e:
    print(f'ERROR: failed to import _make_run_copy: {e}')
    sys.exit(1)

src_dir = None
dst_dir = None

try:
    src_dir = tempfile.mkdtemp()
    dst_dir = tempfile.mkdtemp()
    with open(os.path.join(src_dir, 'test.txt'), 'w') as f:
        f.write('hello')

    gap_observed = [False]
    original_copytree = shutil.copytree

    def observing_copytree(*args, **kwargs):
        gap_observed[0] = not os.path.exists(dst_dir)
        return original_copytree(*args, **kwargs)

    shutil.copytree = observing_copytree

    try:
        _make_run_copy(src_dir, dst_dir)
    finally:
        shutil.copytree = original_copytree

    if gap_observed[0]:
        print(f'CONFIRMED — atomicity gap: run_dir absent during copy phase '
              f'(os.path.exists returned False while copytree was running)')
    else:
        print('NOT CONFIRMED — no gap observed during copy phase')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    for d in (src_dir, dst_dir):
        if d and os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
