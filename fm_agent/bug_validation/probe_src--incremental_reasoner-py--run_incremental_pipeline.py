import sys
import os

try:
    # Locate the actual source file (probe script is at fm_agent/bug_validation/, source is at src/)
    probe_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(probe_dir))
    source_file = os.path.join(repo_root, 'src', 'incremental_reasoner.py')

    with open(source_file, 'r') as f:
        source = f.read()

    # The spec requires removal of files prefixed with 'select_relevant_',
    # 'relevant_', and 'spec_update_'. These glob patterns should exist in the
    # source code indicating the function removes the required artifacts.
    required_globs = [
        'select_relevant_modules.md',
        'select_relevant_files_*.md',
        'relevant_modules.json',
        'relevant_files_*.json',
        'spec_update_*.md',
        'spec_update_*.json',
    ]

    found = [p for p in required_globs if p in source]
    missing = [p for p in required_globs if p not in source]

    if len(found) == len(required_globs):
        print('NOT CONFIRMED — code includes required prefixed-file removal: all %d glob patterns present in source' % len(found))
    else:
        print('CONFIRMED — missing removal patterns: %s' % missing)

except Exception as e:
    print('ERROR: %s' % e)
    sys.exit(1)
