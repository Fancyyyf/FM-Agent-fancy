import sys
import os

# The module under test is at src/generate_batch_prompts.py.
# Import it and exercise the buggy zip behavior through its public API.
# The bug: zip(exts, languages) on line 394 silently truncates to the shorter list,
# causing incomplete ext_to_lang mapping. This propagates to detect_lang_and_comment()
# and build_prompt(), producing incorrect language/comment annotations.

# The repo root is three levels above this script:
# probe_...py -> bug_validation/ -> fm_agent/ -> repo_root/
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from src.generate_batch_prompts import detect_lang_and_comment, COMMENT_PREFIX_BY_LANG
except ImportError as e:
    print(f'ERROR: could not import module: {e}')
    sys.exit(1)

# ── Simulate the bug: mismatched exts and languages ──
# phases.json might contain e.g.:
#   "languages": ["python", "javascript"]
#   "file_extensions": ["py", "js", "ts"]
# The zip() call truncates to min(len(exts), len(languages)), so "ts" is dropped.

exts     = ["py", "js", "ts"]
languages = ["python", "javascript"]

# Reproduce the exact buggy line (same logic as line 394):
ext_to_lang_buggy = {
    ext.lower().lstrip("."): lang
    for ext, lang in zip(exts, languages)
}
# ext_to_lang_buggy = {"py": "python", "js": "javascript"}  — "ts" is SILENTLY DROPPED

# The spec-correct mapping should include all extensions.
# For this example, the expected (correct) mapping would be:
ext_to_lang_correct = {"py": "python", "js": "javascript", "ts": "typescript"}

# ── Test: demonstrate the impact via detect_lang_and_comment ──
file_ts = "src/components/Button.ts"

lang_buggy, comment_buggy = detect_lang_and_comment(file_ts, ext_to_lang_buggy)
lang_correct, comment_correct = detect_lang_and_comment(file_ts, ext_to_lang_correct)

# ── Verdict ──
# The bug is confirmed if:
#   (a) ext_to_lang_buggy is missing "ts" (zip truncation)
#   (b) detect_lang_and_comment returns a FALLBACK language for .ts files
#       when using the buggy mapping, but the CORRECT language when
#       using a complete mapping.

ts_is_missing = "ts" not in ext_to_lang_buggy
fallback_used = (lang_buggy != lang_correct) or (comment_buggy != comment_correct)
bug_confirmed = ts_is_missing and fallback_used

if bug_confirmed:
    print(
        f'CONFIRMED — zip truncation dropped "ts" from ext_to_lang; '
        f'detect_lang_and_comment returned lang="{lang_buggy}" comment="{comment_buggy}" '
        f'instead of expected lang="{lang_correct}" comment="{comment_correct}"'
    )
else:
    print(
        f'NOT CONFIRMED — ts_in_map={not ts_is_missing}, '
        f'buggy_lang={lang_buggy}, correct_lang={lang_correct}'
    )
