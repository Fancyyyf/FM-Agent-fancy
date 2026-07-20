# Bug Report: extract_callee_spec_from_info

**Source file:** `src/generate_batch_prompts-py/extract_callee_spec_from_info.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If info_block contains a [SPLIT]-delimited entry whose first line mentions callee_fqn or any of the aliases (when compared with the comment prefix stripped from that line), returns the full text of that entry exactly as it appears in info_block; otherwise returns None
  - Entries whose content includes the literal string "(no callees)" are treated as non-matching regardless of other content
  - The comment prefix used for stripping is the text preceding a "[SPLIT]" marker within info_block itself, or the first whitespace-delimited token of the block's first non-empty line if no "[SPLIT]" marker is present
  - Within the first line of a candidate entry, the mention check succeeds if any of the search names (callee_fqn or alias) appears as a substring or token
  - The returned entry text preserves the original formatting and comment prefix as found in info_block

---

### Actual Behavior

The function returns either `None` or a nonempty string. If the return value is a nonempty string, it is one of the entries obtained by splitting `info_block` on a delimiter `DELIM` that is determined as follows: let `PREFIX` be the substring before the first `[SPLIT]` in the first line of `info_block` that contains `[SPLIT]`, rightstripped; if no such line exists, let `PREFIX` be the first word of the first nonempty line (if that line matches `r'^(\S+)\s'`), otherwise `PREFIX` is empty; `DELIM` is `PREFIX + " [SPLIT]"` if `PREFIX` is nonempty, else `"[SPLIT]"`. The function returns the earliest such entry (in split order) whose stripped form is nonempty, does not contain the substring `"(no callees)"`, and whose first line (after removing the leading `PREFIX` and surrounding whitespace, if `PREFIX` is nonempty and the first line starts with it) mentions at least one name from `NAMES = _callee_match_names(callee_fqn, aliases or ())` according to `_info_line_mentions_name`. If no entry satisfies these conditions, the function returns `None`. Formally:

Let PREFIX = ( line L  lines(info_block) such that "[SPLIT]"  L ? (substring of L before first "[SPLIT]" right-stripped) : (first non-empty line L'  lines(info_block) matches r'^(\S+)\s' capturing group G ? G : "")).
Let DELIM = (PREFIX  "" ? PREFIX + " [SPLIT]" : "[SPLIT]").
Let NAMES = _callee_match_names(callee_fqn, aliases or ()).
Let ENTRIES = [e.strip() for e in info_block.split(DELIM)].
Let MATCH(e)  e  ""  "(no callees)"  e   n  NAMES: _info_line_mentions_name(
    (if PREFIX  "" and e.split("\n")[0].strip().startswith(PREFIX)
     then e.split("\n")[0].strip()[len(PREFIX):].strip()
     else e.split("\n")[0].strip()),
    n) = True.

Return value R satisfies:
(R = None   e  ENTRIES: MATCH(e))

( e  ENTRIES: MATCH(e)  R = (the first such e in ENTRIES))

---

## Code Evidence

Line 25: split_tag = f"{prefix} [SPLIT]" if prefix else "[SPLIT]"

---

## Trigger Condition

The specification requires that the delimiter used to split entries be exactly the comment prefix followed directly by "[SPLIT]" (the prefix is the text preceding the first "[SPLIT]" marker in the info_block). The code unconditionally inserts a space between the prefix and "[SPLIT]" on line 25. When the actual info_block has no such space (e.g., "//[SPLIT]"), the code uses "// [SPLIT]" as the delimiter, which does not appear in the string. As a result, splitting yields the whole block as a single entry, and the function returns the entire block instead of the first matching entry, violating the specification.

---

## How to trigger the bug

When `extract_callee_spec_from_info` is called with an `info_block` where the comment prefix appears directly adjacent to `[SPLIT]` without an intervening space (e.g., `//[SPLIT]`), the hardcoded space on line 48 of `src/generate_batch_prompts.py` constructs an incorrect delimiter `// [SPLIT]` that does not match any text in the block. The `split()` call returns the entire block as a single undivided entry, and the function then returns that entire block rather than the first matching individual entry.

### Inputs

| Parameter | Value |
|-----------|-------|
| info_block | `"//[SPLIT]entry1\nhello\n//[SPLIT]entry2\nworld"` |
| callee_fqn | `"entry1"` |
| aliases | None (default) |

### Expected (spec-correct) Output

`"entry1\nhello"`

### Actual (buggy) Output

`"//[SPLIT]entry1\nhello\n//[SPLIT]entry2\nworld"`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
from src.generate_batch_prompts import extract_callee_spec_from_info

info_block = "//[SPLIT]entry1\nhello\n//[SPLIT]entry2\nworld"
actual = extract_callee_spec_from_info(info_block, "entry1")
# actual (buggy) output: "//[SPLIT]entry1\nhello\n//[SPLIT]entry2\nworld"
# expected (correct) output: "entry1\nhello"
```

---

## Probe Script

```python
import sys
try:
    from src.generate_batch_prompts import extract_callee_spec_from_info

    # info_block using '//[SPLIT]' (no space between comment prefix and [SPLIT])
    # The specification says the delimiter should be the comment prefix followed
    # directly by '[SPLIT]'. But line 152 hardcodes a space:
    #   split_tag = f"{prefix} [SPLIT]" if prefix else "[SPLIT]"
    # When info_block has '//[SPLIT]', the code constructs '// [SPLIT]' as
    # delimiter, which does not appear in the string, so split returns the
    # entire block as a single entry.
    info_block_no_space = "//[SPLIT]entry1\nhello\n//[SPLIT]entry2\nworld"

    actual = extract_callee_spec_from_info(info_block_no_space, "entry1")

    # Spec-correct expected: just the first entry "entry1\nhello"
    # Buggy actual: the entire block because split with "// [SPLIT]" fails
    expected = "entry1\nhello"

    passed = actual != expected

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: '//[SPLIT]entry1\nhello\n//[SPLIT]entry2\nworld' | expected: 'entry1\nhello'
```
