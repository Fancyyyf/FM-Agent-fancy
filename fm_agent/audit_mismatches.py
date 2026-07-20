#!/usr/bin/env python3
"""Build bug_list.md from one FM-Agent self-verification workspace.

This is deliberately an audit, not another "SPEC is the oracle" validator.  It
keeps the original mismatch and probe evidence visible while adding a separate
classification for specification errors, inference errors, credible
implementation defects, and contracts that need an owner decision.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "logic_verification_results"
EXTRACTED = ROOT / "extracted_functions"
VALIDATION = ROOT / "bug_validation"


# High-confidence implementation defects: the counterexample stays inside the
# declared input/schema domain and the violated property is supported by a
# caller, a repository invariant, a security/resource rule, or the function's
# own documented purpose.  This is still a static-audit label, not proof that a
# product owner chose the same contract.
IMPLEMENTATION_CANDIDATES = {
    "dashboard-py--render_recent",
    "dashboard-py--scan_bugs",
    "src--call_graph_edges-py--_normalize_endpoint_label",
    "src--entry_reasoning_pipeline-py--_count_mismatches",
    "src--entry_reasoning_pipeline-py--_extracted_file_to_source_rel",
    "src--env_check-py--_check_oh_my_openagent",
    "src--extract-py--_extract_func_name_brace",
    "src--extract-py--_extract_functions_indent",
    "src--extract-py--_strip_angle_brackets",
    "src--file_utils-py--_get_incomplete_verification_files",
    "src--file_utils-py--_json_file_is_valid",
    "src--generate_topdown_layers-py--_get_call_regex",
    "src--generate_topdown_layers-py--_load_phases",
    "src--git-py--_get_head_commit",
    "src--git-py--_is_git_repo",
    "src--incremental_reasoner-py--_funcs_from_commit",
    "src--incremental_reasoner-py--_opencode_select_json",
    "src--incremental_reasoner-py--_path_exists_in_commit",
    "src--incremental_reasoner-py--check_last_run_existence",
    "src--languages--codegraph-py--_bare_function_name",
    "src--languages--codegraph-py--_fqn_for",
    "src--languages--codegraph-py--from_proj_dir",
    "src--languages--codegraph-py--get_function_spans",
    "src--languages--erlang-py--__init___1",
    "src--languages--erlang-py--_elp_argv",
    "src--languages--erlang-py--_escape_component",
    "src--languages--erlang-py--_fingerprint_digest",
    "src--languages--erlang-py--_function_id",
    "src--languages--erlang-py--_next_message",
    "src--languages--erlang-py--_persist_analysis",
    "src--languages--erlang-py--_project_fingerprint",
    "src--languages--erlang-py--batch_extract",
    "src--languages--erlang-py--call_edges",
    "src--languages--erlang-py--close",
    "src--languages--erlang-py--initialize",
    "src--languages--registry-py--function_spans_for_file",
    "src--opencode_trace-py--_copy_opencode_output",
    "src--opencode_trace-py--_opencode_log_path",
    "src--opencode_trace-py--_opencode_trace_path",
    "src--opencode_trace-py--run_opencode_traced",
    "src--parser-py--_extract_function_name",
    "src--pipeline_setup-py--_collapse_phases_to_one",
    "src--pipeline_setup-py--_domain_context_complete",
    "src--pipeline_setup-py--_ensure_source_files_in_phases",
    "src--pipeline_setup-py--_run_generate_phases",
    "src--reasoner-py--_compute_brace_depth_per_line",
    "src--scope-py--_llm_rerank",
    "src--scope-py--_parse_issue_signals",
    "src--trace_writer-py--append_event",
    "src--verification-py--_validate_single_bug",
}


# These probes either violate the function's own pre-condition/schema, mutate
# trusted module internals, mock a callee contrary to its contract, or use a
# wrong semantic model.  They are implication/probe failures even when the
# generated probe prints CONFIRMED.
INVALID_COUNTEREXAMPLES = {
    "dashboard-py--_cost_from_usage",
    "dashboard-py--_fmt_duration",
    "dashboard-py--_push_recent",
    "dashboard-py--elapsed",
    "dashboard-py--render_header",
    "dashboard-py--render_stages",
    "dashboard-py--tail_events",
    "src--cli_backend-py--build_agent_command",
    "src--cli_backend-py--messages_to_prompt",
    "src--entry_reasoning_pipeline-py--_restrict_to_chains",
    "src--env_check-py--_check_comment_checker",
    "src--env_check-py--_check_llm_api_key",
    "src--env_check-py--is_interactive",
    "src--generate_batch_prompts-py--_info_line_mentions_name",
    "src--generate_batch_prompts-py--phase_callee_info_names_key",
    "src--generate_topdown_layers-py--_add_resolved_extra_edge",
    "src--generate_topdown_layers-py--_build_call_graph",
    "src--generate_topdown_layers-py--_file_to_fqn",
    "src--generate_topdown_layers-py--_get_keywords_for_lang",
    "src--generate_topdown_layers-py--_resolve_extra_call_edges",
    "src--git-py--_record_version",
    "src--incremental_reasoner-py--_reconcile_caller",
    "src--incremental_reasoner-py--_resolve_callee_fqns",
    "src--languages--cpp-py--batch_extract",
    "src--languages--erlang-py--_iter_project_files",
    "src--languages--erlang-py--_module_from_uri",
    "src--languages--erlang-py--_symbol_line_span",
    "src--languages--erlang-py--_symbol_range",
    "src--languages--erlang-py--position_to_offset",
    "src--languages--go-py--function_spans",
    "src--languages--java-py--function_spans",
    "src--languages--registry-py--batch_extract_all",
    "src--languages--rust-py--batch_extract",
    "src--llm_client-py--_http_status_from_exc",
    "src--llm_client-py--_read_error_body",
    "src--opencode_trace-py--finish_opencode_trace",
    "src--parser-py--add_entry",
    "src--pipeline_setup-py--_build_module_description_prompt",
    "src--pipeline_setup-py--_collect_changed_phases",
    "src--pipeline_setup-py--_filter_phases_to_submodules",
    "src--pipeline_setup-py--_phase_source_files",
    "src--pipeline_setup-py--_prepare_workflow_file",
    "src--pipeline_setup-py--types_path",
    "src--scope-py--_parse_generic_file",
    "src--scope-py--_fuzzy_name_score",
    "src--trace_writer-py--new_event_id",
    "src--verification-py--_generate_validation_summary",
    "src--verification-py--_spec_task_exit_code",
}


# A real implementation/SPEC difference exists, but repository evidence does
# not decide which side is intended.  These need a maintainer/product decision
# before being called either bugs or false positives.
CONTRACT_DECISIONS = {
    "dashboard-py--_parse_iso",
    "dashboard-py--bar_line",
    "dashboard-py--render_llm_status",
    "dashboard-py--tail_opencode",
    "main-py--_clean_previous_run",
    "main-py--_normalize_submodules",
    "src--call_graph_edges-py--_is_edge_file",
    "src--domain_knowledge-py--_split_env_paths",
    "src--domain_knowledge-py--stage_domain_knowledge_files",
    "src--entry_reasoning_pipeline-py--_trim_source_file",
    "src--file_utils-py--_write_file_names",
    "src--file_utils-py--collect_file_names",
    "src--generate_batch_prompts-py--list_staged_domain_knowledge_relpaths",
    "src--generate_batch_prompts-py--main",
    "src--git-py--frozen_worktree",
    "src--incremental_reasoner-py--flush",
    "src--incremental_reasoner-py--write",
    "src--languages--codegraph-py--try_codegraph_init",
    "src--languages--erlang-py--_callgraph_project_root",
    "src--languages--erlang-py--request",
    "src--llm_client-py--_matches_inject_target",
    "src--llm_client-py--_retry_create",
    "src--opencode_trace-py--_payload_dir",
    "src--opencode_trace-py--_start_opencode_process",
    "src--scope-py--_generic_func_info",
    "src--scope-py--_score_class",
}


SPECIAL_NOTES = {
    "main-py--run_pipeline": (
        "SPEC 自相矛盾：Pre-condition 明说无源文件时 sys.exit(1)，Post-condition "
        "又要求 empty file_list 正常返回；实现符合前者，checker 只使用了后者。"
    ),
    "src--cli_backend-py--resolve_model_backend": (
        "仓库 README/docs 明确默认 backend 是 opencode；SPEC 臆造了“环境变量缺失时自动探测”，"
        "所以把文档化默认行为报成 bug。"
    ),
    "src--domain_knowledge-py--resolve_domain_knowledge_paths": (
        "函数 docstring 明确是 Validate，源码与 README 都把不存在的知识文件视为配置错误；"
        "SPEC 反而要求静默丢弃。"
    ),
    "src--entry_reasoning_pipeline-py--run_entry_pipeline": (
        "SPEC 把“源码不被修改”扩大成“proj_dir 中任何文件都不写”；函数文档明确会把生成的 "
        "fm_agent/ 结果复制回 proj_dir，因此 mismatch 来自边界定义错误。"
    ),
    "src--generate_topdown_layers-py--_compute_layers": (
        "同一 SPEC 内部冲突：一条要求 callee 层号 <= caller，末条却说按 callers 已分配后入层；"
        "源码/函数注释采用 caller-first。错误的层序不变量还污染了下游 [INFO]。"
    ),
    "src--generate_topdown_layers-py--_tarjan_scc": (
        "源码 docstring 明确返回 reverse topological order；SPEC 把方向写反，probe 证明的只是 "
        "SPEC 与文档不一致。"
    ),
    "src--incremental_reasoner-py--_topdown_ordered_fqns": (
        "实现按升序 layer 返回 caller-first；mismatch 的 actual POST 错误沿用了“callee 在低层”的 "
        "[INFO]/domain-context 说法，是跨函数错误传播。"
    ),
    "src--languages--codegraph-py--get_call_edges": (
        "源码明确说明 Go/Rust/C 没有传统 constructor 并故意不合成 instantiates 边；SPEC 将这种 "
        "语言设计选择写成遗漏。"
    ),
    "src--languages--erlang-py--_analyze_project": (
        "缓存命中不联系 ELP 正是缓存的目的；SPEC 要求每次验证 ELP 可用性，反而取消缓存语义。"
    ),
    "src--languages--erlang-py--function_spans": (
        "源码 docstring 规定 None 同时表示未索引或无函数，并触发 regex fallback；SPEC 擅自要求 []。"
    ),
    "src--languages--erlang-py--position_to_offset": (
        "checker 把 Python str 下标误当 UTF-8 byte offset。line_offsets 由 len(str) 构造，最终也用于 "
        "str 切片；对 'éa' 返回 1 是正确的字符下标，probe 的 expected=2 使用了错误 oracle。"
    ),
    "src--llm_client-py--_llm_json_call": (
        "trace_dir=None 时不落盘是 trace_writer 的显式 no-op 协议；SPEC 却要求在没有目标目录时仍有"
        "持久记录，这是不可满足契约。"
    ),
    "src--parser-py--parse_input_function": (
        "函数目的就是给 reasoner 提供去注释代码；SPEC 只允许删整行注释、禁止删行尾注释，没有调用方"
        "或文档依据。验证报告自身也承认其中一个子 claim 未复现。"
    ),
    "src--reasoner-py--_has_terminating_statement": (
        "调用方需要知道 block 是否“含有”提前终止路径以触发检查；SPEC 将函数提升为“所有路径都终止”"
        "的控制流证明器，与正则实现和调用方式都不符。"
    ),
    "src--reasoner-py--_split_into_blocks_braced": (
        "最终右花括号把深度从 entry depth 降到 0 是函数正常结束；SPEC 要求每个块都停在 entry depth，"
        "错误排除了合法的最后一块。"
    ),
    "src--scope-py--_rank_functions": (
        "CALLER_INHERIT 与 CALLEE_INHERIT 是两个显式独立的排序权重；SPEC 无依据要求二者相等。"
    ),
    "src--trace_writer-py--record_llm_exchange": (
        "该函数职责就是给 event 增补 metadata/children 后写 trace；SPEC 禁止增加 metadata，直接否定"
        "了函数的主要用途。"
    ),
    "src--verification-py--streaming_reasoner": (
        "等待 reasoning/validation futures 清空可避免遗弃已提交任务；SPEC 要求 spec 进程结束就立即"
        "退出，会产生不完整结果。"
    ),
}


PRIORITY_REPORTS = [
    (
        "src--languages--erlang-py--call_edges",
        "P0",
        "Erlang adapter 直接返回 tuple-key 图，registry/generate_topdown 以 FQN string 查询时会丢失边。",
    ),
    (
        "src--languages--erlang-py--batch_extract",
        "P0",
        "转义非单射导致不同 Erlang function id 碰撞，后一个函数会被静默丢弃。",
    ),
    (
        "src--opencode_trace-py--_opencode_log_path",
        "P0",
        "未约束 event_id，绝对路径可逃逸 work_dir。",
    ),
    (
        "src--opencode_trace-py--_opencode_trace_path",
        "P0",
        "与 log path 相同的绝对路径逃逸问题。",
    ),
    (
        "src--opencode_trace-py--run_opencode_traced",
        "P0",
        "wait 返回 error 但 exit_code 为 0 时，最终 trace 仍记录 success。",
    ),
    (
        "src--pipeline_setup-py--_run_generate_phases",
        "P0",
        "只验证 JSON 可解析，不验证 phases schema，损坏产物会进入后续全管线。",
    ),
    (
        "src--generate_topdown_layers-py--_load_phases",
        "P0",
        "加载 phases.json 不做结构校验，与上一项共同放大 LLM 产物错误。",
    ),
    (
        "src--generate_topdown_layers-py--_get_call_regex",
        "P1",
        "嵌套泛型模板调用不能匹配，影响 C++/Java 等调用图完整性。",
    ),
    (
        "src--extract-py--_extract_func_name_brace",
        "P1",
        "C++ operator, 无法提取。",
    ),
    (
        "src--extract-py--_extract_functions_indent",
        "P1",
        "合法 Python 多行函数头的续行形式会漏提取。",
    ),
    (
        "src--languages--codegraph-py--_bare_function_name",
        "P1",
        "Go pointer receiver 形式可被 function-pointer 分支抢先误解析。",
    ),
    (
        "src--languages--codegraph-py--_fqn_for",
        "P1",
        "Windows 风格反斜杠未统一，跨平台 FQN 不一致。",
    ),
    (
        "src--reasoner-py--_compute_brace_depth_per_line",
        "P1",
        "跨行 block comment 状态未保持，会错误切块并污染 POST 推理。",
    ),
    (
        "src--scope-py--_llm_rerank",
        "P1",
        "接受不属于候选集合的 LLM 函数名，可能把增量范围定位到不存在的目标。",
    ),
    (
        "src--trace_writer-py--append_event",
        "P1",
        "已有 JSONL 尾部缺换行时直接拼接，导致新旧两条记录同时损坏。",
    ),
]


def _rel_from_id(bug_id: str, suffix: str) -> Path:
    parts = bug_id.split("--")
    return Path(*parts[:-1], parts[-1] + suffix)


def _extract_sections(text: str) -> tuple[str, str]:
    pre = re.search(
        r"Pre-condition:\s*\n(.*?)(?=\n\s*(?://|#|%|--)?\s*Post-condition:)",
        text,
        re.S,
    )
    post = re.search(
        r"Post-condition:\s*\n(.*?)(?=\n\s*(?://|#|%|--)?\s*\[SPEC\])",
        text,
        re.S,
    )

    def clean(match: re.Match[str] | None) -> str:
        if not match:
            return "（未提取到）"
        value = re.sub(r"^\s*(?://|#|%|--)\s?", "", match.group(1), flags=re.M)
        return re.sub(r"\s+", " ", value).strip()

    return clean(pre), clean(post)


def _short(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _classify(item: dict) -> tuple[str, str]:
    bug_id = item["id"]
    if item.get("confirmation_status") != "confirmed":
        return "推理误判", "validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。"
    if bug_id in INVALID_COUNTEREXAMPLES:
        return "推理误判", "probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。"
    if bug_id in CONTRACT_DECISIONS:
        return "契约待确认", "实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。"
    if bug_id in IMPLEMENTATION_CANDIDATES:
        return "实现缺陷候选", "反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。"
    return "SPEC 错误", "差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。"


def main() -> None:
    result_files = sorted(RESULTS.rglob("*.json"))
    verdicts = Counter()
    result_by_id = {}
    for path in result_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        verdicts[data.get("verdict", "UNKNOWN")] += 1
        bug_id = str(path.relative_to(RESULTS).with_suffix("")).replace("/", "--")
        result_by_id[bug_id] = data

    summary = json.loads((VALIDATION / "summary.json").read_text(encoding="utf-8"))
    items = summary["bugs"]
    # Runtime bytecode caches are not extracted functions.  Some validation
    # probes import copies from this tree and can leave __pycache__ artifacts.
    extracted_files = [
        path
        for path in EXTRACTED.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    ]
    ready_files = []
    for path in extracted_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        if text.count("[SPEC]") >= 2 and text.count("[INFO]") >= 2:
            ready_files.append(path)

    classified = []
    for index, item in enumerate(items, 1):
        category, reason = _classify(item)
        classified.append((index, item, category, reason))
    audit_counts = Counter(category for _, _, category, _ in classified)

    mismatch = verdicts["MISMATCH"]
    total = sum(verdicts.values())
    confirmed = summary["total_confirmed"]
    not_confirmed = summary["total_not_confirmed"]
    high_conf_false = audit_counts["推理误判"] + audit_counts["SPEC 错误"]

    lines = [
        "# FM-Agent 自验证 mismatch 审计与 Bug 清单",
        "",
        "> 生成口径：`fm_agent/audit_mismatches.py` 对本目录现有产物做静态复核。",
        "> “confirmed”仅表示 probe 观察到实现与生成 SPEC 不同，不等于确认了产品 bug。",
        "",
        "## 总括",
        "",
        "本次 FM-Agent 对自身代码的验证产物明显失真。"
        f"共发现 **{len(extracted_files)}** 个 extracted-function 文件，其中 **{len(ready_files)}** 个已有完整 `[SPEC]/[INFO]`；"
        f"生成 **{total}** 份逻辑结果，覆盖全部 extracted 文件的 **{total / len(extracted_files):.2%}**，"
        f"覆盖 ready 文件的 **{total / len(ready_files):.2%}**。结果为 **{verdicts['MATCH']} MATCH / "
        f"{mismatch} MISMATCH / {verdicts['ERROR']} ERROR**。原始 mismatch 率为 "
        f"**{mismatch / total:.2%}**，这与一个可用的自验证器不相称。",
        "",
        f"内置 bug validator 覆盖了全部 {mismatch} 条 MISMATCH，并报告 {confirmed} confirmed、"
        f"{not_confirmed} not_confirmed：按它自己的口径，直接误判率至少为 "
        f"**{not_confirmed / mismatch:.2%}**（占全部结果 {not_confirmed / total:.2%}）。"
        "但 confirmed probe 的 expected 值通常直接来自同一份 LLM SPEC，因此存在循环论证。",
        "",
        "将 SPEC、Pre-condition、推导 POST、源码/调用方和 probe 一起复核后，本清单给出以下静态审计分层：",
        "",
        "| 审计类别 | 数量 | 占 MISMATCH | 含义 |",
        "|---|---:|---:|---|",
        f"| 推理误判 | {audit_counts['推理误判']} | {audit_counts['推理误判'] / mismatch:.2%} | 代码理解错误、反例违反前置条件/Schema、错误 mock/callee 语义；包含 validator 已 not_confirmed 的项目 |",
        f"| SPEC 错误 | {audit_counts['SPEC 错误']} | {audit_counts['SPEC 错误'] / mismatch:.2%} | 差异可能真实，但 SPEC 自造、过强、自相矛盾或与仓库文档相反 |",
        f"| 契约待确认 | {audit_counts['契约待确认']} | {audit_counts['契约待确认'] / mismatch:.2%} | 实现与 SPEC 确有差异，现有仓库证据不能决定期望行为 |",
        f"| 实现缺陷候选 | {audit_counts['实现缺陷候选']} | {audit_counts['实现缺陷候选'] / mismatch:.2%} | 有独立仓库不变量/调用影响支持，值得修复或补测试 |",
        "",
        f"因此，**高置信度误报下界**（推理误判 + SPEC 错误）为 **{high_conf_false}/{mismatch} = "
        f"{high_conf_false / mismatch:.2%}**。若把尚无产品契约支持的“契约待确认”也按不可直接报 bug 处理，"
        f"当前可直接进入修复队列的只有 **{audit_counts['实现缺陷候选']}/{mismatch} = "
        f"{audit_counts['实现缺陷候选'] / mismatch:.2%}**。这些数字是静态审计结果，不是假装拥有外部 ground truth。",
        "",
        "另外有 10 个 ready function 没有逻辑结果；3 个 ERROR 均为 LLM 连接重试耗尽。"
        "因此 97.37% 是产物覆盖率，不是验证成功率。统计已排除 probe import 产生的 `__pycache__/*.pyc`。",
        "",
        "## 优先排查的具体 bug 报告",
        "",
        "以下是 50 个“实现缺陷候选”中影响面最大的项目；编号仍以逐条清单中的原始 bug id 为准。",
        "",
        "| 优先级 | bug id / 具体报告 | 独立影响判断 |",
        "|---|---|---|",
        *[
            f"| {priority} | [`{bug_id}`](bug_validation/{bug_id}.md) | {impact} |"
            for bug_id, priority, impact in PRIORITY_REPORTS
        ],
        "",
        "## 主要成因",
        "",
        "1. **SPEC 生成没有证据层级。** system prompt 要求 caller-driven intended behavior，但模型大量把格式偏好、"
        "防御性容错、缓存实现、绝对路径、异常吞咽、原子替换等臆造成 MUST。没有区分 README/调用方明确契约、"
        "类型/Schema 不变量、实现猜测和纯偏好。",
        "2. **checker 没有强制反例满足 Pre-condition。** 字符串 token、负 duration、缺失 State 字段、None proj_dir、"
        "非整数 LSP position、被删除的模块全局变量、畸形 JSON schema 等仍被当成 valid input。",
        "3. **POST 推理是自然语言近似，不是 strongest post-condition。** 它会把 Python 字符下标当 byte offset、"
        "漏看 stdin 中的文件列表、误判缩进/return 位置、忽略 deque(maxlen) 语义，再由第二个 LLM 对错误 POST 作蕴含检查。",
        "4. **[INFO]/domain context 会级联污染。** 最明显的是层序方向：engine overview 写“callee 在低层”，"
        "而 `_compute_layers` 代码和 caller-driven 生成顺序是 caller-first；错误 callee contract 继续污染"
        " `_topdown_ordered_fqns` 等下游函数。",
        "5. **bug validator 使用自指 oracle。** probe 通常构造 `expected = spec_claim`，只证明实现不同于 SPEC；"
        "它不检查 SPEC 是否来自文档、调用者或测试。因此 84.98% 的“confirmed”不能解释成真实 bug 精度。",
        "6. **缺少独立测试/双向验证。** 仓库中没有可作为 ground truth 的测试集；validator 也未执行"
        "“反例是否满足 precondition”“SPEC 是否与 caller/README 冲突”“actual POST 是否可由运行结果支持”三道门。",
        "",
        "## 建议的验证器修正顺序",
        "",
        "1. 给 SPEC 每条 post-condition 附 `evidence` 和 `confidence`：仅允许 caller、README、类型/Schema、"
        "用户 domain knowledge 进入 hard contract；实现推断只能是 soft hypothesis。",
        "2. implication prompt 必须先输出 `counterexample_satisfies_precondition: true/false`；false 时强制 MATCH/INCONCLUSIVE，"
        "不得产生 MISMATCH。",
        "3. 对每个函数保存结构化 `{pre, spec_post[], inferred_post[], counterexample, evidence}`，避免整段自然语言互相污染。",
        "4. validator 先验证 SPEC，再验证实现：`SPEC_INVALID`、`INFERENCE_ERROR`、`CONTRACT_AMBIGUOUS`、"
        "`IMPLEMENTATION_BUG` 四态替代 confirmed/not_confirmed 二态。",
        "5. 将 repo invariant 做一致性检查；相反约束（例如 caller-first 与 callee-first）出现时停止下游验证，"
        "不要继续生成数十条派生 mismatch。",
        "6. 为下列高价值模块先补小型回归测试：语言抽取/FQN、Erlang edge adapter、JSON/schema 边界、"
        "trace 路径与资源关闭、layer ordering。",
        "",
        "## 分类说明",
        "",
        "- `推理误判`：actual POST/代码读取错，或 counterexample 不满足该函数自己的 Pre-condition/上游 Schema。",
        "- `SPEC 错误`：probe 可复现差异，但仓库独立证据支持实现，或 SPEC 是无依据的强化。",
        "- `契约待确认`：不能从当前仓库判断产品到底要哪种行为，必须由维护者选择并补测试。",
        "- `实现缺陷候选`：不是最终定罪；表示该项已有独立证据，优先级显著高于普通 mismatch。",
        "",
        "## 逐条 MISMATCH 清单",
        "",
        "每项都给出可检索编号、原始 bug id、完整生成 SPEC、推导 POST/result JSON、validator 报告与 probe。"
        "摘录用于快速定位，链接文件保留完整原文。",
        "",
    ]

    grouped: dict[str, list[tuple[int, dict, str, str]]] = defaultdict(list)
    for row in classified:
        module = row[1]["id"].rsplit("--", 1)[0]
        grouped[module].append(row)

    for module, rows in grouped.items():
        lines.extend([f"### `{module}`", ""])
        for index, item, category, reason in rows:
            bug_id = item["id"]
            rel = _rel_from_id(bug_id, ".json")
            result = result_by_id.get(bug_id, {})
            gaps = result.get("gaps") or {}
            source_rel = rel.with_suffix(".py")
            source_path = EXTRACTED / source_rel
            source_text = source_path.read_text(encoding="utf-8", errors="replace") if source_path.exists() else ""
            pre, generated_post = _extract_sections(source_text)
            report_rel = Path("bug_validation") / f"{bug_id}.md"
            probe_rel = Path("bug_validation") / f"probe_{bug_id}.py"
            result_rel = Path("logic_verification_results") / rel
            source_link = source_rel.as_posix()
            report_link = report_rel.as_posix()
            probe_link = probe_rel.as_posix()
            result_link = result_rel.as_posix()
            status = item.get("confirmation_status", "unknown")
            special = SPECIAL_NOTES.get(bug_id)
            audit_reason = special or reason
            report_name = f"FMA-MISMATCH-{index:03d}"

            lines.extend([
                f"#### {report_name} — `{bug_id}`",
                "",
                f"- 结论：**{category}**；内置 validator：`{status}`。",
                f"- 证据：[`[SPEC]` 原文](extracted_functions/{source_link}) · "
                f"[推导 POST / result]({result_link}) · [具体 bug 报告]({report_link}) · "
                f"[probe]({probe_link})",
                f"- 触发/冲突：{_short(item.get('trigger_summary', ''), 520)}",
                f"- 成因复核：{audit_reason}",
                "",
                "<details><summary>SPEC / POST 摘录</summary>",
                "",
                f"- Pre-condition：{_short(pre, 420)}",
                f"- FMA SPEC post-condition：{_short(gaps.get('spec_claim') or generated_post, 760)}",
                f"- FMA 推导 actual POST：{_short(gaps.get('actual_behavior', ''), 760)}",
                "",
                "</details>",
                "",
            ])

    missing_ready = []
    result_rels = {path.relative_to(RESULTS) for path in result_files}
    for path in ready_files:
        rel = path.relative_to(EXTRACTED).with_suffix(".json")
        if rel not in result_rels:
            missing_ready.append(rel.as_posix())

    error_rows = []
    for path in result_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("verdict") == "ERROR":
            error_rows.append((path.relative_to(RESULTS).as_posix(), data.get("error", "")))

    lines.extend([
        "## 非 MISMATCH 的完整性问题",
        "",
        "### 已 ready 但没有 result 的 10 个函数",
        "",
        *[f"- `{value}`" for value in missing_ready],
        "",
        "### ERROR 结果",
        "",
        *[f"- `{path}`：{error}" for path, error in error_rows],
        "",
        "## 复核边界",
        "",
        "本报告没有把生成 SPEC 自动视为 ground truth，也没有在缺乏产品契约时擅自改源码。"
        "“实现缺陷候选”应逐项转成维护者认可的测试后再修；“契约待确认”应先决定行为；"
        "“SPEC 错误/推理误判”应进入验证器评测集，防止下一轮再次制造同类 mismatch。",
        "",
    ])

    (ROOT / "bug_list.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
