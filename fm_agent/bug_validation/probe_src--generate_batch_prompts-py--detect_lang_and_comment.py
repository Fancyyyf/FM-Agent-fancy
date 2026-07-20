import sys

try:
    from src.generate_batch_prompts import detect_lang_and_comment

    # For file ".hidden", the spec defines the extension as "hidden"
    # (substring after the last "."), so ext_to_lang["hidden"] = "dotfile-lang".
    # The code uses Path.suffix which returns "" for dotfiles, yielding lang="unknown".
    ext_to_lang = {"hidden": "dotfile-lang"}
    actual = detect_lang_and_comment(".hidden", ext_to_lang)

    # Per spec: extension="hidden", ext_to_lang["hidden"]="dotfile-lang" → lang="dotfile-lang"
    # comment: "dotfile-lang" not in COMMENT_PREFIX_BY_LANG → defaults to "//"
    expected = ("dotfile-lang", "//")

    # Bug reproduced if lang mismatches (code returns "unknown" instead of "dotfile-lang")
    lang_mismatch = actual[0] != expected[0]

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if lang_mismatch:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r} (spec: extension=substring after last '.', for '.hidden' ext='hidden', ext_to_lang['hidden']='dotfile-lang')")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
