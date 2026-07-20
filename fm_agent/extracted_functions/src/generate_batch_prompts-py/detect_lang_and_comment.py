# [SPEC]
# Unit: src/generate_batch_prompts-py/detect_lang_and_comment.py
#
# detect_lang_and_comment(file_rel, ext_to_lang) -> (str, str)
#
# Pre-condition:
#   - file_rel is a string
#   - ext_to_lang is a dict mapping file extension strings to language name strings
#
# Post-condition:
#   - Returns a tuple (language_name, comment_prefix) of two strings
#   - language_name is the value in ext_to_lang whose key matches file_rel's file extension (the substring after the last "." character, lowercased), if such a key exists; if file_rel has an extension but no matching key exists in ext_to_lang, language_name is the extension itself (lowercased); if file_rel has no extension (no "." character or "." is the last character), language_name is "unknown"
#   - comment_prefix is the single-line comment marker bound to language_name by a fixed language-to-comment mapping; if language_name is absent from that mapping, comment_prefix defaults to "//"
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def detect_lang_and_comment(file_rel: str, ext_to_lang: Dict[str, str]) -> Tuple[str, str]:
    ext = Path(file_rel).suffix.lstrip(".").lower()
    lang = ext_to_lang.get(ext, ext if ext else "unknown")
    comment = COMMENT_PREFIX_BY_LANG.get(lang, "//")
    return lang, comment
