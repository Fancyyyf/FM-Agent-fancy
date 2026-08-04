#!/usr/bin/env python3
"""Resume-safe DeepSeek translation for the split FM-Agent bug reports.

The English reports are never modified. Translated fragments are cached under
``.bug_report_translation/`` and the three ``*_zh.md`` files are rebuilt
atomically after every completed API response. Pending fragments remain in
English, so an interrupted run always leaves valid, inspectable Markdown.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import fcntl
import hashlib
import json
import os
import re
import sys
import threading
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).resolve().parent
DEFAULT_STATE_DIR = ROOT / ".bug_report_translation"
PROMPT_VERSION = "fm-agent-report-zh-v2"
REPORTS = (
    ("bug_list_v7_28.md", "bug_list_v7_28_zh.md"),
    ("bug_list_v7_28_spec_errors.md", "bug_list_v7_28_spec_errors_zh.md"),
    (
        "bug_list_v7_28_reasoning_misjudgments.md",
        "bug_list_v7_28_reasoning_misjudgments_zh.md",
    ),
)

SYSTEM_PROMPT = """\
你是一名资深软件验证文档翻译员。请将输入 Markdown 片段中的自然语言英文完整翻译为简体中文。

必须遵守：
1. 不得总结、删减、补充、改写事实或改变结论；只做忠实翻译。
2. 严格保留 Markdown/HTML 结构、标题层级、表格列、列表层级、代码围栏和 JSON 语法。
3. JSON key 不翻译；JSON 中用于说明行为、条件、原因、摘要和输出的自然语言 string value 要翻译。
4. 以下内容保持原样：函数名、类名、变量名、参数名、类型名、模块名、FMA-MISMATCH 编号、文件路径、链接目标、
   命令、环境变量、模型名、代码、正则表达式、异常类名、JSON 枚举值，以及 MATCH、MISMATCH、ERROR、
   confirmed、not_confirmed、SPEC、Reasoner、Validator、probe 等审计术语。
5. 反引号包围的 inline code 必须逐字保持；链接显示文字可翻译，但链接目标必须逐字保持。
6. 不得在输出外层增加代码围栏、解释、前言或结束语。只返回翻译后的 Markdown 片段。
7. 必须翻译所有非代码自然语言英文，不得遗漏较长段落或列表项；尤其包括 SPEC claim、Actual behavior、
   Code evidence 周围说明、Trigger condition、Validator trigger、Probe stdout，以及 JSON 中可翻译的
   string value。只有规则 4 指定的技术标识与审计术语可以保留英文。
8. 输入中的 `ZXQFMKEEP` 占位符代表受保护的原文结构，必须逐字保留，不能增加、删除、翻译、拆分或改写。
"""

FENCE_RE = re.compile(
    r"(?ms)^(?P<mark>`{3,}|~{3,})(?P<lang>[^\n]*)\n"
    r"(?P<body>.*?)^(?P=mark)[ \t]*$"
)
FENCE_LINE_RE = re.compile(r"(?m)^(?:`{3,}|~{3,})[^\n]*$")
INLINE_CODE_RE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
SINGLE_QUOTED_CODE_RE = re.compile(r"'[^'\n]{1,120}'")
LINK_TARGET_RE = re.compile(r"\]\(([^)\n]+)\)")
FMA_ID_RE = re.compile(r"FMA-MISMATCH-\d{3}|[A-Za-z0-9_./:-]+--[A-Za-z0-9_./:-]+")
ANCHOR_RE = re.compile(r'<a\s+id="([^"]+)"\s*></a>')
ITEM_HEADING_RE = re.compile(
    r"^##### FMA-MISMATCH-(?P<number>\d{3}) — `(?P<bug_id>[^`]+)`$",
    re.MULTILINE,
)
PROTECTED_JSON_KEYS = {
    "signature",
    "function",
    "id",
    "source_file",
    "function_name",
    "probe_script",
    "detail_file",
    "confirmation_status",
    "attempts",
    "verdict",
    "code_evidence",
    "name",
}
COMPLETENESS_EXEMPT_JSON_KEYS = {
    "counterexample",
    "offending_statements",
    "probe_stdout",
}
COMMON_ENGLISH_PROSE_RE = re.compile(
    r"(?i)\b(?:"
    r"the|a|an|is|are|was|were|be|been|being|returns?|returned|when|if|"
    r"otherwise|where|each|every|values?|strings?|functions?|methods?|code|"
    r"specification|requires?|actual|behavior|inputs?|outputs?|should|contains?|"
    r"containing|without|with|from|into|whose|that|this|these|those|after|before|"
    r"causes?|instead|raises?|can|could|will|would|must|may|only|and|or|not|no|"
    r"as|by|for|to|of|in|on|at|it|its|they|them|their|than|then|also|any|all|"
    r"both|either|neither|whether|used|using|use|given|provides?|remains?|"
    r"results?|expected|observed|because|due|while|during|through"
    r")\b"
)
HTML_CODE_RE = re.compile(r"(?is)<code>.*?</code>")
PROTECTED_HTML_TAG_RE = re.compile(
    r"</?(?:details|summary)>", re.IGNORECASE
)
SHIELD_TOKEN_PREFIX = "ZXQFMKEEP"


@dataclass(frozen=True)
class Chunk:
    source_name: str
    output_name: str
    index: int
    text: str
    item_id: str | None
    key: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def load_environment(explicit_path: str | None) -> Path | None:
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path).expanduser().resolve())
    configured = os.environ.get("FM_AGENT_TRANSLATION_ENV_FILE")
    if configured:
        candidates.append(Path(configured).expanduser().resolve())
    candidates.extend(
        (
            ROOT / ".env",
            ROOT.parent / "FM-Agent_myself" / ".env",
        )
    )
    for candidate in candidates:
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return candidate
    return None


def markdown_blocks(text: str) -> list[str]:
    """Split at blank lines without splitting fenced code blocks."""
    lines = text.splitlines(keepends=True)
    blocks: list[str] = []
    current: list[str] = []
    fence_mark: str | None = None
    for line in lines:
        stripped = line.lstrip()
        if fence_mark is None:
            match = re.match(r"(`{3,}|~{3,})", stripped)
            if match:
                fence_mark = match.group(1)
        elif stripped.startswith(fence_mark):
            fence_mark = None
        current.append(line)
        if fence_mark is None and not line.strip():
            blocks.append("".join(current))
            current = []
    if current:
        blocks.append("".join(current))
    return blocks


def pack_blocks(text: str, max_chars: int) -> list[str]:
    blocks = markdown_blocks(text)
    packed: list[str] = []
    current = ""
    for block in blocks:
        if current and len(current) + len(block) > max_chars:
            packed.append(current)
            current = ""
        if len(block) > max_chars:
            if current:
                packed.append(current)
                current = ""
            # Fenced JSON is kept atomic even when it exceeds max_chars.
            packed.append(block)
        else:
            current += block
    if current:
        packed.append(current)
    return [part for part in packed if part]


def report_units(text: str) -> list[tuple[str | None, str]]:
    headings = list(ITEM_HEADING_RE.finditer(text))
    if not headings:
        return [(None, text)]
    units: list[tuple[str | None, str]] = []
    if headings[0].start():
        units.append((None, text[: headings[0].start()]))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        units.append((heading.group("bug_id"), text[heading.start() : end]))
    return units


def build_chunks(model: str, max_chars: int) -> tuple[list[Chunk], dict[str, list[Chunk]]]:
    all_chunks: list[Chunk] = []
    by_output: dict[str, list[Chunk]] = {}
    for source_name, output_name in REPORTS:
        source_path = ROOT / source_name
        if not source_path.is_file():
            raise FileNotFoundError(f"missing source report: {source_path}")
        pieces: list[tuple[str | None, str]] = []
        for item_id, unit in report_units(source_path.read_text(encoding="utf-8")):
            pieces.extend((item_id, part) for part in pack_blocks(unit, max_chars))
        chunks: list[Chunk] = []
        for index, (item_id, text) in enumerate(pieces):
            key = sha256_text(
                "\0".join((PROMPT_VERSION, model, source_name, str(index), text))
            )
            chunk = Chunk(source_name, output_name, index, text, item_id, key)
            chunks.append(chunk)
            all_chunks.append(chunk)
        by_output[output_name] = chunks
    return all_chunks, by_output


def remove_fenced_regions(text: str) -> str:
    return FENCE_RE.sub("", text)


def shield_for_translation(text: str) -> tuple[str, dict[str, str]]:
    """Replace fragile Markdown/code structures with reversible API placeholders."""
    if SHIELD_TOKEN_PREFIX in text:
        raise ValueError(f"source unexpectedly contains {SHIELD_TOKEN_PREFIX}")
    protected: dict[str, str] = {}

    def token(value: str) -> str:
        placeholder = f"{SHIELD_TOKEN_PREFIX}{len(protected):06d}QXZ"
        protected[placeholder] = value
        return placeholder

    def shield_fence(match: re.Match[str]) -> str:
        if match.group("lang").strip().lower() != "json":
            return token(match.group(0))
        whole = match.group(0)
        body_start = match.start("body") - match.start()
        body_end = match.end("body") - match.start()
        return token(whole[:body_start]) + match.group("body") + token(whole[body_end:])

    shielded = FENCE_RE.sub(shield_fence, text)
    for pattern in (
        INLINE_CODE_RE,
        LINK_TARGET_RE,
        ANCHOR_RE,
        PROTECTED_HTML_TAG_RE,
        FMA_ID_RE,
    ):
        shielded = pattern.sub(lambda match: token(match.group(0)), shielded)
    return shielded, protected


def unshield_translation(text: str, protected: dict[str, str]) -> str:
    """Restore placeholders, rejecting any API response that changed their set."""
    expected = Counter(protected.keys())
    observed = Counter(
        re.findall(rf"{SHIELD_TOKEN_PREFIX}\d{{6}}QXZ", text)
    )
    if observed != expected:
        missing = sum((expected - observed).values())
        extra = sum((observed - expected).values())
        raise ValueError(
            f"protected placeholders changed (missing={missing}, extra={extra})"
        )
    for placeholder, original in protected.items():
        text = text.replace(placeholder, original)
    return text


def json_shape(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: json_shape(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_shape(item) for item in value]
    return type(value).__name__


def protected_json_values(value: Any, output: list[tuple[str, str]]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in PROTECTED_JSON_KEYS and isinstance(item, str):
                output.append((key, item))
            protected_json_values(item, output)
    elif isinstance(value, list):
        for item in value:
            protected_json_values(item, output)


def translatable_json_strings(value: Any, output: list[str]) -> None:
    """Collect prose-bearing JSON values while excluding protected identifiers."""
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str):
                if (
                    key not in PROTECTED_JSON_KEYS
                    and key not in COMPLETENESS_EXEMPT_JSON_KEYS
                ):
                    output.append(item)
            else:
                translatable_json_strings(item, output)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                output.append(item)
            else:
                translatable_json_strings(item, output)


def translatable_prose(text: str) -> str:
    """Return prose used to detect accidentally untranslated English."""
    pieces: list[str] = []
    position = 0
    for fence in FENCE_RE.finditer(text):
        pieces.append(text[position : fence.start()])
        if fence.group("lang").strip().lower() == "json":
            try:
                value = json.loads(fence.group("body"))
            except json.JSONDecodeError:
                pass
            else:
                translatable_json_strings(value, pieces)
        position = fence.end()
    pieces.append(text[position:])
    prose = "\n".join(pieces)
    prose = INLINE_CODE_RE.sub("", prose)
    prose = SINGLE_QUOTED_CODE_RE.sub("", prose)
    prose = HTML_CODE_RE.sub("", prose)
    prose = LINK_TARGET_RE.sub("]()", prose)
    prose = FMA_ID_RE.sub("", prose)
    return prose


def restore_inline_code(source: str, translated: str) -> str:
    """Restore inline-code payloads positionally when Markdown structure survived."""
    originals = INLINE_CODE_RE.findall(remove_fenced_regions(source))
    observed = INLINE_CODE_RE.findall(remove_fenced_regions(translated))
    if len(originals) != len(observed):
        return translated
    original_iter = iter(originals)

    def restore_plain(plain: str) -> str:
        return INLINE_CODE_RE.sub(lambda _match: f"`{next(original_iter)}`", plain)

    pieces: list[str] = []
    position = 0
    for fence in FENCE_RE.finditer(translated):
        pieces.append(restore_plain(translated[position : fence.start()]))
        pieces.append(fence.group(0))
        position = fence.end()
    pieces.append(restore_plain(translated[position:]))
    return "".join(pieces)


def restore_protected_json_tree(source: Any, translated: Any) -> bool:
    """Restore protected string values in an otherwise matching JSON tree."""
    changed = False
    if isinstance(source, dict) and isinstance(translated, dict):
        if source.keys() != translated.keys():
            return False
        for key, source_item in source.items():
            translated_item = translated[key]
            if (
                key in PROTECTED_JSON_KEYS
                and isinstance(source_item, str)
                and isinstance(translated_item, str)
            ):
                if source_item != translated_item:
                    translated[key] = source_item
                    changed = True
            else:
                changed = (
                    restore_protected_json_tree(source_item, translated_item) or changed
                )
    elif isinstance(source, list) and isinstance(translated, list):
        if len(source) != len(translated):
            return False
        for source_item, translated_item in zip(source, translated):
            changed = (
                restore_protected_json_tree(source_item, translated_item) or changed
            )
    return changed


def restore_protected_json(source: str, translated: str) -> str:
    """Reinsert protected identifiers into corresponding translated JSON fences."""
    source_fences = list(FENCE_RE.finditer(source))
    translated_fences = list(FENCE_RE.finditer(translated))
    if len(source_fences) != len(translated_fences):
        return translated

    pieces: list[str] = []
    position = 0
    for source_fence, translated_fence in zip(source_fences, translated_fences):
        pieces.append(translated[position : translated_fence.start("body")])
        body = translated_fence.group("body")
        source_lang = source_fence.group("lang").strip().lower()
        translated_lang = translated_fence.group("lang").strip().lower()
        if source_lang == translated_lang == "json":
            try:
                source_json = json.loads(source_fence.group("body"))
                translated_json = json.loads(body)
            except json.JSONDecodeError:
                pass
            else:
                if json_shape(source_json) == json_shape(translated_json):
                    if restore_protected_json_tree(source_json, translated_json):
                        body = json.dumps(
                            translated_json, ensure_ascii=False, indent=2
                        ) + "\n"
        pieces.append(body)
        position = translated_fence.end("body")
    pieces.append(translated[position:])
    return "".join(pieces)


def validate_translation(source: str, translated: str) -> list[str]:
    errors: list[str] = []
    if not translated.strip():
        return ["empty response"]

    for label, pattern in (
        ("link targets", LINK_TARGET_RE),
        ("FMA/function identifiers", FMA_ID_RE),
        ("HTML anchors", ANCHOR_RE),
    ):
        if Counter(pattern.findall(source)) != Counter(pattern.findall(translated)):
            errors.append(f"{label} changed")

    for tag in ("<details>", "</details>", "<summary>", "</summary>"):
        if source.count(tag) != translated.count(tag):
            errors.append(f"{tag} count changed")

    source_fence_lines = Counter(
        line.strip() for line in FENCE_LINE_RE.findall(source)
    )
    translated_fence_lines = Counter(
        line.strip() for line in FENCE_LINE_RE.findall(translated)
    )
    if source_fence_lines != translated_fence_lines:
        errors.append("raw fence lines changed")

    source_plain = remove_fenced_regions(source)
    translated_plain = remove_fenced_regions(translated)
    if Counter(INLINE_CODE_RE.findall(source_plain)) != Counter(
        INLINE_CODE_RE.findall(translated_plain)
    ):
        errors.append("inline code changed")

    source_fences = list(FENCE_RE.finditer(source))
    translated_fences = list(FENCE_RE.finditer(translated))
    if len(source_fences) != len(translated_fences):
        errors.append("fenced block count changed")
        return errors

    for index, (before, after) in enumerate(zip(source_fences, translated_fences), 1):
        before_lang = before.group("lang").strip().lower()
        after_lang = after.group("lang").strip().lower()
        if before_lang != after_lang:
            errors.append(f"fence {index} language changed")
            continue
        if before_lang != "json":
            if before.group("body") != after.group("body"):
                errors.append(f"non-JSON fence {index} changed")
            continue
        try:
            before_json = json.loads(before.group("body"))
            after_json = json.loads(after.group("body"))
        except json.JSONDecodeError as exc:
            errors.append(f"JSON fence {index} became invalid: {exc}")
            continue
        if json_shape(before_json) != json_shape(after_json):
            errors.append(f"JSON fence {index} structure changed")
        before_protected: list[tuple[str, str]] = []
        after_protected: list[tuple[str, str]] = []
        protected_json_values(before_json, before_protected)
        protected_json_values(after_json, after_protected)
        if before_protected != after_protected:
            errors.append(f"JSON fence {index} protected identifiers changed")

    source_prose_words = len(
        COMMON_ENGLISH_PROSE_RE.findall(translatable_prose(source))
    )
    translated_prose_words = len(
        COMMON_ENGLISH_PROSE_RE.findall(translatable_prose(translated))
    )
    allowed_residue = max(6, int(source_prose_words * 0.20))
    if source_prose_words >= 20 and translated_prose_words > allowed_residue:
        errors.append(
            "too much untranslated English prose remains "
            f"({translated_prose_words}/{source_prose_words} common words; "
            f"allowed {allowed_residue})"
        )
    return errors


def cache_path(state_dir: Path, chunk: Chunk) -> Path:
    return state_dir / "cache" / f"{chunk.key}.json"


def read_cached_translation(state_dir: Path, chunk: Chunk) -> str | None:
    path = cache_path(state_dir, chunk)
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (
        record.get("key") != chunk.key
        or record.get("source_sha256") != sha256_text(chunk.text)
        or not isinstance(record.get("translated"), str)
    ):
        return None
    if validate_translation(chunk.text, record["translated"]):
        return None
    return record["translated"]


def save_cached_translation(
    state_dir: Path,
    chunk: Chunk,
    translated: str,
    model: str,
    usage: dict[str, Any],
) -> None:
    path = cache_path(state_dir, chunk)
    atomic_write_json(
        path,
        {
            "key": chunk.key,
            "source_name": chunk.source_name,
            "output_name": chunk.output_name,
            "chunk_index": chunk.index,
            "item_id": chunk.item_id,
            "source_sha256": sha256_text(chunk.text),
            "model": model,
            "prompt_version": PROMPT_VERSION,
            "translated_at": utc_now(),
            "usage": usage,
            "translated": translated,
        },
    )


def translate_chunk(
    client: OpenAI,
    chunk: Chunk,
    model: str,
    max_tokens: int,
    attempts: int,
    strict_prose: bool = False,
) -> tuple[str, dict[str, Any]]:
    shielded_text, protected = shield_for_translation(chunk.text)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "请翻译下面的 Markdown 片段。只返回翻译后的片段：\n\n"
                + shielded_text
            ),
        },
    ]
    last_error = "unknown translation error"
    for attempt in range(1, attempts + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
                max_tokens=max_tokens,
            )
            translated = (response.choices[0].message.content or "").strip()
            # All source inline code is shielded at this point. Any inline
            # backticks in the raw response were introduced by the model.
            translated = INLINE_CODE_RE.sub(
                lambda match: match.group(1), translated
            )
            translated = unshield_translation(translated, protected)
            translated = restore_inline_code(chunk.text, translated)
            translated = restore_protected_json(chunk.text, translated)
            # Preserve trailing newline semantics for exact document reassembly.
            if chunk.text.endswith("\n"):
                translated += "\n"
            errors = validate_translation(chunk.text, translated)
            if strict_prose:
                source_words = len(
                    COMMON_ENGLISH_PROSE_RE.findall(
                        translatable_prose(chunk.text)
                    )
                )
                translated_words = len(
                    COMMON_ENGLISH_PROSE_RE.findall(
                        translatable_prose(translated)
                    )
                )
                allowed = max(2, int(source_words * 0.20))
                if source_words >= 3 and translated_words > allowed:
                    errors.append(
                        "strict prose translation incomplete "
                        f"({translated_words}/{source_words}; allowed {allowed})"
                    )
            if not errors:
                usage_obj = response.usage
                usage = (
                    usage_obj.model_dump()
                    if usage_obj is not None and hasattr(usage_obj, "model_dump")
                    else {}
                )
                return translated, usage
            last_error = "; ".join(errors)
        except Exception as exc:  # API exceptions are recorded without credentials.
            last_error = f"{type(exc).__name__}: {exc}"

        if attempt < attempts:
            messages.extend(
                (
                    {
                        "role": "assistant",
                        "content": translated if "translated" in locals() else "",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"上次输出未通过译文校验：{last_error}。"
                            "请重新翻译原片段中的全部自然语言英文，包括所有列表说明、"
                            "行为描述、触发条件和 JSON 可翻译字符串；同时严格保持所有"
                            "标识符、链接、JSON 结构、inline code 与代码围栏。"
                            "只返回完整的翻译片段。"
                        ),
                    },
                )
            )
            time.sleep(min(2**attempt, 10))
    raise RuntimeError(last_error)


def translate_chunk_in_parts(
    client: OpenAI,
    chunk: Chunk,
    model: str,
    max_tokens: int,
    attempts: int,
    split_chars: int,
) -> tuple[str, dict[str, Any]]:
    """Translate one original cache chunk as smaller blocks, then validate it whole."""
    parts = pack_blocks(chunk.text, split_chars)
    if len(parts) == 1:
        return translate_chunk(client, chunk, model, max_tokens, attempts)

    translated_parts: list[str] = []
    part_usage: list[dict[str, Any]] = []
    for part_index, part in enumerate(parts):
        part_chunk = Chunk(
            source_name=chunk.source_name,
            output_name=chunk.output_name,
            index=chunk.index,
            text=part,
            item_id=chunk.item_id,
            key=f"{chunk.key}:repair-part:{part_index}",
        )
        translated, usage = translate_chunk(
            client, part_chunk, model, max_tokens, attempts
        )
        translated_parts.append(translated)
        part_usage.append(usage)

    combined = "".join(translated_parts)
    errors = validate_translation(chunk.text, combined)
    if errors:
        raise RuntimeError("combined repair failed: " + "; ".join(errors))
    return combined, {"repair_parts": len(parts), "part_usage": part_usage}


def translate_chunk_fieldwise(
    client: OpenAI,
    chunk: Chunk,
    model: str,
    max_tokens: int,
    attempts: int,
) -> tuple[str, dict[str, Any]]:
    """Rebuild a chunk from translated prose lines and JSON string values."""
    usage_records: list[dict[str, Any]] = []
    unit_index = 0

    def sentence_parts(text: str, max_chars: int = 1200) -> list[str]:
        sentences = re.split(r"(?<=[.!?;])(?=\s|$)", text)
        parts: list[str] = []
        current = ""
        for sentence in sentences:
            if current and len(current) + len(sentence) > max_chars:
                parts.append(current)
                current = ""
            current += sentence
        if current:
            parts.append(current)
        return parts

    def translate_unit(text: str) -> str:
        nonlocal unit_index
        unit_chunk = Chunk(
            source_name=chunk.source_name,
            output_name=chunk.output_name,
            index=chunk.index,
            text=text,
            item_id=chunk.item_id,
            key=f"{chunk.key}:field:{unit_index}",
        )
        unit_index += 1
        try:
            translated, usage = translate_chunk(
                client, unit_chunk, model, max_tokens, attempts
            )
            usage_records.append(usage)
            return translated
        except RuntimeError:
            parts = sentence_parts(text)
            if len(parts) == 1:
                raise
            translated_parts: list[str] = []
            for part_index, part in enumerate(parts):
                if not COMMON_ENGLISH_PROSE_RE.search(
                    translatable_prose(part)
                ):
                    translated_parts.append(part)
                    continue
                part_chunk = Chunk(
                    source_name=chunk.source_name,
                    output_name=chunk.output_name,
                    index=chunk.index,
                    text=part,
                    item_id=chunk.item_id,
                    key=f"{unit_chunk.key}:sentence:{part_index}",
                )
                translated_part, usage = translate_chunk(
                    client, part_chunk, model, max_tokens, attempts
                )
                translated_parts.append(translated_part)
                usage_records.append(usage)
            combined = "".join(translated_parts)
            errors = validate_translation(text, combined)
            if errors:
                raise RuntimeError(
                    "sentence repair failed: " + "; ".join(errors)
                )
            return combined

    def translate_json_value(value: Any, parent_key: str | None = None) -> Any:
        if isinstance(value, dict):
            return {
                key: (
                    item
                    if key in PROTECTED_JSON_KEYS and isinstance(item, str)
                    else translate_json_value(item, key)
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [translate_json_value(item, parent_key) for item in value]
        if (
            isinstance(value, str)
            and COMMON_ENGLISH_PROSE_RE.search(value)
        ):
            return translate_unit(value)
        return value

    def translate_plain(plain: str) -> str:
        translated_lines: list[str] = []
        for line in plain.splitlines(keepends=True):
            if COMMON_ENGLISH_PROSE_RE.search(translatable_prose(line)):
                translated_lines.append(translate_unit(line))
            else:
                translated_lines.append(line)
        return "".join(translated_lines)

    pieces: list[str] = []
    position = 0
    for fence in FENCE_RE.finditer(chunk.text):
        pieces.append(translate_plain(chunk.text[position : fence.start()]))
        if fence.group("lang").strip().lower() != "json":
            pieces.append(fence.group(0))
        else:
            source_json = json.loads(fence.group("body"))
            translated_json = translate_json_value(source_json)
            whole = fence.group(0)
            body_start = fence.start("body") - fence.start()
            body_end = fence.end("body") - fence.start()
            pieces.append(whole[:body_start])
            pieces.append(
                json.dumps(translated_json, ensure_ascii=False, indent=2) + "\n"
            )
            pieces.append(whole[body_end:])
        position = fence.end()
    pieces.append(translate_plain(chunk.text[position:]))

    combined = "".join(pieces)
    errors = validate_translation(chunk.text, combined)
    if errors:
        raise RuntimeError("fieldwise repair failed: " + "; ".join(errors))
    return combined, {
        "repair_mode": "fieldwise",
        "translated_units": unit_index,
        "unit_usage": usage_records,
    }


def plain_line_is_audit_candidate(line: str) -> bool:
    """Return whether an unchanged Markdown line looks like natural-language prose."""
    clean = translatable_prose(line).strip()
    stripped = line.strip()
    if "actual_behavior describes" in stripped:
        return True
    if len(clean) < 60 or len(COMMON_ENGLISH_PROSE_RE.findall(clean)) < 4:
        return False
    if (
        re.match(r"^Line \d+:", stripped)
        or "**Probe stdout" in stripped
        or "**Code evidence" in stripped
        or stripped.startswith(
            (
                "result =",
                "stdout =",
                "raise ",
                "if ",
                "for ",
                "while ",
                "return ",
                "WARNING:",
                "CONFIRMED",
                "NOT CONFIRMED",
                "[",
            )
        )
        or "lambda " in stripped
        or line.count(" = ") >= 2
        or (stripped.startswith("(") and line.count("(") >= 4)
        or (
            line.count("(") + line.count("{") + line.count("[") >= 5
            and line.count("=") >= 1
        )
    ):
        return False
    return True


def json_string_is_audit_candidate(key: str, source: str, translated: str) -> bool:
    return (
        source == translated
        and key not in PROTECTED_JSON_KEYS
        and key not in COMPLETENESS_EXEMPT_JSON_KEYS
        and len(source) >= 40
        and len(COMMON_ENGLISH_PROSE_RE.findall(source)) >= 3
    )


def json_has_unchanged_prose(source: Any, translated: Any) -> bool:
    if isinstance(source, dict) and isinstance(translated, dict):
        for key, source_item in source.items():
            if key not in translated:
                continue
            translated_item = translated[key]
            if (
                isinstance(source_item, str)
                and isinstance(translated_item, str)
                and json_string_is_audit_candidate(
                    key, source_item, translated_item
                )
            ):
                return True
            if json_has_unchanged_prose(source_item, translated_item):
                return True
    elif isinstance(source, list) and isinstance(translated, list):
        return any(
            json_has_unchanged_prose(source_item, translated_item)
            for source_item, translated_item in zip(source, translated)
        )
    return False


def chunk_has_unchanged_prose(source: str, translated: str) -> bool:
    source_fences = list(FENCE_RE.finditer(source))
    translated_fences = list(FENCE_RE.finditer(translated))
    if len(source_fences) != len(translated_fences):
        return False
    source_position = 0
    translated_position = 0
    for source_fence, translated_fence in zip(
        source_fences, translated_fences
    ):
        source_plain = source[source_position : source_fence.start()]
        translated_plain = translated[
            translated_position : translated_fence.start()
        ]
        if any(
            plain_line_is_audit_candidate(line)
            and line in translated_plain
            for line in source_plain.splitlines(keepends=True)
        ):
            return True
        if (
            source_fence.group("lang").strip().lower() == "json"
            and translated_fence.group("lang").strip().lower() == "json"
        ):
            try:
                source_json = json.loads(source_fence.group("body"))
                translated_json = json.loads(translated_fence.group("body"))
            except json.JSONDecodeError:
                pass
            else:
                if json_has_unchanged_prose(source_json, translated_json):
                    return True
        source_position = source_fence.end()
        translated_position = translated_fence.end()
    source_plain = source[source_position:]
    translated_plain = translated[translated_position:]
    return any(
        plain_line_is_audit_candidate(line) and line in translated_plain
        for line in source_plain.splitlines(keepends=True)
    )


def repair_unchanged_prose(
    client: OpenAI,
    chunk: Chunk,
    translated: str,
    model: str,
    max_tokens: int,
    attempts: int,
) -> tuple[str, dict[str, Any]]:
    """Translate natural-language source strings left unchanged in a cached result."""
    usage_records: list[dict[str, Any]] = []
    repair_count = 0

    def translate_unit(text: str) -> str:
        nonlocal repair_count
        unit = Chunk(
            source_name=chunk.source_name,
            output_name=chunk.output_name,
            index=chunk.index,
            text=text,
            item_id=chunk.item_id,
            key=f"{chunk.key}:audit:{repair_count}",
        )
        repaired, usage = translate_chunk(
            client,
            unit,
            model,
            max_tokens,
            attempts,
            strict_prose=True,
        )
        repair_count += 1
        usage_records.append(usage)
        return repaired

    def repair_plain(source_plain: str, translated_plain: str) -> str:
        for line in source_plain.splitlines(keepends=True):
            if plain_line_is_audit_candidate(line) and line in translated_plain:
                translated_plain = translated_plain.replace(
                    line, translate_unit(line), 1
                )
        return translated_plain

    def repair_json_value(source_value: Any, translated_value: Any) -> Any:
        if isinstance(source_value, dict) and isinstance(translated_value, dict):
            for key, source_item in source_value.items():
                if key not in translated_value:
                    continue
                translated_item = translated_value[key]
                if (
                    isinstance(source_item, str)
                    and isinstance(translated_item, str)
                    and json_string_is_audit_candidate(
                        key, source_item, translated_item
                    )
                ):
                    translated_value[key] = translate_unit(source_item)
                else:
                    repair_json_value(source_item, translated_item)
        elif isinstance(source_value, list) and isinstance(
            translated_value, list
        ):
            for source_item, translated_item in zip(
                source_value, translated_value
            ):
                repair_json_value(source_item, translated_item)
        return translated_value

    source_fences = list(FENCE_RE.finditer(chunk.text))
    translated_fences = list(FENCE_RE.finditer(translated))
    if len(source_fences) != len(translated_fences):
        raise RuntimeError("cannot audit-repair mismatched fence counts")
    pieces: list[str] = []
    source_position = 0
    translated_position = 0
    for source_fence, translated_fence in zip(
        source_fences, translated_fences
    ):
        pieces.append(
            repair_plain(
                chunk.text[source_position : source_fence.start()],
                translated[translated_position : translated_fence.start()],
            )
        )
        if (
            source_fence.group("lang").strip().lower() == "json"
            and translated_fence.group("lang").strip().lower() == "json"
        ):
            source_json = json.loads(source_fence.group("body"))
            translated_json = json.loads(translated_fence.group("body"))
            translated_json = repair_json_value(source_json, translated_json)
            whole = translated_fence.group(0)
            body_start = (
                translated_fence.start("body") - translated_fence.start()
            )
            body_end = translated_fence.end("body") - translated_fence.start()
            pieces.append(whole[:body_start])
            pieces.append(
                json.dumps(translated_json, ensure_ascii=False, indent=2) + "\n"
            )
            pieces.append(whole[body_end:])
        else:
            pieces.append(translated_fence.group(0))
        source_position = source_fence.end()
        translated_position = translated_fence.end()
    pieces.append(
        repair_plain(
            chunk.text[source_position:],
            translated[translated_position:],
        )
    )
    repaired = "".join(pieces)
    errors = validate_translation(chunk.text, repaired)
    if errors:
        raise RuntimeError("audit repair failed: " + "; ".join(errors))
    return repaired, {
        "repair_mode": "unchanged-prose-audit",
        "repair_count": repair_count,
        "unit_usage": usage_records,
    }


def build_outputs(
    state_dir: Path,
    by_output: dict[str, list[Chunk]],
) -> None:
    for output_name, chunks in by_output.items():
        parts = [
            read_cached_translation(state_dir, chunk) or chunk.text for chunk in chunks
        ]
        atomic_write_text(ROOT / output_name, "".join(parts))


def status_payload(
    state_dir: Path,
    chunks: list[Chunk],
    by_output: dict[str, list[Chunk]],
    started_at: str,
    failures: dict[str, str] | None = None,
) -> dict[str, Any]:
    completed_keys = {
        chunk.key
        for chunk in chunks
        if read_cached_translation(state_dir, chunk) is not None
    }
    item_chunks: dict[str, list[str]] = {}
    for chunk in chunks:
        if chunk.item_id:
            item_chunks.setdefault(chunk.item_id, []).append(chunk.key)
    complete_items = sum(
        all(key in completed_keys for key in keys) for keys in item_chunks.values()
    )
    partial_items = sum(
        any(key in completed_keys for key in keys)
        and not all(key in completed_keys for key in keys)
        for keys in item_chunks.values()
    )
    output_status = {}
    for output_name, output_chunks in by_output.items():
        done = sum(chunk.key in completed_keys for chunk in output_chunks)
        output_status[output_name] = {
            "completed_chunks": done,
            "total_chunks": len(output_chunks),
            "percent": round(100 * done / len(output_chunks), 2),
        }
    return {
        "prompt_version": PROMPT_VERSION,
        "started_at": started_at,
        "updated_at": utc_now(),
        "completed_chunks": len(completed_keys),
        "total_chunks": len(chunks),
        "percent": round(100 * len(completed_keys) / len(chunks), 2),
        "complete_items": complete_items,
        "partial_items": partial_items,
        "total_items": len(item_chunks),
        "failed_chunks": failures or {},
        "outputs": output_status,
    }


def print_status(state_dir: Path) -> int:
    path = state_dir / "status.json"
    if not path.is_file():
        print(json.dumps({"status": "not_started", "state_dir": str(state_dir)}))
        return 1
    print(path.read_text(encoding="utf-8"), end="")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate the three split FM-Agent bug reports with DeepSeek."
    )
    parser.add_argument("--env-file", help="dotenv file containing the API settings")
    parser.add_argument("--model", help="DeepSeek model (defaults to environment)")
    parser.add_argument("--base-url", help="OpenAI-compatible API base URL")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR))
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-chars", type=int, default=14000)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument(
        "--repair-split-chars",
        type=int,
        help=(
            "translate each pending original chunk in smaller Markdown blocks, "
            "then validate and cache the recombined original chunk"
        ),
    )
    parser.add_argument(
        "--repair-fieldwise",
        action="store_true",
        help=(
            "rebuild each pending chunk by translating prose lines and "
            "unprotected JSON string values separately"
        ),
    )
    parser.add_argument(
        "--audit-repair-unchanged",
        action="store_true",
        help=(
            "scan completed cache chunks and translate natural-language "
            "source lines/JSON values that remained byte-for-byte unchanged"
        ),
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        help="translate at most this many pending chunks (smoke-test mode)",
    )
    parser.add_argument("--status", action="store_true", help="print saved status and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state_dir = Path(args.state_dir).expanduser().resolve()
    if args.status:
        return print_status(state_dir)
    if (
        args.workers < 1
        or args.max_chars < 1000
        or args.max_tokens < 256
        or (
            args.repair_split_chars is not None
            and args.repair_split_chars < 1000
        )
    ):
        raise SystemExit("workers/max-chars/max-tokens are out of range")

    env_path = load_environment(args.env_file)
    api_key = (
        os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    base_url = (
        args.base_url
        or os.environ.get("DEEPSEEK_API_BASE_URL")
        or os.environ.get("LLM_API_BASE_URL")
        or "https://api.deepseek.com"
    )
    model = (
        args.model
        or os.environ.get("DEEPSEEK_MODEL")
        or os.environ.get("LLM_MODEL")
        or "deepseek-chat"
    )
    if not api_key:
        raise SystemExit("DeepSeek API key not found in DEEPSEEK_API_KEY/LLM_API_KEY")

    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / "run.lock"
    lock_handle = lock_path.open("w")
    try:
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("another translation process is already running")

    chunks, by_output = build_chunks(model, args.max_chars)
    started_at = utc_now()
    if args.audit_repair_unchanged:
        pending = []
        for chunk in chunks:
            translated = read_cached_translation(state_dir, chunk)
            if translated is not None and chunk_has_unchanged_prose(
                chunk.text, translated
            ):
                pending.append(chunk)
    else:
        pending = [
            chunk
            for chunk in chunks
            if read_cached_translation(state_dir, chunk) is None
        ]
    if args.max_chunks is not None:
        pending = pending[: max(0, args.max_chunks)]

    manifest = {
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "base_url": base_url,
        "env_file": str(env_path) if env_path else None,
        "max_chars": args.max_chars,
        "reports": [
            {
                "source": source,
                "output": output,
                "source_sha256": sha256_text((ROOT / source).read_text(encoding="utf-8")),
                "chunks": len(by_output[output]),
            }
            for source, output in REPORTS
        ],
        "total_chunks": len(chunks),
        "created_at": started_at,
    }
    atomic_write_json(state_dir / "manifest.json", manifest)
    build_outputs(state_dir, by_output)
    atomic_write_json(
        state_dir / "status.json",
        status_payload(state_dir, chunks, by_output, started_at),
    )

    print(
        f"[translation] model={model} base_url={base_url} "
        f"chunks={len(chunks)} pending_this_run={len(pending)} workers={args.workers}",
        flush=True,
    )
    client = OpenAI(
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        timeout=args.timeout,
        max_retries=2,
    )
    failures: dict[str, str] = {}
    completed_this_run = 0
    state_lock = threading.Lock()

    def worker(chunk: Chunk) -> tuple[Chunk, str, dict[str, Any]]:
        if args.audit_repair_unchanged:
            translated = read_cached_translation(state_dir, chunk)
            if translated is None:
                raise RuntimeError("audit target cache disappeared")
            translated, usage = repair_unchanged_prose(
                client,
                chunk,
                translated,
                model,
                args.max_tokens,
                args.attempts,
            )
        elif args.repair_fieldwise:
            translated, usage = translate_chunk_fieldwise(
                client,
                chunk,
                model,
                args.max_tokens,
                args.attempts,
            )
        elif args.repair_split_chars is not None:
            translated, usage = translate_chunk_in_parts(
                client,
                chunk,
                model,
                args.max_tokens,
                args.attempts,
                args.repair_split_chars,
            )
        else:
            translated, usage = translate_chunk(
                client, chunk, model, args.max_tokens, args.attempts
            )
        return chunk, translated, usage

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {executor.submit(worker, chunk): chunk for chunk in pending}
        for future in concurrent.futures.as_completed(future_map):
            chunk = future_map[future]
            try:
                _, translated, usage = future.result()
                save_cached_translation(
                    state_dir, chunk, translated, model=model, usage=usage
                )
                completed_this_run += 1
                result = "ok"
            except Exception as exc:
                failures[chunk.key] = (
                    f"{chunk.source_name} chunk={chunk.index} item={chunk.item_id}: "
                    f"{type(exc).__name__}: {exc}"
                )
                result = "failed"
            with state_lock:
                build_outputs(state_dir, by_output)
                payload = status_payload(
                    state_dir, chunks, by_output, started_at, failures
                )
                atomic_write_json(state_dir / "status.json", payload)
                print(
                    f"[translation] {result} {chunk.source_name} "
                    f"chunk={chunk.index} item={chunk.item_id or 'preamble'} "
                    f"progress={payload['completed_chunks']}/{payload['total_chunks']} "
                    f"items={payload['complete_items']}/{payload['total_items']}",
                    flush=True,
                )

    final = status_payload(state_dir, chunks, by_output, started_at, failures)
    atomic_write_json(state_dir / "status.json", final)
    build_outputs(state_dir, by_output)
    print(
        f"[translation] run_finished completed_this_run={completed_this_run} "
        f"overall={final['completed_chunks']}/{final['total_chunks']} "
        f"failed={len(failures)}",
        flush=True,
    )
    return (
        0
        if final["completed_chunks"] == final["total_chunks"] and not failures
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
