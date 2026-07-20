# Bug Report: detect_lang_and_comment

**Source file:** `src/generate_batch_prompts.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a tuple (language_name, comment_prefix) of two strings
  - language_name is the value in ext_to_lang whose key matches file_rel's file extension (the substring after the last "." character, lowercased), if such a key exists; if file_rel has an extension but no matching key exists in ext_to_lang, language_name is the extension itself (lowercased); if file_rel has no extension (no "." character or "." is the last character), language_name is "unknown"
  - comment_prefix is the single-line comment marker bound to language_name by a fixed language-to-comment mapping; if language_name is absent from that mapping, comment_prefix defaults to "//"

---

### Actual Behavior

The function returns a tuple (lang, comment). Let ext = Path(file_rel).suffix.lstrip('.').lower(). Then lang = ext_to_lang.get(ext, ext if ext else 'unknown'). Then comment = COMMENT_PREFIX_BY_LANG.get(lang, '//'). No external state is modified, and no exceptions are raised. Formal logic: (ext = lowercase(strip_leading_dots(suffix(Path(file_rel)))))  (lang = (ext_to_lang[ext] if ext  dom(ext_to_lang) else (ext if ext  '' else 'unknown')))  (comment = (COMMENT_PREFIX_BY_LANG[lang] if lang  dom(COMMENT_PREFIX_BY_LANG) else '//'))  (return_value = (lang, comment)).

---

## Code Evidence

Line 2: ext = Path(file_rel).suffix.lstrip('.').lower()

---

## Trigger Condition

The specification defines the extension as the substring after the last '.' character, which for '.hidden' is 'hidden'. The code uses Path.suffix, which treats a leading period as part of the stem and returns an empty suffix, leading to ext = '' and lang = 'unknown', while the spec requires lang = 'hidden'.

---

## How to trigger the bug

The function `detect_lang_and_comment` in `src/generate_batch_prompts.py` uses `Path(file_rel).suffix` to extract the file extension. Python's `Path.suffix` treats a leading dot as part of the stem (not a separator), so `Path(".hidden").suffix` returns `""` instead of `".hidden"`. This causes dotfiles (e.g., `.hidden`, `.gitignore`, `.env`) to be classified as `"unknown"` language, when the specification requires they be classified by the substring after the dot.

### Inputs

| Parameter | Value |
|-----------|-------|
| file_rel | `".hidden"` |
| ext_to_lang | `{"hidden": "dotfile-lang"}` |

### Expected (spec-correct) Output

`("dotfile-lang", "//")`

### Actual (buggy) Output

`("unknown", "//")`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.generate_batch_prompts import detect_lang_and_comment

ext_to_lang = {"hidden": "dotfile-lang"}
result = detect_lang_and_comment(".hidden", ext_to_lang)
# actual (buggy) output: ("unknown", "//")
# expected (correct) output: ("dotfile-lang", "//")
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — actual: ('unknown', '//') | expected: ('dotfile-lang', '//') (spec: extension=substring after last '.', for '.hidden' ext='hidden', ext_to_lang['hidden']='dotfile-lang')
```
