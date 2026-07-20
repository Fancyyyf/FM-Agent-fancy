"""Probe for _split_env_paths bug: \r not treated as path separator."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from src import domain_knowledge

actual = None
expected = 2  # Should resolve 2 files
passed = False

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two valid .md files
        a_path = os.path.join(tmpdir, 'a.md')
        b_path = os.path.join(tmpdir, 'b.md')
        for p in (a_path, b_path):
            with open(p, 'w') as f:
                f.write('# test\n')

        # Set env var with \r separator between two valid filenames
        # Spec says both \n and "newline characters" (includes \r) should be separators
        # Buggy code only replaces \n, so "a.md\rb.md" becomes a single path element
        os.environ['FM_AGENT_DOMAIN_KNOWLEDGE'] = 'a.md\rb.md'

        try:
            result = domain_knowledge.collect_domain_knowledge_paths(
                cli_paths=[],
                base_dir=tmpdir,
            )
            # If we reach here without ValueError, the bug might still exist:
            # _split_env_paths returned ["a.md\rb.md"] (didn't split on \r)
            # but resolve_domain_knowledge_paths somehow resolved it
            actual = len(result)
            passed = actual != expected  # Bug: only 1 file resolved, not 2
        except ValueError as e:
            # If ValueError, _split_env_paths returned ["a.md\rb.md"] (single element)
            # and resolve_domain_knowledge_paths couldn't find a file named "a.md\rb.md"
            actual = f'ValueError: {e}'
            passed = True  # Bug confirmed: \r was not treated as separator

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED - actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED - actual matched expected: {actual!r}')
