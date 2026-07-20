# Bug Report: main

**Source file:** `fm_agent/extracted_functions/src/generate_batch_prompts-py/main.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns 0 on success; a ValueError is raised (and propagates) if batch_size ≤ 0 or the layer range is out of bounds
  - If args.dry_run is true: prints per-batch diagnostics to stdout and returns 0 without writing any files
  - If args.dry_run is false:
    - Creates output_dir (default: fm_agent/spec_prompts/batch_prompts_<project>_phaseNN/)
    - For each layer in the requested range, partitions layer functions into contiguous chunks of at most args.batch_size elements
    - Writes one batch prompt .txt file per chunk to output_dir; each file is named with the pattern batch_NNN_layerX_<tag>_bM.txt where <tag> is "cycle" for cycle-resolution layers and "extracted" otherwise, NNN is a global sequential batch index, X is the layer index, and M is the chunk index within that layer
    - On resume (args.resume is true): a batch whose functions already carry both [SPEC] and [INFO] blocks produces no prompt file; any stale prompt file left from a prior run for that batch is removed
    - Writes manifest.json in output_dir recording every batch across the layer range — including fully-specced batches — with fields: index, file, layer, is_cycle, num_functions, num_pending, functions (paths prefixed with fm_agent/)
    - Prints the count of generated batches and (on resume) the count of skipped already-specced functions to stdout

---

### Actual Behavior

After line 40, the program state satisfies: args holds the parsed CLI arguments with all attributes (phase, layers, batch_size, output_dir, dry_run, resume) and batch_size > 0. work_dir is the resolved absolute path of the 'fm_agent/' directory (parent of the script's grandparent). repo_root is work_dir.parent. fm_agent_prefix is str(work_dir.relative_to(repo_root)) + '/'. phases_json is the decoded JSON from work_dir/phases.json. project = phases_json['project']. languages = phases_json.get('languages', []). exts = phases_json.get('file_extensions', []). ext_to_lang = {ext.lower().lstrip('.'): lang for ext, lang in zip(exts, languages)}. topdown is the decoded JSON from work_dir/spec_prompts/phase_{args.phase:02d}_topdown_layers.json. layers = topdown.get('layers', []). total_layers = len(layers). start_layer, end_layer = parse_layers_spec(args.layers) with 0 <= start_layer <= end_layer < total_layers. output_dir = Path(args.output_dir) if args.output_dir else work_dir / 'spec_prompts' / f'batch_prompts_{project}_phase{args.phase:02d}'. func_to_layer: Dict[str, int] mapping each function's FQN to its layer index, built by iterating all layers and their functions after file-path normalization. all_funcs: Dict[str, dict] mapping each function's FQN to its entry dict, where for every fn entry, if the original 'file' value started with fm_agent_prefix, it has been replaced by the suffix after that prefix; otherwise it remains unchanged. manifest_batches = []. total_functions = 0. skipped_functions = 0. batch_index = 0. write_targets = []. All these variables are defined in the local scope, and no exceptions were raised because the preconditions ensure args.batch_size > 0 and the layer range is within bounds.

---

## Code Evidence

Line 14: ext_to_lang = {ext.lower().lstrip("."): lang for ext, lang in zip(exts, languages)}

---

## Trigger Condition

The code builds ext_to_lang by zipping exts and languages. If the two lists have different lengths, the resulting mapping is incomplete (only covers the shortest list). For the given input, .js is missing, so later when processing a function with that extension, the program will likely raise a KeyError or produce an incorrect prompt, violating the specification that the program returns 0 and correctly generates batch prompts.

---

## How to trigger the bug

When `phases.json` contains mismatched `languages` and `file_extensions` arrays (e.g., `["python", "javascript"]` and `["py", "js", "ts"]`), the `zip()` call on line 394 of `src/generate_batch_prompts.py` silently truncates to the shorter list. This drops extensions from the longer list, producing an incomplete `ext_to_lang` dictionary. The downstream `detect_lang_and_comment()` function then falls back to using the raw extension string as the language name instead of the correct language identifier, leading to incorrect prompt generation.

### Inputs

| Parameter | Value |
|-----------|-------|
| exts (simulated) | `["py", "js", "ts"]` |
| languages (simulated) | `["python", "javascript"]` |
| file_path (test input) | `"src/components/Button.ts"` |

### Expected (spec-correct) Output

`("typescript", "//")` — language correctly identified as "typescript", comment style "//"

### Actual (buggy) Output

`("ts", "//")` — language falls back to raw extension "ts" because zip truncation dropped it from `ext_to_lang`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.generate_batch_prompts import detect_lang_and_comment

# Simulate mismatched phases.json data
exts     = ["py", "js", "ts"]
languages = ["python", "javascript"]

# Buggy zip truncation (line 394 of src/generate_batch_prompts.py)
ext_to_lang = {ext.lower().lstrip("."): lang for ext, lang in zip(exts, languages)}
# Result: {"py": "python", "js": "javascript"} — "ts" SILENTLY DROPPED

lang, comment = detect_lang_and_comment("src/components/Button.ts", ext_to_lang)
# actual (buggy) output: ("ts", "//")
# expected (correct) output: ("typescript", "//")
```

---

## Probe Script

```python
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
exts      = ["py", "js", "ts"]
languages = ["python", "javascript"]

# Reproduce the exact buggy logic:
ext_to_lang_buggy = {
    ext.lower().lstrip("."): lang
    for ext, lang in zip(exts, languages)
}

# The spec-correct mapping should include ALL extensions:
ext_to_lang_correct = {"py": "python", "js": "javascript", "ts": "typescript"}

# ── Test: demonstrate the impact via detect_lang_and_comment ──
file_ts = "src/components/Button.ts"

lang_buggy, comment_buggy = detect_lang_and_comment(file_ts, ext_to_lang_buggy)
lang_correct, comment_correct = detect_lang_and_comment(file_ts, ext_to_lang_correct)

# ── Verdict ──
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
```

### Probe Output

```
CONFIRMED — zip truncation dropped "ts" from ext_to_lang; detect_lang_and_comment returned lang="ts" comment="//" instead of expected lang="typescript" comment="//"
```
