"""Probe: verify batch_extract uses truthiness check (if cg) instead of explicit None check."""

import sys
import os
from unittest.mock import MagicMock, patch

# Ensure repo root is on the path so the package entry point resolves.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.languages.codegraph import CodeGraphExtractor
    from src.languages.c import batch_extract
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Build a mock extractor that is deliberately non-None but falsy.
# The spec guarantees from_proj_dir returns CodeGraphExtractor | None.
# A truthiness-based guard (if cg) would incorrectly reject this object.
class FalsyExtractor(CodeGraphExtractor):
    def __bool__(self) -> bool:
        return False

    def get_functions_by_file(self, lang_key: str, proj_dir: str = None) -> dict:
        return {"/fake/path.c": [("main", "int main(void) {}\n")]}


# Expected result if the code used a proper `is not None` check:
# the mock extractor's get_functions_by_file result.
expected = {"/fake/path.c": [("main", "int main(void) {}\n")]}

# Monkey-patch from_proj_dir to return a non-None, falsy extractor.
original_from_proj_dir = CodeGraphExtractor.from_proj_dir

try:
    CodeGraphExtractor.from_proj_dir = classmethod(
        lambda cls, proj_dir: FalsyExtractor.__new__(FalsyExtractor)
    )
    actual = batch_extract("/dummy/proj_dir")
    passed = actual != expected  # bug reproduced if actual is {} instead of expected dict
finally:
    CodeGraphExtractor.from_proj_dir = original_from_proj_dir

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
