import sys
import os
import tempfile

sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot')

try:
    from src.domain_knowledge import collect_domain_knowledge_paths
except Exception as e:
    print(f'ERROR: Failed to import collect_domain_knowledge_paths: {e}')
    sys.exit(1)

# Create a temp directory for test fixtures
probe_tmp = tempfile.mkdtemp(prefix='bug_probe_')
print(f'[DEBUG] probe workspace: {probe_tmp}', file=sys.stderr)

# Create a single valid markdown file in the probe workspace
valid_md = os.path.join(probe_tmp, 'valid.md')
with open(valid_md, 'w') as f:
    f.write('# Valid domain knowledge\n')

# Test case: pass one valid path and one nonexistent path via cli_paths.
# The spec says: nonexistent/invalid paths should be silently ignored,
# only valid resolved paths should appear in the result.
# The bug: resolve_domain_knowledge_paths raises ValueError on invalid paths.

cli_paths = [valid_md, '/nonexistent_xyz_file_that_does_not_exist.md']

try:
    actual = collect_domain_knowledge_paths(
        cli_paths=cli_paths,
        base_dir=probe_tmp,
        fallback_base_dir=None,
    )
    # If we reach here, no ValueError was raised.
    # Check: the invalid path should have been skipped.
    # The valid path should be in the result.
    expected_abs = os.path.abspath(valid_md)
    actual_abs = [os.path.abspath(p) for p in actual] if actual else []

    if expected_abs in actual_abs and '/nonexistent_xyz_file' not in str(actual):
        print(f'NOT CONFIRMED — invalid path was silently skipped as expected per spec. '
              f'Returned only valid path: {actual!r}')
    else:
        print(f'NOT CONFIRMED — no ValueError raised, but unexpected result: '
              f'actual={actual!r}, expected to contain {expected_abs!r} and skip invalid paths')
except ValueError as e:
    # This confirms the bug: the spec says ignore, but code raises ValueError
    print(f'CONFIRMED — ValueError raised on invalid path (spec requires silent skip): {e}')
except Exception as e:
    print(f'ERROR: Unexpected exception: {e}')
    sys.exit(1)
finally:
    # Cleanup probe workspace
    import shutil
    shutil.rmtree(probe_tmp, ignore_errors=True)
