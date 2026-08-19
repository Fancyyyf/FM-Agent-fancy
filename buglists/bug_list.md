# FM-Agent 自验证 mismatch 审计与 Bug 清单

> 生成口径：`fm_agent/audit_mismatches.py` 对本目录现有产物做静态复核；后续 restore 重跑解决 3 个 ERROR 并补齐 10 个无结果函数后，本文已按新产物增量更新。
> “confirmed”仅表示 probe 观察到实现与生成 SPEC 不同，不等于确认了产品 bug。

## 总括

本次 FM-Agent 对自身代码的验证产物明显失真。共发现 **380** 个 extracted-function 文件，其中 **380** 个已有完整 `[SPEC]/[INFO]`；恢复重跑后已生成 **380** 份逻辑结果，对 extracted/ready 文件的覆盖率均为 **100.00%**。最终结果为 **115 MATCH / 265 MISMATCH / 0 ERROR**，原始 mismatch 率为 **69.74%**，这与一个可用的自验证器不相称。

内置 bug validator 覆盖了全部 265 条 MISMATCH，并报告 222 confirmed、43 not_confirmed：按它自己的口径，直接误判率至少为 **16.23%**（占全部结果 11.32%）。但 confirmed probe 的 expected 值通常直接来自同一份 LLM SPEC，因此存在循环论证。

恢复重跑前后的 3 项变化如下。这说明原 ERROR 是可恢复的 LLM 连接故障，不是对三个函数的逻辑判定；重跑后仍需分别审查新 verdict。

| 函数 | 重跑前 | 重跑后 | 后续复核 |
|---|---|---|---|
| `src/reasoner.py::_sanitize_strings` | ERROR | MATCH | 未发现 mismatch |
| `src/reasoner.py::reasoner` | ERROR | MATCH | 未发现 mismatch |
| `src/file_utils.py::_iter_project_source_files` | ERROR | MISMATCH | validator `not_confirmed`；归类为推理误判 |

将 SPEC、Pre-condition、推导 POST、源码/调用方和 probe 一起复核后，本清单给出以下静态审计分层：

| 审计类别 | 数量 | 占 MISMATCH | 含义 |
|---|---:|---:|---|
| 推理误判 | 93 | 35.09% | 代码理解错误、反例违反前置条件/Schema、错误 mock/callee 语义；包含 validator 已 not_confirmed 的项目 |
| SPEC 错误 | 92 | 34.72% | 差异可能真实，但 SPEC 自造、过强、自相矛盾或与仓库文档相反 |
| 契约待确认 | 26 | 9.81% | 实现与 SPEC 确有差异，现有仓库证据不能决定期望行为 |
| 实现缺陷候选 | 54 | 20.38% | 有独立仓库不变量/调用影响支持，值得修复或补测试 |

因此，**高置信度误报下界**（推理误判 + SPEC 错误）为 **185/265 = 69.81%**。若把尚无产品契约支持的“契约待确认”也按不可直接报 bug 处理，当前可直接进入修复队列的只有 **54/265 = 20.38%**。这些数字是静态审计结果，不是假装拥有外部 ground truth。

原先无 result 的 10 个 ready function 已全部补跑，均生成 MISMATCH；原有 3 个 ERROR 也已通过恢复重跑清零。当前 380 份结果均已得到 MATCH 或 MISMATCH 逻辑结论，但仍不代表结论正确。统计已排除 probe import 产生的 `__pycache__/*.pyc`。

## 优先排查的具体 bug 报告

以下是 54 个“实现缺陷候选”中影响面最大的项目；编号仍以逐条清单中的原始 bug id 为准。

| 优先级 | bug id / 具体报告 | 独立影响判断 |
|---|---|---|
| P0 | [`src--languages--erlang-py--call_edges`](../fm_agent/bug_validation/src--languages--erlang-py--call_edges.md) | Erlang adapter 直接返回 tuple-key 图，registry/generate_topdown 以 FQN string 查询时会丢失边。 |
| P0 | [`src--languages--erlang-py--batch_extract`](../fm_agent/bug_validation/src--languages--erlang-py--batch_extract.md) | 转义非单射导致不同 Erlang function id 碰撞，后一个函数会被静默丢弃。 |
| P0 | [`src--opencode_trace-py--_opencode_log_path`](../fm_agent/bug_validation/src--opencode_trace-py--_opencode_log_path.md) | 未约束 event_id，绝对路径可逃逸 work_dir。 |
| P0 | [`src--opencode_trace-py--_opencode_trace_path`](../fm_agent/bug_validation/src--opencode_trace-py--_opencode_trace_path.md) | 与 log path 相同的绝对路径逃逸问题。 |
| P0 | [`src--opencode_trace-py--run_opencode_traced`](../fm_agent/bug_validation/src--opencode_trace-py--run_opencode_traced.md) | wait 返回 error 但 exit_code 为 0 时，最终 trace 仍记录 success。 |
| P0 | [`src--pipeline_setup-py--_run_generate_phases`](../fm_agent/bug_validation/src--pipeline_setup-py--_run_generate_phases.md) | 只验证 JSON 可解析，不验证 phases schema，损坏产物会进入后续全管线。 |
| P0 | [`src--generate_topdown_layers-py--_load_phases`](../fm_agent/bug_validation/src--generate_topdown_layers-py--_load_phases.md) | 加载 phases.json 不做结构校验，与上一项共同放大 LLM 产物错误。 |
| P1 | [`src--generate_topdown_layers-py--_get_call_regex`](../fm_agent/bug_validation/src--generate_topdown_layers-py--_get_call_regex.md) | 嵌套泛型模板调用不能匹配，影响 C++/Java 等调用图完整性。 |
| P1 | [`src--extract-py--_extract_func_name_brace`](../fm_agent/bug_validation/src--extract-py--_extract_func_name_brace.md) | C++ operator, 无法提取。 |
| P1 | [`src--extract-py--_extract_functions_indent`](../fm_agent/bug_validation/src--extract-py--_extract_functions_indent.md) | 合法 Python 多行函数头的续行形式会漏提取。 |
| P1 | [`src--languages--codegraph-py--_bare_function_name`](../fm_agent/bug_validation/src--languages--codegraph-py--_bare_function_name.md) | Go pointer receiver 形式可被 function-pointer 分支抢先误解析。 |
| P1 | [`src--languages--codegraph-py--_fqn_for`](../fm_agent/bug_validation/src--languages--codegraph-py--_fqn_for.md) | Windows 风格反斜杠未统一，跨平台 FQN 不一致。 |
| P1 | [`src--reasoner-py--_compute_brace_depth_per_line`](../fm_agent/bug_validation/src--reasoner-py--_compute_brace_depth_per_line.md) | 跨行 block comment 状态未保持，会错误切块并污染 POST 推理。 |
| P1 | [`src--scope-py--_llm_rerank`](../fm_agent/bug_validation/src--scope-py--_llm_rerank.md) | 接受不属于候选集合的 LLM 函数名，可能把增量范围定位到不存在的目标。 |
| P1 | [`src--trace_writer-py--append_event`](../fm_agent/bug_validation/src--trace_writer-py--append_event.md) | 已有 JSONL 尾部缺换行时直接拼接，导致新旧两条记录同时损坏。 |

## 主要成因

1. **SPEC 生成没有证据层级。** system prompt 要求 caller-driven intended behavior，但模型大量把格式偏好、防御性容错、缓存实现、绝对路径、异常吞咽、原子替换等臆造成 MUST。没有区分 README/调用方明确契约、类型/Schema 不变量、实现猜测和纯偏好。
2. **checker 没有强制反例满足 Pre-condition。** 字符串 token、负 duration、缺失 State 字段、None proj_dir、非整数 LSP position、被删除的模块全局变量、畸形 JSON schema 等仍被当成 valid input。
3. **POST 推理是自然语言近似，不是 strongest post-condition。** 它会把 Python 字符下标当 byte offset、漏看 stdin 中的文件列表、误判缩进/return 位置、忽略 deque(maxlen) 语义，再由第二个 LLM 对错误 POST 作蕴含检查。
4. **[INFO]/domain context 会级联污染。** 最明显的是层序方向：engine overview 写“callee 在低层”，而 `_compute_layers` 代码和 caller-driven 生成顺序是 caller-first；错误 callee contract 继续污染 `_topdown_ordered_fqns` 等下游函数。
5. **bug validator 使用自指 oracle。** probe 通常构造 `expected = spec_claim`，只证明实现不同于 SPEC；它不检查 SPEC 是否来自文档、调用者或测试。因此 83.77% 的“confirmed”不能解释成真实 bug 精度。
6. **缺少独立测试/双向验证。** 仓库中没有可作为 ground truth 的测试集；validator 也未执行“反例是否满足 precondition”“SPEC 是否与 caller/README 冲突”“actual POST 是否可由运行结果支持”三道门。

## 建议的验证器修正顺序

1. 给 SPEC 每条 post-condition 附 `evidence` 和 `confidence`：仅允许 caller、README、类型/Schema、用户 domain knowledge 进入 hard contract；实现推断只能是 soft hypothesis。
2. implication prompt 必须先输出 `counterexample_satisfies_precondition: true/false`；false 时强制 MATCH/INCONCLUSIVE，不得产生 MISMATCH。
3. 对每个函数保存结构化 `{pre, spec_post[], inferred_post[], counterexample, evidence}`，避免整段自然语言互相污染。
4. validator 先验证 SPEC，再验证实现：`SPEC_INVALID`、`INFERENCE_ERROR`、`CONTRACT_AMBIGUOUS`、`IMPLEMENTATION_BUG` 四态替代 confirmed/not_confirmed 二态。
5. 将 repo invariant 做一致性检查；相反约束（例如 caller-first 与 callee-first）出现时停止下游验证，不要继续生成数十条派生 mismatch。
6. 为下列高价值模块先补小型回归测试：语言抽取/FQN、Erlang edge adapter、JSON/schema 边界、trace 路径与资源关闭、layer ordering。

## 分类说明

- `推理误判`：actual POST/代码读取错，或 counterexample 不满足该函数自己的 Pre-condition/上游 Schema。
- `SPEC 错误`：probe 可复现差异，但仓库独立证据支持实现，或 SPEC 是无依据的强化。
- `契约待确认`：不能从当前仓库判断产品到底要哪种行为，必须由维护者选择并补测试。
- `实现缺陷候选`：不是最终定罪；表示该项已有独立证据，优先级显著高于普通 mismatch。

## 逐条 MISMATCH 清单

每项都给出可检索编号、原始 bug id、完整生成 SPEC、推导 POST/result JSON、validator 报告与 probe。摘录用于快速定位，链接文件保留完整原文。

### `dashboard-py`

#### FMA-MISMATCH-001 — `dashboard-py--_cache_rate`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/_cache_rate.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/_cache_rate.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--_cache_rate.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--_cache_rate.py)
- 触发/冲突：When input_sum == 0 (e.g. empty rows []), the code returns None as rate instead of the specified 0.0.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- rows is a sequence of (cache_read, total_input) pairs where both cache_read and total_input are non-negative numeric values.
- FMA SPEC post-condition：- Returns a 3-tuple (rate, cache_read_sum, input_sum). - cache_read_sum is the sum of all cache_read values across rows. - input_sum is the sum of all total_input values across rows. - When input_sum > 0: rate is cache_read_sum / input_sum, a float in the range [0.0, ) representing the fraction of total input tokens served from cache. - When input_sum == 0: rate is 0.0. - The type of each sum is determined by the numeric types present in rows (the result of adding the values in the sequence).
- FMA 推导 actual POST：The function returns a tuple (result, cr_total, in_total) such that cr_total = sum(cr for (cr, _) in rows) and in_total = sum(t for (_, t) in rows), both nonnegative. If in_total == 0 then result is None; otherwise result = cr_total / in_total. No exceptions are raised. Formally: rows where rows is a sequence of pairs (cr, t) with cr 0 and t 0, let S_cr = _{ (cr, t) rows } cr and S_t = _{ (cr, t) rows } t. The return value r satisfies: r = (None, S_cr, S_t) if S_t = 0, else r = (S_cr / S_t, S_cr, S_t).

</details>

#### FMA-MISMATCH-002 — `dashboard-py--_cost_from_usage`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/_cost_from_usage.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/_cost_from_usage.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--_cost_from_usage.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--_cost_from_usage.py)
- 触发/冲突：Passing string token counts in the usage dict (e.g. {"input_tokens": "150"}) causes _cost_from_usage to raise TypeError instead of returning a float.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- model is a string identifying an LLM model, or None - usage is a dict whose values are non-negative numeric token counts, or None / a falsy value
- FMA SPEC post-condition：- Returns a non-negative float representing the total cost in USD of the token consumption recorded in usage, priced according to the per-token rates of the model's known pricing tier - Four token categories are recognized: input tokens, output tokens, cache-read tokens, and cache-creation tokens; each is priced at a distinct per-token rate determined independently by the model's pricing tier - A token category not present in usage, or present with a falsy value, contributes zero to the total - A pricing component not present in the model's tier contributes zero to the total - Returns 0.0 when model is None, usage is falsy, or no pricing tier is associated with model
- FMA 推导 actual POST：The function returns a non-negative float value `cost` representing the total cost in USD for the given usage, computed from per-token prices obtained via `_price_for(model)`. If `_price_for(model)` returns a falsy value (e.g., `None`) or if `usage` is falsy (e.g., `None`), `cost` is exactly `0.0`. Otherwise, let `p = _price_for(model)` be a dictionary mapping price component names to positive floats. For each token type `k` in {"input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"}, let `tokens_k = (usage.get(k, 0) or 0)` (i.e., the token count if present and truthy, else 0). The corresponding price `price_k = (p.get(price_key) or 0)` where the price key for each token type is: "input_cost_per_token" for input_to…

</details>

#### FMA-MISMATCH-003 — `dashboard-py--_fmt_duration`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/_fmt_duration.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/_fmt_duration.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--_fmt_duration.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--_fmt_duration.py)
- 触发/冲突：With negative seconds=-1.2, int() truncates toward zero giving -1, while math.floor() gives -2; code enters the hour branch (if h: with h=-1 is truthy) and returns '-1h 59m 59s' instead of the spec-required '-2s'.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- seconds is either None or a non-negative numeric value
- FMA SPEC post-condition：- When seconds is None, returns the literal string "" (U+2014 EM DASH) - When seconds is not None, returns a string composed of up to three space-separated segments ordered by decreasing time-unit magnitude (hours, then minutes, then seconds), where each segment has the form "<value><unit-suffix>" with unit-suffix in {"h", "m", "s"}: * The hour segment ("<H>h") appears only when floor(seconds) >= 3600; its value is the whole-hour count, never zero-padded * The minute segment ("<M>m" or "<MM>m") appears when floor(seconds) >= 60; its value is zero-padded to two digits only when the hour segment is present, otherwise it is the bare whole-minute count * The second segment ("<S>s" or "<SS>s") always appears; its value is zero-padded to two digits when a…
- FMA 推导 actual POST：If the input 'seconds' is None, the function returns the string ''. If 'seconds' is a non-negative numeric value, let s = int(seconds) (truncation toward zero), h = s // 3600, m = (s % 3600) // 60, sec = s % 60. Then the return value is: if h > 0, return f'{h}h {m:02d}m {sec:02d}s'; if h == 0 and m > 0, return f'{m}m {sec:02d}s'; otherwise (h == 0 and m == 0) return f'{sec}s'. The function always returns a string and does not raise exceptions for inputs satisfying the pre-condition.

</details>

#### FMA-MISMATCH-004 — `dashboard-py--_fmt_tokens`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/_fmt_tokens.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/_fmt_tokens.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--_fmt_tokens.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--_fmt_tokens.py)
- 触发/冲突：Passing a float < 1000 (e.g., 0.5) to _fmt_tokens returns '0.5' via str(n), but the spec requires the integer representation '0'.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- n is either None or a non-negative numeric value.
- FMA SPEC post-condition：- When n is None, returns "" (U+2014 em dash). - When n is a non-negative numeric value, returns a compact human-readable string representation formatted as follows: * n 1,000,000 value divided by 10, formatted to two decimal places, suffixed with "M". * 1,000 n < 1,000,000 value divided by 10, formatted to one decimal place, suffixed with "K". * n < 1,000 decimal string representation of the integer value of n, with no suffix. - The returned string is minimal in length for its magnitude category; the original value can be approximately recovered by multiplying the numeric prefix by the magnitude implied by the suffix (10 for "K", 10 for "M").
- FMA 推导 actual POST：If n is None, the function returns the string "". If n is a non-negative number, then: if n >= 1,000,000, returns f"{n/1_000_000:.2f}M"; if 1,000 <= n < 1,000,000, returns f"{n/1_000:.1f}K"; if n < 1,000, returns str(n). Formally, let r be the return value. (n = None r = "") (n None n 1000000 r = format(n/1000000, ".2f") + "M") (n None 1000 n < 1000000 r = format(n/1000, ".1f") + "K") (n None 0 n < 1000 r = str(n)).

</details>

#### FMA-MISMATCH-005 — `dashboard-py--_llm_status_style`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/_llm_status_style.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/_llm_status_style.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--_llm_status_style.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--_llm_status_style.py)
- 触发/冲突：code=None and status='completed' returns ('red', 'completed') instead of ('green', '200') because only 'success' and 'mismatch' are treated as completion statuses.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- code is an integer, string, or None, representing an HTTP-style status code from a trace event - status is a string or None, representing the "status" field of a trace event
- FMA SPEC post-condition：- Returns a pair (color, label) where color is a Rich-compatible color name and label is a display string. - The label is constructed by selecting the first truthy value from code, status, and the string "?" in that priority order, converted to a string. - When the label is "200" or status is a completion-type status (indicating the operation finished), the pair is ("green", "200"). - When status is a format-error type or the label begins with "4" or equals "FMT", the pair is ("yellow", label). - For all other code/status combinations, the pair is ("red", label).
- FMA 推导 actual POST：Let t = str(code) if code else (str(status) if status else "?"). Then the function returns: ("green", "200") if t == "200" or status in ("success", "mismatch"); else ("yellow", t) if status == "format_error" or t.startswith('4') or t == "FMT"; else ("red", t). Formally, for the return value r: ( (t = "200" status {"success", "mismatch"}) r = ("green", "200") ) ( ((t = "200" status {"success", "mismatch"}) (status = "format_error" t starts with "4" t = "FMT")) r = ("yellow", t) ) ( ((t = "200" status {"success", "mismatch"}) (status = "format_error" t starts with "4" t = "FMT")) r = ("red", t) ).

</details>

#### FMA-MISMATCH-006 — `dashboard-py--_locate_workdir`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/_locate_workdir.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/_locate_workdir.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--_locate_workdir.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--_locate_workdir.py)
- 触发/冲突：_locate_workdir checks for a trace/ subdirectory with is_dir(), but the spec requires detecting trace output data generically (e.g. a trace file); when trace exists as a file the function incorrectly appends fm_agent.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a value convertible to a pathlib.Path, referencing a directory that exists on the filesystem
- FMA SPEC post-condition：- Returns a Path to the fm_agent workspace directory to monitor for the given project directory - When the resolved absolute path of proj_dir is itself an fm_agent workspace (identified by the presence of trace output data within that directory), returns that resolved path verbatim - Otherwise, returns the resolved absolute path of proj_dir with "fm_agent" appended as a child path component - The caller is responsible for verifying that the returned path exists or for creating any missing parent directories
- FMA 推导 actual POST：The function returns a pathlib.Path object. Let p = Path(proj_dir).resolve(). If (p / 'trace') is an existing directory, the return value is p; otherwise, it is p / 'fm_agent'. The returned path is absolute.

</details>

#### FMA-MISMATCH-007 — `dashboard-py--_parse_iso`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/_parse_iso.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/_parse_iso.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--_parse_iso.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--_parse_iso.py)
- 触发/冲突：Input '2023-10-01T12:00:00' (valid ISO 8601 without timezone) returns a naive datetime (tzinfo=None), but the spec requires timezone-aware datetime on all successful parses.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- ts is a string or a falsy value (None, empty string).
- FMA SPEC post-condition：- Returns None when ts is falsy. - When ts is a non-empty string, attempts to interpret it as an ISO 8601 timestamp. A trailing "Z" (UTC designator) is accepted and treated equivalently to "+00:00". - On successful parse, returns a timezone-aware datetime object whose components (year, month, day, hour, minute, second, microsecond, UTC offset) match the values expressed in ts according to ISO 8601 rules. - Returns None when ts cannot be parsed as an ISO 8601 timestamp (malformed format, invalid date/time values, etc.).
- FMA 推导 actual POST：If the input 'ts' is falsy (i.e., evaluates to False in a boolean context), the function returns None. Otherwise, 'ts' is a non-empty string. Define t = (ts[:-1] + '+00:00') if ts ends with 'Z' else ts. The function attempts to call datetime.fromisoformat(t). If that call succeeds, the return value is the resulting datetime.datetime object; if any Exception is raised, the return value is None. No non-local state is modified. Formal post-condition: let R be the return value. R = None if (not ts) or (isinstance(ts, str) and datetime.fromisoformat(t) raises an Exception), else R = datetime.fromisoformat(t), where t = (ts[:-1] + '+00:00') if (isinstance(ts, str) and ts.endswith('Z')) else ts. All other program state is unchanged.

</details>

#### FMA-MISMATCH-008 — `dashboard-py--_price_for`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/_price_for.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/_price_for.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--_price_for.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--_price_for.py)
- 触发/冲突：When _MODEL_COST holds a non-dict value (e.g., float 0.03) for a model key, _price_for returns that non-dict value instead of None or a dict, violating the spec's dict/None return type guarantee.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- model is a string, or None / a falsy value
- FMA SPEC post-condition：- Returns a dict whose keys are per-token pricing component names and whose values are positive float per-token costs in USD for the model identified by model, or None when no pricing data is available - A model identifier that contains a "/" character (provider-prefixed form such as "provider/model") is recognized under both its full provider-prefixed form and its bare form (the substring following the first "/"); a match in either form is sufficient - Returns None when model is falsy, or when the model identifier has no matching pricing data in either its full or bare form
- FMA 推导 actual POST：The function returns None if the input model is falsy (e.g., None, empty string). Otherwise, if model is a truthy string and exists as a key in the global _MODEL_COST dictionary, the function returns the corresponding price. If model is not in _MODEL_COST but contains a '/', the substring after the first '/' is extracted; if this substring exists as a key in _MODEL_COST, that price is returned. In all other cases, the function returns None. No modifications are made to the input or the _MODEL_COST mapping. Formally, for return value r: r = None (bool(model)) (bool(model) (model _MODEL_COST) (('/' model) (model.split('/', 1)[1] _MODEL_COST))). r = _MODEL_COST[model] bool(model) model _MODEL_COST. r = _MODEL_COST[model.split('/', 1)[1]] bool(model) mo…

</details>

#### FMA-MISMATCH-009 — `dashboard-py--_push_recent`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/_push_recent.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/_push_recent.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--_push_recent.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--_push_recent.py)
- 触发/冲突：Passing a falsy non-None object with .strftime() as ts causes when_str to be '' instead of the formatted time string, because line 322 uses 'if ts' (truthiness check) instead of 'if ts is not None' (identity check).
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self is an initialized State with a bounded recent_events collection that has a fixed maximum capacity. - ts is a datetime or None. - stage, status, and summary are strings.
- FMA SPEC post-condition：- A 4-tuple (when_str, stage, status, summary) is present at the most recently added position of self.recent_events, where when_str is the "HH:MM:SS"-formatted string of ts if ts is not None, or "" (empty string) if ts is None. - If self.recent_events was at maximum capacity before the call, the chronologically oldest entry is evicted. - Every other entry in self.recent_events retains its relative insertion order (all existing entries shift one position toward the eviction boundary). - self.recent_events does not grow beyond its fixed capacity. - No value other than recent_events of self is modified.
- FMA 推导 actual POST：The recent_events deque now has at its front (index 0) the tuple (when, stage, status, summary), where when is ts.strftime("%H:%M:%S") if ts is not None else "". If the deque was at maximum capacity before the operation, the oldest element (the rightmost) has been removed; otherwise its size has increased by one. All other attributes of self remain unchanged. Formally, let L be the previous length of recent_events and M be its fixed maximum capacity. Then len(recent_events) = min(L+1, M). recent_events[0] = (when, stage, status, summary). For 1 <= i < min(L+1, M), recent_events[i] = old recent_events[i-1]. All other parts of self's state are preserved.

</details>

#### FMA-MISMATCH-010 — `dashboard-py--_strip_star`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/_strip_star.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/_strip_star.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--_strip_star.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--_strip_star.py)
- 触发/冲突：Passing a dict with a non-string key (e.g. integer 42) to _strip_star raises AttributeError because k.startswith('*') is called directly on the key, while the spec requires using str(k).startswith('*').
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- d may be any value; the function gracefully handles non-dict inputs.
- FMA SPEC post-condition：- If d is a dict, returns a new dict with the same key-value pairs as d, except that every key whose string representation starts with "*" has that leading "*" character stripped from the key. Keys that do not start with "*" are unchanged. - Every value in the returned dict is the identical object reference as the corresponding value in d (values are not copied or transformed). - The input dict d is not mutated. - If d is not a dict, returns d unchanged.
- FMA 推导 actual POST：If the input d is not a dictionary, the function returns d unchanged. If d is a dictionary, the function returns a new dictionary with the same number of key-value pairs, preserving insertion order, where each key k that starts with the character '*' is replaced by k[1:] (i.e., removing the single leading '*'), and all other keys remain unchanged; all values remain the same. Formally: result = d if not isinstance(d, dict) else { (k[1:] if k.startswith('*') else k) : v for k, v in d.items() }.

</details>

#### FMA-MISMATCH-011 — `dashboard-py--bar_line`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/bar_line.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/bar_line.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--bar_line.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--bar_line.py)
- 触发/冲突：When cache_read > total_input (rate > 1), filled = int(20*rate) exceeds 20, making the bar longer than the specified 20 characters.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- label is a non-empty string. - rows is an iterable of (cache_read, total_input) numeric pairs where cache_read and total_input are non-negative.
- FMA SPEC post-condition：- When the total input tokens aggregated across rows is zero, returns a Rich markup string indicating no data for the given label. - Otherwise, returns a Rich markup string containing: * The label left-aligned to a fixed width. * The cache-hit rate expressed as a percentage with one decimal place, rendered in bold with a color determined by the rate: green when 80%, yellow when 50%, and red otherwise. * A 20-character horizontal bar whose filled portion is proportional to the hit rate (rendered with the same color as the percentage), followed by the formatted cache-read and total-input token counts separated by " / " in dim style.
- FMA 推导 actual POST：The function returns a string and has no side effects on the inputs. Let n be the number of pairs in rows, and for each i=1..n let a_i = cache_read_i 0, b_i = total_input_i 0. Define cr = a_i, tot = b_i. If tot = 0 the function returns "[dim]" + label left-justified to width 14 + "(no data)[/]". Otherwise, let rate = cr / tot, pct = 100 * rate, filled = 20 * rate, bar = "" repeated filled times + "" repeated (20filled) times, color = "green" if pct 80 else ("yellow" if pct 50 else "red"). The function returns f"{label:<10}[bold {color}]{pct:5.1f}%[/] [{color}]{bar}[/] [dim]{_fmt_tokens(cr)} / {_fmt_tokens(tot)}[/]" where _fmt_tokens gives a humanreadable abbreviation. Precondition guarantees label is a nonempty string, so label alignment never fails.

</details>

#### FMA-MISMATCH-012 — `dashboard-py--build_layout`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/build_layout.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/build_layout.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--build_layout.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--build_layout.py)
- 触发/冲突：Header size is hardcoded to 3; if render_header produces >3 rows the content is clipped instead of the height being computed from data rows.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- state is a State instance whose aggregated fields (stage counts, token totals, cache statistics, LLM status history, recent events, bug validation counts) reflect the latest ingested trace data
- FMA SPEC post-condition：- Returns a Rich Layout renderable that, when rendered to a terminal, produces a full-screen dashboard partitioned into vertically stacked regions: header, top, mid, and footer - The header region contains run identification information derived from state - The top region is horizontally split into a pipeline stage progress panel (ratio 3) and a right column containing a prompt-cache panel (ratio 2) stacked above a bug-validation summary panel (ratio 1) - The mid region is horizontally split into a token-usage statistics panel (ratio 3) and an LLM call status panel (ratio 2) - The footer region displays the most recent trace events in chronological order - Every panel's rendered content reflects the data in state at the moment of the call - Region h…
- FMA 推导 actual POST：Natural language: The function returns a Rich `Layout` object that represents a dashboard with a specific vertical and horizontal split structure. The root layout is split into four vertical panes: 'header' (fixed height 3, containing the dashboard title and project identification rendered from `state`), 'top' (height equal to the number of pipeline stages plus 6), 'mid' (height 9), and 'footer' (fills remaining space, containing a recent event log). The 'top' pane is split horizontally into 'stages' (ratio 3, rendering stage status tallies) and 'top_right' (ratio 2), which is itself split vertically into 'cache' (ratio 2, rendering prompt-cache statistics) and 'bugs' (ratio 1, rendering bug validation counts). The 'mid' pane is split horizontally i…

</details>

#### FMA-MISMATCH-013 — `dashboard-py--elapsed`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/elapsed.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/elapsed.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--elapsed.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--elapsed.py)
- 触发/冲突：Deleting the last_event_time attribute from a State instance and calling elapsed() raises AttributeError because line 508 accesses self.last_event_time directly without guarding against attribute absence.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self.first_event_time is either None or a timezone-aware datetime representing when the earliest recorded event occurred - self.last_event_time is either None or a timezone-aware datetime representing when the most recent recorded event occurred
- FMA SPEC post-condition：- Returns None when self.first_event_time is None (no events have been recorded yet) - Otherwise returns the elapsed wall-clock duration between self.first_event_time and the endpoint timestamp, expressed as a possibly-fractional number of seconds - The endpoint timestamp is self.last_event_time when self.last_event_time is truthy; when self.last_event_time is falsy (None or absent), the current UTC wall-clock instant is used as the endpoint instead
- FMA 推导 actual POST：If `self.first_event_time` is None, the method returns None with no side effects. Otherwise, let `end` be `self.last_event_time` if it is not None, else the result of `datetime.now(timezone.utc)` evaluated at the time of the call. Then the method returns `(end - self.first_event_time).total_seconds()`, a float representing the duration in seconds between `self.first_event_time` and `end`. No side effects on the object state.

</details>

#### FMA-MISMATCH-014 — `dashboard-py--main`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/main.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/main.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--main.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--main.py)
- 触发/冲突：When --refresh is set to a value greater than 1.0, time.sleep(args.refresh) sleeps for more than 1 second, violating the spec requirement that refresh rate be no slower than once per second.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- sys.argv contains at minimum one argument: a filesystem path to either a project directory (with an fm_agent/ subdirectory) or a workspace directory (with a trace/ subdirectory). - sys.argv may contain an optional --refresh flag followed by a float value greater than zero.
- FMA SPEC post-condition：- If the trace directory expected under the project directory does not exist, a diagnostic message and a waiting hint are written to stderr; execution continues regardless. - Enters an infinite loop. On each iteration: - The dashboard state is refreshed with the latest trace events, OpenCode trace data, and bug validation results from the filesystem. - A full-screen terminal UI is rendered showing the current aggregated dashboard state, refreshed at a rate no slower than once per second and no faster than the configured refresh interval. - The loop sleeps for the configured refresh interval (default 1.5 seconds) after each render. - On KeyboardInterrupt, the loop terminates and the function returns without propagating the exception.
- FMA 推导 actual POST：If the function returns normally (i.e., after catching a KeyboardInterrupt while in the infinite update loop), then the `Live` context manager has exited, the terminal has been restored to its original state, and the program ends with an implicit success code. The `State` object `state` reflects the events, trace, and bug data that were read from the project directory up to the end of the last *fully completed* iteration of the loop. Any iteration that was in progress when the interrupt was raised is partially applied: some of `tail_events`, `tail_opencode`, `scan_bugs` may have completed, but `live.update` might not have been called with the final layout, or `time.sleep` might not have finished. The live display showed the layout that was last gene…

</details>

#### FMA-MISMATCH-015 — `dashboard-py--render_cache`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/render_cache.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/render_cache.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--render_cache.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--render_cache.py)
- 触发/冲突：When state.cache_window sums differ from accumulated state.totals (e.g., after >200 events truncate the deque), the overall bar uses the wrong data source (totals instead of cache_window aggregate), producing a different hit rate.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- state is a State instance whose token-total fields (totals, opencode_token_totals) contain numeric values keyed by category strings - state.cache_window is a sequence of (cache_read, total_input) numeric pairs representing recent trace data - state.model_seen is a string or None - state.cost_native and state.opencode_cost are numeric values
- FMA SPEC post-condition：- Returns a Panel renderable titled "Cache Coverage" with a green border - The panel body displays cache hit-rate bars for three aggregation windows: the most recent 10 entries of state.cache_window, the most recent 100 entries, and the aggregate of all entries in state.cache_window - Each bar renders a percentage value, a filled-bar visual of width 20 characters, and the token counts in the form "cache_read / total_input" - The bar color is green when the hit rate is at least 80%, yellow when at least 50%, and red when the hit rate is below 50% - A window whose total_input is zero produces "(no data)" in place of bar content for that window - When the combined total of cache_read and input tokens across all data sources is zero, the panel body disp…
- FMA 推导 actual POST：After execution, the function returns a Panel object; state is unmodified. The Panel has title "Cache Coverage" and border style "green". Its renderable is an Align(center, vertical="middle") containing a Text object. If the sum of all cache_read, input, and cache_write tokens from both totals and opencode_token_totals is zero, the Text markup is "[dim](no token data yet)[/]". Otherwise, the Text contains three bar-line strings (latest 10, latest 100, overall) summarizing cache hit rates, a visual bar, and formatted token counts, computed from state.cache_window and the aggregated totals. If pricing data exists for the model (state.model_seen), input_cost_per_token > 0, and total cache_read > 0, an additional line showing estimated cost savings and…

</details>

#### FMA-MISMATCH-016 — `dashboard-py--render_header`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/render_header.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/render_header.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--render_header.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--render_header.py)
- 触发/冲突：Calling render_header() with a state object that lacks the model_seen attribute causes AttributeError; the spec requires returning '?' in that case.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- state is a State instance with state.workdir, state.model_seen, and state.elapsed() populated
- FMA SPEC post-condition：- Returns a Panel renderable with a cyan border containing a single line of metadata as its body - The body line contains four items separated by bullet characters, in order: the literal text "FM-Agent Dashboard", the working directory from state.workdir, the model identifier from state.model_seen (or "?" when model_seen is falsy or absent), and the formatted elapsed duration derived from state.elapsed() - All items after the dashboard title are styled dimmed relative to the title
- FMA 推导 actual POST：The function returns a rich Panel object representing a header with the state's workdir, model_seen (or '?' if None), and formatted elapsed time. The state object is unchanged. Formal logic: result = Panel(Text.from_markup(' '.join([...]))) attr {workdir, model_seen, elapsed}: state.attr = old(state.attr).

</details>

#### FMA-MISMATCH-017 — `dashboard-py--render_llm_status`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/render_llm_status.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/render_llm_status.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--render_llm_status.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--render_llm_status.py)
- 触发/冲突：The strip loop uses statuses[-50:] instead of iterating all window entries, so when LLM_STATUS_WINDOW (80) exceeds 50, not all entries are represented.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- state.llm_statuses is an iterable where each element supports .get("code"), .get("status"), .get("time"), .get("source"), and .get("label") - Each element's "code" is an integer HTTP status code and "status" is a string label
- FMA SPEC post-condition：- Returns a Rich Panel renderable titled "LLM Calls" with a cyan border style - When state.llm_statuses yields no items: the panel body contains a vertically centered, dimmed "(no LLM calls yet)" message - When state.llm_statuses yields one or more items: - The panel body opens with a summary line reporting the count of status entries considered (capped at LLM_STATUS_WINDOW) and the percentage of entries whose code maps to a 200-class label, color-coded green when the percentage is 95% or above, yellow when it is 80% or above but below 95%, and red when it is below 80% - Below the summary, a single-line strip of colored block characters represents the most recent status entries, with each character's color determined by the entry's code and status v…
- FMA 推导 actual POST：The function returns a Rich Panel object `result` with `result.title == 'LLM Calls'` and `result.border_style == 'cyan'`. Let `statuses = list(state.llm_statuses)[-LLM_STATUS_WINDOW:]`. If `len(statuses) == 0`, then `result.renderable` is an `Align.center` containing a `Text` with markup `'[dim](no LLM calls yet)[/]'` and `vertical='middle'`. Otherwise, `result.renderable` is a `Table.grid` with `expand=True`, containing two rows. The first row is a `Text` object consisting of: (a) a strip of symbols for the last `min(len(statuses), 50)` items, where for each item the symbol is `''` if `_llm_status_style(item['code'], item['status'])[1] == '200'`, else `''` if the returned color is `'yellow'`, else `''`, each appended with the corresponding style co…

</details>

#### FMA-MISMATCH-018 — `dashboard-py--render_recent`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/render_recent.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/render_recent.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--render_recent.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--render_recent.py)
- 触发/冲突：Rich markup in data values (time, stage, summary) is parsed by Rich instead of being escaped, allowing inline markup to override column-level styles — e.g., [red] markup in time field renders red instead of required dimmed.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- state.recent_events is an iterable yielding 4-element tuples of the form (time: str, stage: str, status: str, summary: str)
- FMA SPEC post-condition：- Returns a Rich Panel renderable titled "Recent Events" with a cyan border style - The panel body is a table with four columns: time (dimmed style), stage (cyan style), status (color-coded), and summary (ellipsized if content exceeds column width) - Each row corresponds to one tuple from state.recent_events in the iteration order of that collection - The status column renders each status value in a color determined by its string: "success" green, "mismatch" yellow, "error" red, "format_error" magenta, and any unrecognized status string white - The returned renderable performs no I/O and is suitable for composition into a terminal layout
- FMA 推导 actual POST：If the function returns normally, it returns a Panel object with title 'Recent Events', border_style 'cyan', and content being a Table whose columns are 'time', 'stage', 'status', 'summary' with specified styles; the table rows are exactly those obtained by iterating over list(state.recent_events) in order, where for each event (time, stage, status, summary) a row is added containing time, stage, a Rich-markup coloured status string '[color]status[/]' with color determined by the mapping {success: green, mismatch: yellow, error: red, format_error: magenta, default: white}, and summary. If an exception (e.g., NameError for undefined Table or Panel, TypeError from misbehaving state.recent_events, etc.) occurs during execution, the exception propagates…

</details>

#### FMA-MISMATCH-019 — `dashboard-py--render_stages`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/render_stages.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/render_stages.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--render_stages.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--render_stages.py)
- 触发/冲突：Setting a non-integer float (5.5) in state.stage_counts causes str() to render the raw float string instead of an integer representation.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- state is a State instance whose stage_counts attribute is a dict-like mapping from stage name strings to dicts that map verdict category keys ("success", "mismatch", "error", "format_error") to non-negative integer counts - STAGES is an iterable of stage name strings providing the display order; every element of STAGES is a key in stage_counts or defaults to zero for all verdict categories
- FMA SPEC post-condition：- Returns a Rich Panel renderable whose title is "Stages" and whose border is styled cyan - The panel contains a table with one row for each stage name in STAGES, in iteration order, and no other rows - For each stage, the row displays four non-negative integer counts derived from state.stage_counts: the number of successful verifications (key "success"), mismatches (key "mismatch"), errors (key "error"), and format errors (key "format_error") - When a stage name is absent from state.stage_counts, every verdict count for that stage is rendered as zero
- FMA 推导 actual POST：The function returns a rich Panel object r with title 'Stages' and border_style 'cyan'. The renderable of r is a Table t with header row ['Stage', '', ' mismatch', ' error', 'fmt']. For each stage string st in the iterable STAGES, t contains a row consisting of the elements: st, str(c_s), str(c_m), str(c_e), str(c_f), where counts = state.stage_counts.get(st, {}) and c_s = counts.get('success', 0), c_m = counts.get('mismatch', 0), c_e = counts.get('error', 0), c_f = counts.get('format_error', 0). The stage_counts attribute of state is not modified.

</details>

#### FMA-MISMATCH-020 — `dashboard-py--scan_bugs`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/scan_bugs.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/scan_bugs.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--scan_bugs.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--scan_bugs.py)
- 触发/冲突：When bug_dir is missing, bugs_pending is not reset to 0; invalid/unreadable JSON files are silently skipped instead of being counted as bugs_not_confirmed.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self.bug_dir is a Path object pointing to a directory that may contain *.result.json files. - self.stage_counts is a dict mapping stage name strings to dicts whose values are integers representing operation counts per status.
- FMA SPEC post-condition：- self.bugs_confirmed equals the number of *.result.json files in self.bug_dir whose parsed "confirmation_status" field, after lowercasing, contains the substring "confirm". - self.bugs_not_confirmed equals the number of remaining *.result.json files in self.bug_dir those whose parsed "confirmation_status" field, after lowercasing, does NOT contain "confirm", including files where the field is absent, the file cannot be read, or the content is not valid JSON. - self.bugs_pending equals max(0, C - (self.bugs_confirmed + self.bugs_not_confirmed)), where C is the sum of all integer values under self.stage_counts["bug_validation"], or 0 if the key "bug_validation" is absent from self.stage_counts. - If self.bug_dir does not exist, self.bugs_confirmed, s…
- FMA 推导 actual POST：If self.bug_dir does not exist at the start of the method, then self.bugs_confirmed = 0, self.bugs_not_confirmed = 0, and self.bugs_pending remains unchanged. Otherwise, let F be the set of paths in self.bug_dir.glob('*.result.json') for which open and json.load succeed without raising an Exception. For each f in F, let S(f) = (json.load(f).get('confirmation_status') or '').lower(). Define C = { f in F | 'confirm' in S(f) and 'not' not in S(f) }. Then self.bugs_confirmed = |C|, self.bugs_not_confirmed = |F \ C|, and self.bugs_pending = max(0, sum(self.stage_counts.get('bug_validation', {}).values()) - (self.bugs_confirmed + self.bugs_not_confirmed)). No other attributes are modified.

</details>

#### FMA-MISMATCH-021 — `dashboard-py--tail_events`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/tail_events.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/tail_events.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--tail_events.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--tail_events.py)
- 触发/冲突：When _ingest_event raises an exception during tail_events, the loop exits before processing remaining lines and _events_offset is never updated, violating spec guarantees.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self.events_path is a Path object pointing to a JSONL file where each non-blank line is a valid JSON object. - self._events_offset is a non-negative integer tracking the byte position up to which the file has already been processed by previous calls.
- FMA SPEC post-condition：- Every non-blank line in self.events_path that was written after the byte position recorded in self._events_offset at call time is parsed as a JSON object and passed to self._ingest_event. - Lines that are blank or cannot be parsed as valid JSON are silently skipped and do not prevent processing of subsequent lines. - self._events_offset is updated to the file's end byte position after all newly written lines have been read. - If self.events_path does not exist, the function returns immediately and no state is modified. - If the file's current byte size is smaller than self._events_offset (indicating truncation or rotation), self._events_offset is reset to 0 before reading, causing the entire file to be reprocessed. - If the file's current byte siz…
- FMA 推导 actual POST：Natural language post-condition: If the method exits normally (no uncaught exception): - If `self.events_path` does not exist, `self._events_offset` is unchanged. - Otherwise, let `old_offset` be the value of `self._events_offset` before the call and `sz` be `self.events_path.stat().st_size` at the start of the call. - If `sz < old_offset`, then `self._events_offset` is set to 0. - If `sz == old_offset`, then `self._events_offset` remains `old_offset`. - If `sz > old_offset`, the method reads all lines from byte `old_offset` to the current end of file. For each line that is non-blank and parses successfully as JSON, `self._ingest_event` is called with the parsed object; blank lines or lines causing a JSON parse error are silently skipped. After proc…

</details>

#### FMA-MISMATCH-022 — `dashboard-py--tail_opencode`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/tail_opencode.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/tail_opencode.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--tail_opencode.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--tail_opencode.py)
- 触发/冲突：open() on .jsonl files is not guarded by try/except; when open() fails (e.g. permission denied), the exception propagates and all subsequent files are skipped, violating the spec's requirement that all files be visited.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self is an initialized State with a project directory. - self.opencode_dir is a pathlib.Path that may or may not exist. - self._opencode_offsets is a dict mapping filenames to integer byte offsets.
- FMA SPEC post-condition：- If self.opencode_dir does not exist, returns immediately with no side effects. - All files ending in ".jsonl" in self.opencode_dir are visited in ascending lexicographic order of filename. - For each such file: any content appended since the previous call to tail_opencode is consumed; if no previous offset was recorded for the file, all content is consumed. - If a file has fewer bytes than its previously recorded offset (indicating truncation or rotation), the offset is silently reset to zero before reading. - If a file has no new content since the last recorded offset, it is skipped. - Every non-empty line in the new content that decodes as a valid JSON object is ingested by the State; lines that fail JSON decoding are silently skipped. - After p…
- FMA 推导 actual POST：Natural language: If self.opencode_dir does not exist, the method returns immediately and the State is unchanged. Otherwise, it processes each JSONL file in the directory in alphabetical order. For each file, if os.stat fails (OSError), the file is skipped entirely with no change to its offset. If the files size is less than the stored offset, the offset is reset to 0. If after any reset the size equals the offset, the file is skipped and no records are ingested. Otherwise, the file is opened at the determined offset, every non-empty line is attempted to be parsed as JSON; successful parses are passed to self._ingest_opencode, which updates the States aggregated metrics, while lines that fail parsing are ignored. After processing all lines, the offs…

</details>

#### FMA-MISMATCH-216 — `dashboard-py--_ingest_opencode`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/_ingest_opencode.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/_ingest_opencode.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--_ingest_opencode.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--_ingest_opencode.py)
- 触发/冲突：Response with status 200 and valid usage dict was claimed to be ignored, but 3 probe variants all confirmed the code correctly updates opencode_calls, token totals, cost, and cache_window.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- rec is a dict parsed from a single JSONL line of an OpenCode trace file. It contains at minimum the key "_kind" (string) and may contain "_id" (call identifier), "_ts" (ISO 8601 timestamp), "_trace_file" (string), "model" (string), "usage" (dict), and response status fields. - trace_file is an optional string identifying the source trace file; may be None when the record embeds "_trace_file". - self is an initiali…
- FMA SPEC post-condition：- Records with "_kind" == "request" AND a non-None "_id": the request metadata (timestamp, model, URL, purpose) is stored internally keyed by (trace_file, call_id). No user-visible aggregated metric changes. - Records with "_kind" == "error": an error entry is appended to the LLM-status history. No token or cost totals change. - Records with "_kind" != "response": no side effects beyond the request and error handling described above. - Records with "_kind" == "response": * If the HTTP status code (from any of "_status", "status", "status_code") is present and not 200, an error entry is appended to the LLM-status history. No token or cost totals change. * If "usage" is not a dict (missing or non-dict value), a success entry is appended to the LLM-sta…
- FMA 推导 actual POST：After completing execution of _ingest_opencode, the state of self is transformed as follows: Case 1: rec._kind is "request" and rec._id is not None. - self._opencode_requests is updated: for fresh_key = (trace_key, call_id) where trace_key = rec.get("_trace_file") or trace_file, and call_id = rec["_id"], the entry self._opencode_requests[fresh_key] is set to a dict with keys "ts" (datetime or None, parsed from rec._ts), "model" (value of rec.model, or None), "url" (value of rec._url, or None), and "purpose" (value of rec._purpose, or None). - All other attributes of self (opencode_calls, opencode_token_totals, opencode_cost, cache_window, LLM-status history, and _opencode_requests entries for other keys) remain unchanged. Case 2: rec._kind is "error…

</details>

#### FMA-MISMATCH-217 — `dashboard-py--_push_llm_status`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/_push_llm_status.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/_push_llm_status.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--_push_llm_status.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--_push_llm_status.py)
- 触发/冲突：_push_llm_status allegedly fails to evict oldest entry when deque exceeds capacity, but Python's deque(maxlen=N) append() automatically enforces the limit.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- ts is a datetime or None. - source, label, status, model, code, and detail are strings or None. - self.llm_statuses is a mutable sequence that supports appending and evicts the oldest entry when at a fixed maximum capacity.
- FMA SPEC post-condition：- A new record is appended to self.llm_statuses. - The record contains the following fields: * "time": "HH:MM:SS" string formatted from ts when ts is truthy; empty string when ts is falsy. * "source": the given source value. * "label": the given label value, defaulting to "llm_call" when label is falsy. * "status": the given status value, defaulting to "?" when status is falsy. * "model": the given model value. * "code": the given code value, defaulting to the status value when code is falsy; if status is also falsy, defaults to "?". * "detail": the given detail value. - self.llm_statuses never exceeds a fixed maximum length; when the append would exceed the maximum, the oldest entry is evicted.
- FMA 推导 actual POST：After the method executes, no exception is raised. The sequence `self.llm_statuses` has been updated to contain a new dictionary as its last element, with fields assembled from the parameters. Let `old` be the value of `self.llm_statuses` immediately before the call, `new` be its value after the call, and `capacity` the fixed maximum length of the sequence (the eviction threshold). The new dictionary `entry` is defined as: `entry = { "time": ts.strftime("%H:%M:%S") if ts is not None else "", "source": source, "label": label if label else "llm_call", "status": status if status else "?", "model": model, "code": code if code else (status if status else "?"), "detail": detail }` Post-conditions on the sequence: - If `len(old) < capacity`: `new == old +…

</details>

#### FMA-MISMATCH-218 — `dashboard-py--render_tokens`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/dashboard-py/render_tokens.py) · [推导 POST / result](../fm_agent/logic_verification_results/dashboard-py/render_tokens.json) · [具体 bug 报告](../fm_agent/bug_validation/dashboard-py--render_tokens.md) · [probe](../fm_agent/bug_validation/probe_dashboard-py--render_tokens.py)
- 触发/冲突：When state.model_seen is None (falsy), _price_for receives empty string but handles it gracefully via guard clause; the function still returns a valid Panel.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- state is a State instance - state.totals is a dict-like mapping token-category keys ("input", "cache_read", "cache_write", "output") to non-negative integer counts representing verification-phase token consumption - state.opencode_token_totals is a dict-like mapping the same four token-category keys to non-negative integer counts representing OpenCode token consumption - state.model_seen is a string identifying th…
- FMA SPEC post-condition：- Returns a Rich Panel renderable whose title is "Tokens & Cost" and whose border is styled green - The panel contains a table with exactly three data rows: one for verification tokens, one for OpenCode tokens, and one for the combined totals across both sources - Each data row displays five values: the token count classified as new input ("input"), the count of tokens served from the prompt cache ("cache_read"), the count of tokens written to the prompt cache ("cache_write"), the output token count ("output"), and a monetary cost formatted as currency - The OpenCode row label includes the value of state.opencode_calls to indicate the number of invocations comprising the totals - The combined-total row's token values are the element-wise sum of the…
- FMA 推导 actual POST：The state object is unchanged: state.totals, state.opencode_token_totals, state.model_seen, state.cost_native, state.opencode_cost, and state.opencode_calls retain the exact same values and types as before the call. The return value is an instance of rich.panel.Panel with title='Tokens & Cost', border_style='green', and its renderable is a rich.table.Table containing the following rows: a header row [Source, in:new, in:read, in:write, output, cost]; a row labeled 'verification' with token counts from state.totals and cost from state.cost_native; a row labeled 'opencode (<state.opencode_calls>)' with token counts from state.opencode_token_totals and cost from state.opencode_cost; a total row summing both token categories and both costs, displaying a…

</details>

### `main-py`

#### FMA-MISMATCH-023 — `main-py--_clean_previous_run`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/main-py/_clean_previous_run.py) · [推导 POST / result](../fm_agent/logic_verification_results/main-py/_clean_previous_run.json) · [具体 bug 报告](../fm_agent/bug_validation/main-py--_clean_previous_run.md) · [probe](../fm_agent/bug_validation/probe_main-py--_clean_previous_run.py)
- 触发/冲突：When work_dir is a symbolic link to a directory, os.path.isdir returns True but shutil.rmtree raises OSError, violating the specification that requires the directory to be removed without error.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- work_dir is a string representing a filesystem path.
- FMA SPEC post-condition：- If work_dir refers to an existing directory in the filesystem, that directory and all of its contents (files and subdirectories, recursively) are permanently removed. - If work_dir does not refer to an existing directory, no action is taken and the function returns without error. - No other filesystem paths outside of work_dir are affected.
- FMA 推导 actual POST：After the function call: - If no exception occurs: - If `os.path.isdir(work_dir)` held before the call, then `work_dir` no longer exists (`os.path.exists(work_dir)` is False). - If `work_dir` was not a directory before the call, the existence status of the path remains unchanged from the precall state. - If an exception is raised during removal (e.g., by `shutil.rmtree`), the directory may be left in an inconsistent or partially removed state (no guarantee about its existence). Formally (assuming normal return): ( old(os.path.isdir(work_dir)) os.path.exists(work_dir) ) ( old(os.path.isdir(work_dir)) ( os.path.exists(work_dir) old(os.path.exists(work_dir)) ) ). No explicit return value is produced (returns `None`).

</details>

#### FMA-MISMATCH-024 — `main-py--_normalize_submodules`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/main-py/_normalize_submodules.py) · [推导 POST / result](../fm_agent/logic_verification_results/main-py/_normalize_submodules.json) · [具体 bug 报告](../fm_agent/bug_validation/main-py--_normalize_submodules.md) · [probe](../fm_agent/bug_validation/probe_main-py--_normalize_submodules.py)
- 触发/冲突：os.path.commonpath performs lexical comparison, incorrectly rejecting submodules whose resolved paths are inside proj_dir but have different lexical prefixes (e.g. via symlinks or case-differing paths on case-insensitive filesystems)
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string representing an existing project root directory path - submodules is None, an empty iterable, or an iterable of strings, each a relative or absolute path
- FMA SPEC post-condition：- Returns a list of project-relative directory paths using "/" as the path separator, regardless of platform - Each returned path is a valid existing subdirectory strictly inside proj_dir (not proj_dir itself) - No returned path is a descendant of any other returned path: the result is a minimal covering set of the input submodules - The list contains no duplicate entries - The list is ordered by increasing path depth (number of "/" characters), with paths of equal depth ordered lexicographically - If submodules is None or contains only empty/whitespace-only strings, returns an empty list - Raises ValueError if any input path resolves outside proj_dir - Raises ValueError if any input path resolves to proj_dir itself - Raises ValueError if any input…
- FMA 推导 actual POST：If submodules is falsy (None or empty), the function returns an empty list without raising exceptions. Otherwise, for each nonempty string `raw` in submodules: if its absolute path resides under proj_dir (not equal to proj_dir) and names an existing directory, its relative path with forward slashes is collected; otherwise a ValueError is raised (message indicates invalid submodule). If os.path.isdir raises OSError, that OSError propagates. After processing all entries, the collected relative paths are sorted primarily by increasing directory depth (number of '/') and secondarily lexicographically. From the sorted list, any path whose directory hierarchy has a prefix already in the result is omitted. The final sorted list of minimal, distinct relativ…

</details>

#### FMA-MISMATCH-025 — `main-py--run_pipeline`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/main-py/run_pipeline.py) · [推导 POST / result](../fm_agent/logic_verification_results/main-py/run_pipeline.json) · [具体 bug 报告](../fm_agent/bug_validation/main-py--run_pipeline.md) · [probe](../fm_agent/bug_validation/probe_main-py--run_pipeline.py)
- 触发/冲突：run_pipeline calls sys.exit(1) when proj_dir contains no supported source files instead of returning early as the spec requires for empty file_list.
- 成因复核：SPEC 自相矛盾：Pre-condition 明说无源文件时 sys.exit(1)，Post-condition 又要求 empty file_list 正常返回；实现符合前者，checker 只使用了后者。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a non-None string; if it does not reference an existing directory, the function prints a diagnostic and calls sys.exit(1) - If proj_dir is a directory but contains no files with an extension recognized by the pipeline, the function prints a diagnostic and calls sys.exit(1) - resume is a truthy/falsy value; when truthy and fm_agent/ exists under proj_dir, previously completed pipeline work is preserved…
- FMA SPEC post-condition：- On success (normal return): the full pipeline has executed across all source files under proj_dir - If only_spec is truthy: every function in the extracted call graph has a behavioral spec ([SPEC] block) prepended to its extracted-function file; no verification or bug validation runs - If only_spec is falsy: specs are generated, then each specced function has a verification result in fm_agent/logic_verification_results/, and each MISMATCH has a bug validation report in fm_agent/bug_validation/ - The fm_agent/ work directory under proj_dir is created and populated; no file outside fm_agent/ under proj_dir is modified - If resume is truthy and fm_agent/ exists, previously completed stages are not re-executed; if resume is falsy or fm_agent/ is absen…
- FMA 推导 actual POST：One of the following three cases holds after execution of the code block: 1. If os.path.isdir(proj_dir): the message '[Pipeline] ERROR: proj_dir does not exist or is not a directory: ' was printed and sys.exit(1) was called. 2. If os.path.isdir(proj_dir) _has_source_code(proj_dir, submodules): the message '[Pipeline] ERROR: No source code files found in' was printed and sys.exit(1) was called. 3. If os.path.isdir(proj_dir) _has_source_code(proj_dir, submodules): the program reached line 40 and the following state holds: - work_dir = proj_dir + '/fm_agent', - input_dir = work_dir + '/extracted_functions', - output_dir = work_dir + '/logic_verification_results', - script_dir = directory of the pipeline script (os.path.dirname(os.path.abspath(__file__)…

</details>

### `src--call_graph_edges-py`

#### FMA-MISMATCH-026 — `src--call_graph_edges-py--_clean_label`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/call_graph_edges-py/_clean_label.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/call_graph_edges-py/_clean_label.json) · [具体 bug 报告](../fm_agent/bug_validation/src--call_graph_edges-py--_clean_label.md) · [probe](../fm_agent/bug_validation/probe_src--call_graph_edges-py--_clean_label.py)
- 触发/冲突：Input with nested matching quotes (e.g., '"hello"') causes _clean_label to strip only the outermost quotes once, violating idempotence when applied twice.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- None
- FMA SPEC post-condition：- Returns a string - Returns the empty string when the string representation of value has no content beyond whitespace, trailing semicolons, and outermost matching single or double quote characters - Otherwise, returns a string with no leading or trailing whitespace, with trailing semicolons removed, and with outermost matching single or double quote characters removed when present - The transformation is deterministic: the same input always produces the same output - The transformation is idempotent: applying _clean_label to its own output returns the same string - The returned label preserves the path-vs-non-path classification of the input label (i.e., whether the label represents a source-file-qualified function reference or a plain function nam…
- FMA 推导 actual POST：The function returns a string. Let s = str(value).strip(). If s is the empty string, return the empty string. Otherwise, let t = s.rstrip(';').strip(). If len(t) >= 2 and t[0] == t[-1] and t[0] is in {'\'', '"'} (either a single or double quote), then return t[1:-1].strip(); else return t.

</details>

#### FMA-MISMATCH-027 — `src--call_graph_edges-py--_dedupe_edges`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/call_graph_edges-py/_dedupe_edges.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/call_graph_edges-py/_dedupe_edges.json) · [具体 bug 报告](../fm_agent/bug_validation/src--call_graph_edges-py--_dedupe_edges.md) · [probe](../fm_agent/bug_validation/probe_src--call_graph_edges-py--_dedupe_edges.py)
- 触发/冲突：Two CallEdge objects with the same (caller.fqn, callee.fqn) pair but different source values are incorrectly merged into a single entry by _dedupe_edges, which also sorts the output instead of preserving input order.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- edges is an iterable of CallEdge objects
- FMA SPEC post-condition：- Returns a list containing exactly one occurrence of each distinct CallEdge present in edges, preserving the relative order of first occurrences
- FMA 推导 actual POST：Natural language: The function returns a sorted list of CallEdge objects with unique (caller.fqn, callee.fqn) pairs from the input. The list is sorted in ascending order by (caller.fqn, callee.fqn). For each unique pair, the returned CallEdge has caller.fqn equal to the common caller FQN, callee.fqn equal to the common callee FQN, source from the first edge with that pair in iteration order, caller.callsite_names a tuple of all distinct callsite_names across edges with that pair in order of first appearance, and callee.info_names a tuple of all distinct info_names across edges with that pair in order of first appearance. The function has no side effects. Formal logic: Let E be the sequence of input edges in iteration order. Define K = { (e.caller.fq…

</details>

#### FMA-MISMATCH-028 — `src--call_graph_edges-py--_edge_source`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/call_graph_edges-py/_edge_source.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/call_graph_edges-py/_edge_source.json) · [具体 bug 报告](../fm_agent/bug_validation/src--call_graph_edges-py--_edge_source.md) · [probe](../fm_agent/bug_validation/probe_src--call_graph_edges-py--_edge_source.py)
- 触发/冲突：When evidence list contains empty strings alongside non-empty ones, the code filters out empty elements before joining, but the spec requires keeping all elements (up to 4) as long as at least one is non-empty after stripping.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- item is a dict - fallback is a string
- FMA SPEC post-condition：- Returns a string identifying the edge origin - When item contains a key "source" whose value is a string that is non-empty after stripping, returns that stripped string - When no valid "source" value is present and item contains a key "evidence" whose value is a list, returns up to 4 elements from that list, each converted to a string and stripped, joined by "; ", provided at least one such element is non-empty after stripping - When no valid "source" value is present and item contains a key "evidence" whose value is a string that is non-empty after stripping, returns that stripped string - Otherwise, returns fallback unchanged - Never raises an exception
- FMA 推导 actual POST：The function returns a string. If the input dictionary 'item' contains a key 'source' with a value that is a string and is not empty after stripping whitespace, the function returns that stripped string. Otherwise, it checks the key 'evidence'. If the value is a list, it collects all elements that, when converted to a string and stripped, yield a non-empty string; if any such elements exist, it returns a string formed by joining the first four of them with '; '. If no such elements exist, or if 'evidence' is not a list, the function then checks if 'evidence' is a string whose stripped value is non-empty; if so, it returns that stripped string. In all other cases (missing keys, non-matching types, empty strings after stripping), it returns the provid…

</details>

#### FMA-MISMATCH-029 — `src--call_graph_edges-py--_is_edge_file`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/call_graph_edges-py/_is_edge_file.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/call_graph_edges-py/_is_edge_file.json) · [具体 bug 报告](../fm_agent/bug_validation/src--call_graph_edges-py--_is_edge_file.md) · [probe](../fm_agent/bug_validation/probe_src--call_graph_edges-py--_is_edge_file.py)
- 触发/冲突：_is_edge_file returns True for any .json file regardless of content; a .json file with valid JSON but no 'edges' list passes the filter and causes load_call_edges to raise ValueError instead of skipping the file.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- file_path is a Path object referring to an existing file on the filesystem
- FMA SPEC post-condition：- Returns True exactly when the file at file_path contains parseable CallEdge data
- FMA 推导 actual POST：The function returns True if the file extension (suffix) of the given path object, when lowercased, equals '.json'; otherwise returns False. The path object is not modified. No side effects occur. Formalized: (result == (path.suffix.lower() == '.json'))

</details>

#### FMA-MISMATCH-030 — `src--call_graph_edges-py--_normalize_endpoint_label`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/call_graph_edges-py/_normalize_endpoint_label.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/call_graph_edges-py/_normalize_endpoint_label.json) · [具体 bug 报告](../fm_agent/bug_validation/src--call_graph_edges-py--_normalize_endpoint_label.md) · [probe](../fm_agent/bug_validation/probe_src--call_graph_edges-py--_normalize_endpoint_label.py)
- 触发/冲突：lstrip('./') greedily strips all leading '.' and '/' characters instead of only the literal './' prefix, destroying '../' parent-directory components in path-qualified labels.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- label is a non-empty string
- FMA SPEC post-condition：- Returns a string - When the input label represents a function reference qualified by a source-file path, the returned FQN has the source-file extension dot in the filename replaced with "-", leading "./" stripped, "." and empty parent-directory components excluded, and components joined with "::" - When the input label does not represent a path-qualified function reference, the returned string equals the input - The normalization is deterministic: the same input always produces the same output
- FMA 推导 actual POST：The function terminates normally and returns a string r. Let c = _clean_label(label). If _is_path_function_label(c) is False, then r = c. If _is_path_function_label(c) is True, then c can be uniquely decomposed as p + '::' + f where f contains no '::', and r is computed as: let p' = the result of removing all leading occurrences of '.' and '/' from p; let src = PurePosixPath(p'); let b = src.name; let d = b.rfind('.'); let fd = (b[:d] + '-' + b[d+1:]) if d > 0 else b; let dirs = [x for x in src.parent.parts if x not in {'', '.'}]; then r = '::'.join(dirs + [fd, f]).

</details>

#### FMA-MISMATCH-031 — `src--call_graph_edges-py--_parse_callee`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/call_graph_edges-py/_parse_callee.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/call_graph_edges-py/_parse_callee.json) · [具体 bug 报告](../fm_agent/bug_validation/src--call_graph_edges-py--_parse_callee.md) · [probe](../fm_agent/bug_validation/probe_src--call_graph_edges-py--_parse_callee.py)
- 触发/冲突：Non-list info_names raises ValueError via _string_list, but spec only requires errors for missing/non-dict value and missing/empty fqn.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- value is the callee data to parse (a dict, or any value that may result from dict access) - source is a string identifying the origin of the data for error reporting
- FMA SPEC post-condition：- Returns a CalleeTarget constructed from the callee data - The returned CalleeTarget.fqn is a non-empty string - The returned CalleeTarget.info_names is a (possibly empty) tuple of strings - When value is not a dict, raises a ValueError whose message includes source - When value is a dict but does not contain a well-formed "fqn" field yielding a non-empty string, raises an error whose message includes source
- FMA 推导 actual POST：After execution, the function either raises a ValueError or returns a CalleeTarget instance. - If value is not a dict, a ValueError is raised with message f"{source}: missing object 'callee'". - If value is a dict, let fqn_raw = value.get('fqn') and info_names_raw = value.get('info_names', []). Then: * When fqn_raw is None, not a string, or a string that after stripping whitespace becomes empty, an error (ValueError) is raised whose message contains source and 'callee.fqn'. * Else, when info_names_raw is not a list, an error (ValueError) is raised whose message contains source and 'callee.info_names'. * Otherwise, the function returns CalleeTarget(fqn=s, info_names=t) where s is a nonempty string equal to fqn_raw with leading and trailing whitespace…

</details>

#### FMA-MISMATCH-032 — `src--call_graph_edges-py--_parse_caller`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/call_graph_edges-py/_parse_caller.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/call_graph_edges-py/_parse_caller.json) · [具体 bug 报告](../fm_agent/bug_validation/src--call_graph_edges-py--_parse_caller.md) · [probe](../fm_agent/bug_validation/probe_src--call_graph_edges-py--_parse_caller.py)
- 触发/冲突：Passing a non-string value (e.g., integer 1) for fqn alongside a nonempty callsite_names list causes _optional_string to raise ValueError, violating the spec that non-string fqn should default to empty and still return a CallerSelector when callsite_names is nonempty.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- value is the value of a "caller" key from caller input data (a dict or None) - source is a string identifying the origin of the input (used in error messages)
- FMA SPEC post-condition：- When value is not a dict, raises ValueError whose message contains source - When value is a dict but neither a non-empty fqn string nor a non-empty callsite_names list can be extracted from it, raises ValueError whose message contains source - Otherwise, returns a CallerSelector where at least one of fqn or callsite_names is non-empty - The returned CallerSelector's fqn is the canonical normalized form of the string from value["fqn"] when that key holds a non-empty string; otherwise fqn is the empty string - The returned CallerSelector's callsite_names is a tuple containing every non-empty string element from value["callsite_names"] when that key holds a list value; otherwise callsite_names is an empty tuple
- FMA 推导 actual POST：If `value` is not a dictionary, raise ValueError with message `f"{source}: missing object 'caller'"`. Otherwise, let `d = value`. Let `raw_fqn = d.get("fqn", "")` and `raw_calls = d.get("callsite_names", [])`. - If `raw_fqn` is present (key exists and value is not `None`) and is neither a string nor empty, a ValueError is raised by `_optional_string`. - If `raw_calls` is not a list, a ValueError is raised by `_string_list`. - If `raw_calls` is a list any element of which is neither a string nor empty, a ValueError is raised by `_string_list`. Otherwise, after successful processing: - `fqn_str = raw_fqn.strip()` when `raw_fqn` is a non-empty string, else `""`. - `fqn = normalize_fqn_label(fqn_str)` if `fqn_str`, else `""`. - `callsite_names = tuple(e…

</details>

#### FMA-MISMATCH-033 — `src--call_graph_edges-py--_string_list`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/call_graph_edges-py/_string_list.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/call_graph_edges-py/_string_list.json) · [具体 bug 报告](../fm_agent/bug_validation/src--call_graph_edges-py--_string_list.md) · [probe](../fm_agent/bug_validation/probe_src--call_graph_edges-py--_string_list.py)
- 触发/冲突：Zero-width Unicode characters (U+200B, U+200D, U+2060, U+FEFF) survive _clean_label unchanged because Python's str.strip() does not classify them as whitespace; the `if label:` truthiness check then keeps these invisible strings, violating the spec's requirement to include only non-blank labels.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- key is a string naming a field (used in error messages) - source is a string identifying the data origin (used in error messages)
- FMA SPEC post-condition：- When value is not a list, raises ValueError whose message includes source and key - When value is a list and any element is not a string, raises ValueError whose message includes source and key - Otherwise, returns a tuple containing the label-normalized form of every string element of value whose label-normalized form is non-blank - The relative order of elements in the returned tuple preserves the relative order of the corresponding elements in value
- FMA 推导 actual POST：If `value` is not a list, a ValueError is raised with the message "{source}: '{key}' must be a string array". If `value` is a list, then for each element at 1based index `i`, if the element is not a string, a ValueError is raised with the message f"{source}: {key}[{i}] must be a string". Otherwise, if all elements are strings, the function returns a tuple containing every `_clean_label(item)` that is not empty (i.e., `len(clean) > 0`), preserving the original order of items. Formally, let `V` be the input argument `value`. Then: (isinstance(V, list) raises ValueError(source + ": '" + key + "' must be a string array")) (isinstance(V, list) ( ( i {1,,|V|} : isinstance(V[i-1], str)) raises ValueError(source + ": " + key + "[" + str(i) + "] must be a st…

</details>

#### FMA-MISMATCH-219 — `src--call_graph_edges-py--_load_json_edges`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/call_graph_edges-py/_load_json_edges.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/call_graph_edges-py/_load_json_edges.json) · [具体 bug 报告](../fm_agent/bug_validation/src--call_graph_edges-py--_load_json_edges.md) · [probe](../fm_agent/bug_validation/probe_src--call_graph_edges-py--_load_json_edges.py)
- 触发/冲突：Edge dicts with missing/invalid caller or callee keys are caught by _edge_from_mapping via _parse_caller/_parse_callee before an invalid CallEdge is returned.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- text is a string - source_path is a string identifying the origin of the JSON content being parsed
- FMA SPEC post-condition：- When text is valid JSON that parses to an object containing an "edges" key whose value is a list, returns a list of CallEdge objects, one per element of that list, in the same order as the "edges" array - When the "edges" list is empty, returns an empty list - Every returned CallEdge has a callee whose fqn is a non-empty string - Every returned CallEdge has a caller object where at least one of fqn or callsite_names is non-empty - When text is not valid JSON, raises ValueError with a message that includes source_path - When the parsed JSON value is not a dict, raises ValueError with a message that includes source_path - When the parsed dict does not contain an "edges" key whose value is a list, raises ValueError with a message that includes source…
- FMA 推导 actual POST：The function either raises a ValueError or returns a list of CallEdge objects. If ValueError is raised, the exception's message starts with 'source_path' and indicates the specific violation: if text cannot be decoded as JSON it wraps the json.JSONDecodeError; if the decoded data is not a dict it says 'expected JSON object with an 'edges' list'; if data is a dict but data.get('edges') is not a list it says 'expected an 'edges' list'; if any element of the 'edges' list is not a dict it says 'expected edge object'. If the function returns normally, let D = json.loads(text) (which must succeed). Then D is a dict containing an 'edges' key whose value is a list L (otherwise an earlier ValueError would have been raised). The returned list R satisfies len(…

</details>

### `src--cli_backend-py`

#### FMA-MISMATCH-034 — `src--cli_backend-py--_compose_stdin`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/cli_backend-py/_compose_stdin.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/cli_backend-py/_compose_stdin.json) · [具体 bug 报告](../fm_agent/bug_validation/src--cli_backend-py--_compose_stdin.md) · [probe](../fm_agent/bug_validation/probe_src--cli_backend-py--_compose_stdin.py)
- 触发/冲突：When files is an empty list, _compose_stdin returns the prompt string instead of None as the specification requires.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- prompt is a non-empty string - files is a list of file path strings (may be empty)
- FMA SPEC post-condition：- When files is empty, returns None - When files is non-empty, returns a string that begins with a directive to read the listed files, enumerates each file path on a separate line, and appends the prompt text after a blank line
- FMA 推导 actual POST：The function returns a string. If the input list `files` is empty, the returned string is identical to the input `prompt`. Otherwise, the returned string is `'Read these file(s) before acting:\n' + '\n'.join('- ' + path for path in files) + '\n\n' + prompt`. The order of the file paths in the output matches the order in the input list. The function has no side effects and does not modify the inputs.

</details>

#### FMA-MISMATCH-035 — `src--cli_backend-py--_normalize_backend`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/cli_backend-py/_normalize_backend.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/cli_backend-py/_normalize_backend.json) · [具体 bug 报告](../fm_agent/bug_validation/src--cli_backend-py--_normalize_backend.md) · [probe](../fm_agent/bug_validation/probe_src--cli_backend-py--_normalize_backend.py)
- 触发/冲突：Passing an integer value to '_normalize_backend' (via 'build_agent_command' with backend=1) causes AttributeError because (1 or '').strip() calls .strip() on an int.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- value is either None, a string, or any value whose string representation (after stripping leading and trailing whitespace and lowercasing) produces an empty string, a recognized sentinel, the literal "auto", a recognized alias, or an unrecognized string
- FMA SPEC post-condition：- When value is None, or when its normalized form is the empty string, or when the normalized form is one of the recognized disable-sentinel strings ("0", "false", "no", "off"): returns "opencode", the canonical name of the default backend - When the normalized form equals "auto": returns "auto" unchanged, deferring resolution of the auto-sentinel to the caller - When the normalized form matches a recognized backend alias: returns the canonical backend name that the alias maps to (aliases map to the set {"opencode", "codex-cli", "claude-cli"}) - When the normalized form matches none of the above categories: returns the normalized form itself unchanged as a pass-through - The returned string is always non-empty, case-normalized to lowercase, and draw…
- FMA 推导 actual POST：The function returns a string. Let b = (value or "").strip().lower(). If b is empty or b {"0", "false", "no", "off"}, return "opencode". If b == "auto", return "auto". Otherwise, return _BACKEND_ALIASES.get(b, b). Formally: result = "opencode" if (b == "" or b in {"0","false","no","off"}) else ("auto" if b == "auto" else (_BACKEND_ALIASES[b] if b in _BACKEND_ALIASES else b)). The function never raises an exception under the given pre-condition.

</details>

#### FMA-MISMATCH-036 — `src--cli_backend-py--build_agent_command`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/cli_backend-py/build_agent_command.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/cli_backend-py/build_agent_command.json) · [具体 bug 报告](../fm_agent/bug_validation/src--cli_backend-py--build_agent_command.md) · [probe](../fm_agent/bug_validation/probe_src--cli_backend-py--build_agent_command.py)
- 触发/冲突：When 'files' is a non-empty list, file paths are not added to argv — only stdin is composed; backends receive no direct file path context.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- model is a non-empty string identifying an LLM model - prompt is a non-empty string - cwd is a path to an existing directory - files is either None or a list of file path strings (may be empty) - backend is either None or a string identifying a desired CLI backend - effort is either None or a string
- FMA SPEC post-condition：- The effective backend is determined by normalizing the provided backend argument (resolving alias names) when non-None, or by reading the configured default model backend when backend is None; the sentinel value "auto" resolves to a concrete backend - Raises ValueError with a message identifying the unsupported backend when the effective backend is not a supported CLI backend - Returns an AgentCommand whose argv is a non-empty list of argument strings that, when executed via subprocess with cwd resolved to an absolute path as the working directory, invokes the effective backend to process prompt using model - When files is a non-empty list, the prompt text and the contents of each listed file are combined into the AgentCommand's stdin field; each…
- FMA 推导 actual POST：If the resolved backend is not in {'codex-cli', 'claude-cli'}, a ValueError is raised with the message 'unsupported CLI backend: {resolved}'. Otherwise, the function returns an AgentCommand object. The resolved backend is computed as: Let raw = _normalize_backend(backend) if backend is not None and backend != '' else resolve_model_backend(); then resolved = resolve_model_backend() if raw == 'auto' else raw. Let cwd_abs = os.path.abspath(cwd), std = _compose_stdin(prompt, files if files is not None else []), m = (model or '').strip(), e = (effort if effort is not None else cli_effort()).strip(). Then: - If resolved == 'codex-cli', the returned AgentCommand has backend='codex-cli', stdin=std, and argv = ['codex', 'exec', '--sandbox', 'danger-full-acce…

</details>

#### FMA-MISMATCH-037 — `src--cli_backend-py--command_argv`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/cli_backend-py/command_argv.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/cli_backend-py/command_argv.json) · [具体 bug 报告](../fm_agent/bug_validation/src--cli_backend-py--command_argv.md) · [probe](../fm_agent/bug_validation/probe_src--cli_backend-py--command_argv.py)
- 触发/冲突：A non-AgentCommand object with an argv attribute triggers TypeError when list(command) is called because the object is not iterable.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- command is one of: a) an object that carries its argument list in an `argv` attribute whose value is a list of strings, or b) a string, or c) an iterable of strings
- FMA SPEC post-condition：- When command has an `argv` attribute whose value is a list of strings: returns that list object (the same reference) it is the caller's responsibility that the returned list contains only strings - When command is a string: returns a new single-element list containing that string - When command is any other iterable of strings: returns a new list whose elements are the strings yielded by iterating over command, preserving iteration order - The returned value is always a list of strings every element is a str - Returns a list in all cases no exceptions are raised for any valid input type
- FMA 推导 actual POST：The function returns a list of strings. If 'command' is an instance of AgentCommand, the returned list equals 'command.argv'. Otherwise, it equals 'list(command)'. Formally: (isinstance(command, AgentCommand) result = command.argv) (isinstance(command, AgentCommand) result = list(command)) e : (e result type(e) = str)

</details>

#### FMA-MISMATCH-038 — `src--cli_backend-py--messages_to_prompt`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/cli_backend-py/messages_to_prompt.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/cli_backend-py/messages_to_prompt.json) · [具体 bug 报告](../fm_agent/bug_validation/src--cli_backend-py--messages_to_prompt.md) · [probe](../fm_agent/bug_validation/probe_src--cli_backend-py--messages_to_prompt.py)
- 触发/冲突：When a content block's 'text' field is a non-string (integer 42), str.join raises TypeError, crashing the function instead of returning the formatted string as specified.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- messages is a list of dicts, each optionally containing "role" (a string) and "content" (a string or a list of content-block dicts each optionally containing a "text" string key)
- FMA SPEC post-condition：- Returns a single string formed by concatenating every message in order - Each message is formatted as the uppercase of its "role" value (defaulting to "USER" when "role" is absent), followed by a colon and a newline, followed by the message's content text - When "content" is absent from a message dict, the content text is the empty string - When a message's "content" is a string, that string is used directly as the content text - When a message's "content" is a list, the content text is the newline-joined concatenation of the "text" field of each element that is a dict, treating a missing "text" field as the empty string; elements that are not dicts are excluded - Adjacent messages in the output are separated by a single blank line (two consecutiv…
- FMA 推导 actual POST：The function returns a string. Let the input list be `messages`. For each dictionary `msg` in `messages`, define `role = msg.get("role", "user")` (which is a string); define `content` as follows: let `raw = msg.get("content", "")`; if `raw` is a string, `content = raw`; otherwise (raw is a list of dicts) `content = "\n".join(block.get("text", "") for block in raw if isinstance(block, dict))`. Then the returned string is `"\n\n".join(f"{role.upper()}:\n{content}" for msg in messages)`. The input list `messages` and its elements are not modified. This holds provided the pre-condition is satisfied (messages is a list of dicts, each optionally containing string role and content being string or list of content-block dicts with optional text key). No exce…

</details>

#### FMA-MISMATCH-039 — `src--cli_backend-py--resolve_model_backend`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/cli_backend-py/resolve_model_backend.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/cli_backend-py/resolve_model_backend.json) · [具体 bug 报告](../fm_agent/bug_validation/src--cli_backend-py--resolve_model_backend.md) · [probe](../fm_agent/bug_validation/probe_src--cli_backend-py--resolve_model_backend.py)
- 触发/冲突：When FM_AGENT_MODEL_BACKEND is absent from the environment, _normalize_backend(None) returns 'opencode' instead of falling through to auto-detection of Claude/Codex markers.
- 成因复核：仓库 README/docs 明确默认 backend 是 opencode；SPEC 臆造了“环境变量缺失时自动探测”，所以把文档化默认行为报成 bug。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- The process environment may or may not contain a variable named FM_AGENT_MODEL_BACKEND, whose value is any string - The process environment may or may not contain variables named FM_AGENT_HOST or FM_AGENT_CLIENT, whose values are any strings - The process environment may or may not contain any of the markers CLAUDE_PLUGIN_ROOT, CLAUDE_CODE_ENTRYPOINT, CODEX_HOME, CODEX_SANDBOX, or CODEX_EXECUTION_MODE
- FMA SPEC post-condition：- Returns a canonical backend identifier string: one of "opencode", "codex-cli", or "claude-cli" - When FM_AGENT_MODEL_BACKEND is set and its alias-normalized value is not the sentinel "auto", returns the normalized value directly - When FM_AGENT_MODEL_BACKEND is absent from the environment or its normalized value is "auto", the backend is determined by inspecting environment markers in a fixed priority order: 1. FM_AGENT_HOST or FM_AGENT_CLIENT (whichever is set) is checked case-insensitively for "claude" or "codex" substrings 2. The presence of any Claude-specific environment variable (CLAUDE_PLUGIN_ROOT, CLAUDE_CODE_ENTRYPOINT) 3. The presence of any Codex-specific environment variable (CODEX_HOME, CODEX_SANDBOX, CODEX_EXECUTION_MODE) - The first…
- FMA 推导 actual POST：The function returns a string or None according to these rules. Let env(k) denote the value of environment variable k, or None if k is absent. Let norm(v) be the canonical backend name when v is a recognized alias, otherwise v unchanged; norm(None)=None. The return value R is: if norm(env('FM_AGENT_MODEL_BACKEND')) != 'auto' then R = norm(env('FM_AGENT_MODEL_BACKEND')). Otherwise (that is, norm(env('FM_AGENT_MODEL_BACKEND')) == 'auto'), let hint = (env('FM_AGENT_HOST') or env('FM_AGENT_CLIENT') or '').lower(). Then if 'claude' in hint, R = 'claude-cli'; else if 'codex' in hint, R = 'codex-cli'; else if any env(v) is truthy for v in {'CLAUDE_PLUGIN_ROOT', 'CLAUDE_CODE_ENTRYPOINT'}, R = 'claude-cli'; else if any env(v) is truthy for v in {'CODEX_HOME'…

</details>

### `src--domain_knowledge-py`

#### FMA-MISMATCH-040 — `src--domain_knowledge-py--_safe_staged_name`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/domain_knowledge-py/_safe_staged_name.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/domain_knowledge-py/_safe_staged_name.json) · [具体 bug 报告](../fm_agent/bug_validation/src--domain_knowledge-py--_safe_staged_name.md) · [probe](../fm_agent/bug_validation/probe_src--domain_knowledge-py--_safe_staged_name.py)
- 触发/冲突：When the base candidate already exists in used_names, the disambiguation path appends an underscore before the numeric suffix (test_2.txt) instead of a plain numeric suffix (test2.txt).
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- source_path is an absolute file path - used_names is a mutable set of filename strings already reserved for the current batch
- FMA SPEC post-condition：- Returns a filename string that was not present in used_names before the call and adds it to used_names as a side effect - The returned filename is derived from the basename of source_path: characters outside [A-Za-z0-9._-] in the stem are replaced with underscores; the stem is then stripped of leading and trailing ".", "_", and "-" characters; when this produces an empty stem, the stem defaults to "knowledge"; the extension is lowercased - When the derived candidate already exists in used_names, a numeric suffix is appended to the stem (before the extension), starting at 2 and incrementing by 1 until the candidate is unique within used_names - Given the same source_path and an equivalent used_names set, the returned name is deterministic
- FMA 推导 actual POST：After the function executes, the return value `r` is a string satisfying: - `r` was not present in `used_names` upon entry (`r used_names_old`), and after the call `r used_names` with `used_names = used_names_old {r}`. - `r` is constructed from `source_path` as follows: let `basename = os.path.basename(source_path)`, `(stem0, ext0) = os.path.splitext(basename)`, `stem = (re.sub(r'[^A-Za-z0-9._-]+', '_', stem0).strip('._-') or 'knowledge')`, `ext = ext0.lower()`. Then either: (1) `stem + ext used_names_old` and `r = stem + ext`; or (2) there exists an integer `k 2` such that ` j {2, , k-1}: stem + '_' + str(j) + ext used_names_old`, and `stem + '_' + str(k) + ext used_names_old`, and `r = stem + '_' + str(k) + ext`. No other side effects occur; the f…

</details>

#### FMA-MISMATCH-041 — `src--domain_knowledge-py--_split_env_paths`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/domain_knowledge-py/_split_env_paths.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/domain_knowledge-py/_split_env_paths.json) · [具体 bug 报告](../fm_agent/bug_validation/src--domain_knowledge-py--_split_env_paths.md) · [probe](../fm_agent/bug_validation/probe_src--domain_knowledge-py--_split_env_paths.py)
- 触发/冲突：The function only replaces \n with os.pathsep, ignoring carriage return (\r). Input with \r separators is not split, producing a single element containing the raw \r character.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- value is None or a string
- FMA SPEC post-condition：- If value is None or empty, returns an empty list - For a non-empty value, the function treats both the OS path separator (os.pathsep) and newline characters as path element separators, producing a list of individual path strings - Every element in the returned list is a non-empty string with no leading or trailing whitespace - The relative order of the returned path elements corresponds to their order of appearance in value - Empty path components (those that become empty after whitespace stripping) are discarded and do not appear in the result
- FMA 推导 actual POST：The function returns a list of strings with no empty elements. If the input `value` is None or an empty string, or if after replacing newlines with the OS path separator and splitting by that separator all resulting parts consist solely of whitespace characters, the list is empty. Otherwise, each element is a string obtained by splitting the modified input (with newlines replaced by `os.pathsep`) by `os.pathsep`, stripping whitespace from both ends, and keeping those that are non-empty, in the original order. Formally: let `value` be the argument. If `value` is None or `not value` is True, return `[]`. Else define `s = value.replace("\n", os.pathsep)`. Let `L = s.split(os.pathsep)`. Then the returned list is `[x.strip() for x in L if x.strip() != ""…

</details>

#### FMA-MISMATCH-042 — `src--domain_knowledge-py--load_staged_domain_knowledge_text`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/domain_knowledge-py/load_staged_domain_knowledge_text.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/domain_knowledge-py/load_staged_domain_knowledge_text.json) · [具体 bug 报告](../fm_agent/bug_validation/src--domain_knowledge-py--load_staged_domain_knowledge_text.md) · [probe](../fm_agent/bug_validation/probe_src--domain_knowledge-py--load_staged_domain_knowledge_text.py)
- 触发/冲突：Call load_staged_domain_knowledge_text with a non-empty list of staged domain knowledge files; the output incorrectly includes a 'User-provided domain knowledge:' preamble not required by the specification.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- work_dir is a valid directory path string pointing to the fm_agent workspace directory - Staged domain knowledge files (if any) exist at project-root-relative paths as returned by list_staged_domain_knowledge_relpaths
- FMA SPEC post-condition：- Returns a string containing the concatenated UTF-8 Markdown contents of all staged domain knowledge files, formatted for injection into an LLM context - Returns an empty string when no domain knowledge files are staged - Each file's content is introduced by a level-3 Markdown heading of the form "### {relative_path}" in the order list_staged_domain_knowledge_relpaths produces them - Files whose content cannot be read (OSError during open/read) are silently excluded from the output - Files whose content is empty or whitespace-only after stripping are silently excluded from the output - Bytes in file content that cannot be decoded as UTF-8 are replaced with the Unicode replacement character - The output has no leading or trailing whitespace beyond t…
- FMA 推导 actual POST：If `list_staged_domain_knowledge_relpaths(work_dir)` returns an empty list, the function returns an empty string. Otherwise, let `P` be the nonempty sorted list of relative paths returned by that call, and let `ROOT = os.path.dirname(os.path.abspath(work_dir))`. For each path `p` in `P`, attempt to open and read the file at `os.path.join(ROOT, p)` using UTF8 encoding with replacement on decoding errors. If the file is successfully opened, let `content` be the result of `f.read().strip()`. A path `p` *contributes* iff `content` is nonempty. Let `C` be the list of contributing pairs `(p, content)` in the order they appear in `P`. Define `HEADER = 'User-provided domain knowledge:\nUse these Markdown notes as additional context for intended behavior, te…

</details>

#### FMA-MISMATCH-043 — `src--domain_knowledge-py--resolve_domain_knowledge_paths`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/domain_knowledge-py/resolve_domain_knowledge_paths.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/domain_knowledge-py/resolve_domain_knowledge_paths.json) · [具体 bug 报告](../fm_agent/bug_validation/src--domain_knowledge-py--resolve_domain_knowledge_paths.md) · [probe](../fm_agent/bug_validation/probe_src--domain_knowledge-py--resolve_domain_knowledge_paths.py)
- 触发/冲突：Passing a non-existent file path causes a ValueError instead of silently excluding it from the returned list.
- 成因复核：函数 docstring 明确是 Validate，源码与 README 都把不存在的知识文件视为配置错误；SPEC 反而要求静默丢弃。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- paths is an iterable of path-like strings, potentially nested (may contain inner iterables of path strings) - base_dir is a string referencing an existing directory - fallback_base_dir is None or a string referencing an existing directory
- FMA SPEC post-condition：- Returns a list of absolute file path strings, one per distinct valid domain-knowledge markdown file - Each input entry is expanded for user home directories and flattened from any nesting - If an expanded entry is absolute, it is used directly; otherwise it is resolved against base_dir - When fallback_base_dir is not None and the base_dir-resolved path does not exist on the filesystem, the entry is resolved against fallback_base_dir as a secondary base - An entry whose resolved path does not exist on the filesystem is excluded from the returned list - An entry whose resolved path is not a regular file is excluded from the returned list - An entry whose resolved path has a file extension not in the set of recognized markdown extensions is excluded…
- FMA 推导 actual POST：If the function returns normally, it returns a list `resolved` of strings satisfying: (1) each element `p` `resolved` is the absolute path (via `os.path.abspath`) of an existing regular file whose extension (lowercase) belongs to the set `VALID_DOMAIN_KNOWLEDGE_EXTENSIONS`; (2) the canonical paths `os.path.realpath(p)` are all distinct, i.e., ij, `os.path.realpath(resolved[i])` `os.path.realpath(resolved[j])`; (3) `resolved` preserves the order of first occurrence of each unique canonical file as they appear in the flattened input sequence `_flatten_paths(paths)`; (4) for every `raw_path` in `_flatten_paths(paths)`, either its resolved absolute path (after expansion, candidate selection, and abspath) appears in `resolved` (if it passes all checks an…

</details>

#### FMA-MISMATCH-044 — `src--domain_knowledge-py--stage_domain_knowledge_files`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/domain_knowledge-py/stage_domain_knowledge_files.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/domain_knowledge-py/stage_domain_knowledge_files.json) · [具体 bug 报告](../fm_agent/bug_validation/src--domain_knowledge-py--stage_domain_knowledge_files.md) · [probe](../fm_agent/bug_validation/probe_src--domain_knowledge-py--stage_domain_knowledge_files.py)
- 触发/冲突：shutil.rmtree(target_dir) followed by os.replace(tmp_dir, target_dir) creates a window where the staging directory does not exist, violating the atomicity specification.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a directory path that exists on the filesystem. - work_dir is the fm_agent/ workspace directory path. - markdown_paths is None or an iterable of file path strings (relative or absolute).
- FMA SPEC post-condition：- When markdown_paths is falsy (None or empty): the staging directory <work_dir>/spec_prompts/domain_context/user_knowledge/ is NOT modified; any previously staged files are preserved. This supports resume runs. - When markdown_paths is truthy and non-empty: the staging directory is atomically replaced to contain exactly copies of the resolved markdown files plus a manifest file recording which source files were staged. - The replacement is atomic: a temporary directory is populated, then atomically swapped into place; a concurrent reader either sees the complete old state or the complete new state. - Returns a sorted list of project-relative path strings, each prefixed with "fm_agent/", for all domain knowledge files that are currently staged under…
- FMA 推导 actual POST：After executing stage_domain_knowledge_files(proj_dir, work_dir, markdown_paths): If markdown_paths is falsy (None or an empty iterable), then the function returns the list of currently staged domain knowledge file paths relative to the project root (each prefixed with 'fm_agent/') as returned by list_staged_domain_knowledge_relpaths(work_dir). The file system remains unchanged; no files in the staging directory are added, removed, or modified. If markdown_paths is truthy (a non-empty iterable of path strings), then: 1. Let resolved = resolve_domain_knowledge_paths(markdown_paths, base_dir=proj_dir, fallback_base_dir=os.getcwd()). resolved is a list of existing absolute source file paths. 2. Let target_dir = os.path.join(work_dir, USER_KNOWLEDGE_REL…

</details>

### `src--entry_reasoning_pipeline-py`

#### FMA-MISMATCH-045 — `src--entry_reasoning_pipeline-py--_count_mismatches`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_count_mismatches.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/entry_reasoning_pipeline-py/_count_mismatches.json) · [具体 bug 报告](../fm_agent/bug_validation/src--entry_reasoning_pipeline-py--_count_mismatches.md) · [probe](../fm_agent/bug_validation/probe_src--entry_reasoning_pipeline-py--_count_mismatches.py)
- 触发/冲突：A .json file containing valid JSON that is not a dict (e.g., an array) causes json.load() to return a non-dict object, and .get('verdict') raises an unhandled AttributeError — the except block only catches OSError and ValueError.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- results_dir is a filesystem path
- FMA SPEC post-condition：- Returns an integer 0; does not raise any exception - When results_dir does not exist or is not a directory, returns 0 - When results_dir exists and is a directory, the returned value is the number of JSON files (filenames ending in ".json") located anywhere in the directory tree rooted at results_dir whose parsed JSON object contains the field "verdict" with the string value "MISMATCH" - Files whose filename does not end in ".json", files that cannot be opened for reading, and files containing malformed JSON are excluded from the count - Does not create, delete, rename, or modify any file or directory
- FMA 推导 actual POST：The function either raises an exception (OSError from os.walk, or AttributeError if a .json file parses to a non-dict) and returns no value, or it completes normally. Under normal execution, the return value is the number of non-directory files under the results_dir subtree whose name ends with '.json', that can be opened and parsed as a JSON mapping without raising OSError or ValueError, and for which the mapping has the key 'verdict' with value 'MISMATCH'. Formally: let S be the set of all non-directory entries yielded by os.walk(results_dir) (following its default semantics). Let is_json(f) = basename(f) ends with '.json'. Define safe_parse(f) = open(f) and json.load read without OSError/ValueError, producing a dict. Let normal = (os.walk raises…

</details>

#### FMA-MISMATCH-046 — `src--entry_reasoning_pipeline-py--_enumerate_source_files`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_enumerate_source_files.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/entry_reasoning_pipeline-py/_enumerate_source_files.json) · [具体 bug 报告](../fm_agent/bug_validation/src--entry_reasoning_pipeline-py--_enumerate_source_files.md) · [probe](../fm_agent/bug_validation/probe_src--entry_reasoning_pipeline-py--_enumerate_source_files.py)
- 触发/冲突：Files without a dot in their filename are mapped to '' extension and incorrectly included when EXT_TO_LANG[''] is truthy, violating the spec that requires an actual file extension.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is an existing directory path
- FMA SPEC post-condition：- Returns a sorted list (ascending lexicographic order) of source-file relative paths (using "/" separators) for every regular file under proj_dir that satisfies ALL of the following: a) Not located within any subdirectory named "fm_agent" or ".git" at any nesting level below proj_dir b) Has a file extension for which EXT_TO_LANG returns a truthy value c) _is_test_file returns False for the relative path - The returned paths are relative to proj_dir - The returned list is in ascending lexicographic order - Files excluded by test-file heuristics are omitted; the test-file exemption for the entry function is a caller-side concern and does not affect this function's output
- FMA 推导 actual POST：The function returns a sorted list of strings, each representing a relative path (using '/' separators) from proj_dir to a Python source file. The list includes every file that (a) resides under proj_dir after skipping the 'fm_agent' and '.git' directories during traversal, (b) has a file extension mapped by EXT_TO_LANG, and (c) is not classified as a test file by _is_test_file. No other files are included. The returned list is sorted in lexicographical order. The function has no side effects: proj_dir and the global EXT_TO_LANG are unmodified. Given the pre-condition that proj_dir exists, the walk completes without raising an exception. Formally: let F = { f_rel | f_abs Walk(proj_dir, skip={'fm_agent','.git'}) such that f_rel = relpath(f_abs, proj_…

</details>

#### FMA-MISMATCH-047 — `src--entry_reasoning_pipeline-py--_extracted_file_to_source_rel`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_extracted_file_to_source_rel.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/entry_reasoning_pipeline-py/_extracted_file_to_source_rel.json) · [具体 bug 报告](../fm_agent/bug_validation/src--entry_reasoning_pipeline-py--_extracted_file_to_source_rel.md) · [probe](../fm_agent/bug_validation/probe_src--entry_reasoning_pipeline-py--_extracted_file_to_source_rel.py)
- 触发/冲突：When parent directory name starts with hyphen (rfind returns 0), 'hyphen > 0' check fails, causing prepend of parent directory when spec requires returning dir_name alone.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- extracted_rel is a relative path whose last path component names a function file and whose parent directory name was derived from a source filename by replacing the last "." with "-"
- FMA SPEC post-condition：- Returns the source-file relative path obtained by replacing the last hyphen in the parent directory name with a dot and stripping the function-name file component - When the parent directory name contains no hyphen after its first character, the directory name is returned unchanged and no parent directory prefix is prepended - The returned path uses "/" as the path separator
- FMA 推导 actual POST：If the input extracted_rel satisfies the pre-condition (a relative path whose last component is a function file and whose immediate parent directory name was formed by replacing the last '.' of a source filename with '-'), the function returns a relative path that is the original source file: it is the grandparent directory (if any) joined with a name obtained from the parent directory name by reversing the replacementlocating the last hyphen (which is guaranteed to exist and have index > 0) and substituting it with a dot. Formally, let func_dir = os.path.dirname(extracted_rel), src_dir = os.path.dirname(func_dir), dir_name = os.path.basename(func_dir), and h = dir_name.rfind('-'). If h > 0 then source_base = dir_name[:h] + '.' + dir_name[h+1:]; els…

</details>

#### FMA-MISMATCH-048 — `src--entry_reasoning_pipeline-py--_make_run_copy`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_make_run_copy.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/entry_reasoning_pipeline-py/_make_run_copy.json) · [具体 bug 报告](../fm_agent/bug_validation/src--entry_reasoning_pipeline-py--_make_run_copy.md) · [probe](../fm_agent/bug_validation/probe_src--entry_reasoning_pipeline-py--_make_run_copy.py)
- 触发/冲突：The function removes the old run_dir before copying, creating a window where run_dir is absent and any observer sees a missing directory, violating the atomic-installation guarantee.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is an existing directory path
- FMA SPEC post-condition：- proj_dir is never mutated - run_dir holds a fresh recursive copy of proj_dir reflecting the state of proj_dir at call time, excluding entries whose names match a fixed, predefined set of skip patterns - Directory symlinks present in proj_dir are preserved as symlinks in the copy - Any pre-existing data at run_dir (e.g. a leftover directory from an interrupted prior invocation) is fully removed before the new copy is created - The copy is atomically installed: no observer can see a partial or intermediate state at run_dir
- FMA 推导 actual POST：If the function returns normally: run_dir exists as a directory whose recursive contents are an exact copy of proj_dir except that any files or subdirectories matching patterns in _SKIP_DIRS (including '.git') are omitted; proj_dir is unchanged; no run_dir + '.tmp' directory exists. If an exception occurs, the function does not return normally, and the filesystem may be partially modified: old run_dir and/or run_dir.tmp may have been removed, and run_dir.tmp may contain an incomplete copy.

</details>

#### FMA-MISMATCH-049 — `src--entry_reasoning_pipeline-py--_restrict_to_chains`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_restrict_to_chains.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/entry_reasoning_pipeline-py/_restrict_to_chains.json) · [具体 bug 报告](../fm_agent/bug_validation/src--entry_reasoning_pipeline-py--_restrict_to_chains.md) · [probe](../fm_agent/bug_validation/probe_src--entry_reasoning_pipeline-py--_restrict_to_chains.py)
- 触发/冲突：A node (E) not reachable from entry_func (A) but backward-reachable from end_func (C) is incorrectly retained in the output.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- call_graph is a dict mapping each FQN string to a list of callee FQN strings, where every callee referenced in any value list is also a key in call_graph (the graph is closed under its FQN space) - entry_func is an FQN string that is a key in call_graph - end_funcs is an iterable of FQN strings, possibly empty
- FMA SPEC post-condition：- call_graph is never mutated; a new dict is returned (or the original when end_funcs is falsy) - When end_funcs is empty or falsy, call_graph is returned unchanged - When end_funcs is non-empty, the returned dict contains exactly those FQNs that satisfy both: 1. Reachable from entry_func via zero or more edges in call_graph, AND 2. Can reach at least one member of end_funcs via zero or more edges in call_graph - For each FQN in the returned dict that is also a member of end_funcs: its callee list is empty (the FQN is a terminal stop-point) - For each FQN in the returned dict that is not a member of end_funcs: its callee list contains exactly the subset of its callees from call_graph that also appear in the returned dict
- FMA 推导 actual POST：If `bool(end_funcs)` is False, the return value is the input dictionary `call_graph` unchanged (identical reference). Otherwise, let `V` be the set of keys in `call_graph`, and for each `u V`, let `E(u) = call_graph[u]`. Let `T = {t end_funcs | t V}` be the end_funcs present in the graph. Define `R = { u V | there exists a directed path from u to some t T }` (nodes that can reach an end_func). The returned dictionary `pruned` satisfies: (1) `set(pruned.keys()) = R`; (2) for every `u R`, if `u T` then `pruned[u] = []`, else `pruned[u] = [v for v in E(u) if v R]`. The original `call_graph` is assumed to contain only nodes reachable from `entry_func`; therefore `R` is exactly the set of functions lying on some call chain from `entry_func` to an end_fun…

</details>

#### FMA-MISMATCH-050 — `src--entry_reasoning_pipeline-py--_run_entry_pipeline_inner`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_run_entry_pipeline_inner.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/entry_reasoning_pipeline-py/_run_entry_pipeline_inner.json) · [具体 bug 报告](../fm_agent/bug_validation/src--entry_reasoning_pipeline-py--_run_entry_pipeline_inner.md) · [probe](../fm_agent/bug_validation/probe_src--entry_reasoning_pipeline-py--_run_entry_pipeline_inner.py)
- 触发/冲突：When an exception propagates from inside the try block of _run_entry_pipeline_inner, the mismatch count print statement (lines 494-495) is skipped because it sits after the try-finally block, violating the spec that requires the count on every run.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is an absolute path to an existing directory - work_dir is the path <proj_dir>/fm_agent - entry_func is a non-empty FQN string - domain_knowledge_files, if provided, is a non-empty collection of file paths
- FMA SPEC post-condition：- proj_dir is never mutated by this function or any callee transitively invoked - A temporary directory at <proj_dir>.fm-entry-run is created during execution and destroyed before return, regardless of success or failure - The set of functions operated on is the subset reachable from entry_func via the static call graph; when end_funcs is non-empty, the set is further restricted to functions on at least one call-chain path from entry_func to some member of end_funcs - On successful completion, work_dir contains the complete fm_agent/ output produced by running the standard pipeline on the trimmed project copy - On failure, any partial fm_agent/ results already produced within the temporary run directory are copied to work_dir before the temporary di…
- FMA 推导 actual POST：After the function terminates (whether normally or by exception): (1) The temporary directory `run_dir = proj_dir + '.fm-entry-run'` is deleted. (2) If the subdirectory `run_work_dir = run_dir + '/fm_agent'` existed at the moment the finally block executed, then `work_dir` (which is `proj_dir + '/fm_agent'`) is replaced by a copy of `run_work_dir`. If `run_work_dir` did not exist, `work_dir` is left unchanged (except for the conditional deletion that only fires when `run_work_dir` exists, so its prior state is preserved). (3) On normal return: - The standard output contains a line showing the number of mismatch verdicts from `<work_dir>/logic_verification_results/`. - The function returns `None`. (4) On an exception that propagates out of the functi…

</details>

#### FMA-MISMATCH-051 — `src--entry_reasoning_pipeline-py--_trim_source_file`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_trim_source_file.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/entry_reasoning_pipeline-py/_trim_source_file.json) · [具体 bug 报告](../fm_agent/bug_validation/src--entry_reasoning_pipeline-py--_trim_source_file.md) · [probe](../fm_agent/bug_validation/probe_src--entry_reasoning_pipeline-py--_trim_source_file.py)
- 触发/冲突：open(filepath, 'w') on line 149 uses default text mode without encoding parameter, re-encoding file bytes in system default encoding and failing to preserve the original file encoding as the spec requires
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- filepath is an absolute path to an existing source file - keep_names is a collection of function name strings to preserve - proj_dir is a project root directory path or None
- FMA SPEC post-condition：- When the file extension does not map to a recognized language key in EXT_TO_LANG, the file is left untouched and (0, 0) is returned - When the file has no detected function bodies (spans is empty), the file is left untouched and (0, 0) is returned - When the file has detected function bodies: every function body whose name is a member of keep_names is preserved, every function body whose name is not a member of keep_names is removed, and all source lines that do not belong to any function body are preserved in their original order and form - The source file at filepath is overwritten with the resulting content; the file path does not change - Returns a tuple (kept, removed) where kept is the count of function bodies preserved, removed is the count…
- FMA 推导 actual POST：After the execution of _trim_source_file, one of the following scenarios holds: 1. (Normal return) The function returns a tuple (kept, removed) where kept and removed are non-negative integers, and the file at filepath is in a consistent state. - Compute ext = os.path.basename(filepath).rsplit(".", 1)[-1] if "." in os.path.basename(filepath) else "". - Compute lang_key = EXT_TO_LANG.get(ext). - If lang_key is falsy: kept = 0, removed = 0, and the file at filepath is unchanged (identical to its pre-execution content). - Otherwise, let (spans, raw_lines) = _function_spans(filepath, lang_key, proj_dir) (assuming no exception). * If spans is empty: kept = 0, removed = 0, and the file at filepath is unchanged. * Else: + kept = |{ (n, s, e) spans | n keep…

</details>

#### FMA-MISMATCH-052 — `src--entry_reasoning_pipeline-py--run_entry_pipeline`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/run_entry_pipeline.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/entry_reasoning_pipeline-py/run_entry_pipeline.json) · [具体 bug 报告](../fm_agent/bug_validation/src--entry_reasoning_pipeline-py--run_entry_pipeline.md) · [probe](../fm_agent/bug_validation/probe_src--entry_reasoning_pipeline-py--run_entry_pipeline.py)
- 触发/冲突：Calling run_entry_pipeline with a valid entry_func creates or modifies proj_dir/fm_agent/, violating the spec claim that proj_dir is never mutated.
- 成因复核：SPEC 把“源码不被修改”扩大成“proj_dir 中任何文件都不写”；函数文档明确会把生成的 fm_agent/ 结果复制回 proj_dir，因此 mismatch 来自边界定义错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a non-empty string representing an existing directory path
- FMA SPEC post-condition：- If entry_func is None, raises ValueError before any filesystem side effects occur - proj_dir is never mutated; all filesystem mutations are confined to temporary copies that are discarded before return, regardless of success or failure - A temporary run directory at <proj_dir>.fm-entry-run is created during execution and deleted before return - On successful completion, <proj_dir>/fm_agent/ contains specification, reasoning, and bug-validation results scoped to functions reachable from entry_func via the static call graph; when end_funcs is non-empty, the scope is restricted to functions on at least one call-chain path from entry_func to an element of end_funcs - On failure, any partial results already written to <proj_dir>/fm_agent/ by the inner…
- FMA 推导 actual POST：The function may terminate normally (implicitly returning None) or by raising an exception. The post-condition depends on the value of entry_func at call time. Case A entry_func is None: * The function raises ValueError("entry_func is required to run the entry pipeline"). * The filesystem is unmodified; no temporary directory is created and proj_dir remains unchanged. * Global configuration and test-file exemption sets are untouched. * Formally: exception = ValueError (global state unchanged) Case B entry_func is not None: * The original proj_dir is resolved to its absolute path P = os.path.abspath(proj_dir). From that point onward, regardless of whether the function returns normally or propagates an exception from `_run_entry_pipeline_inner`, the f…

</details>

#### FMA-MISMATCH-220 — `src--entry_reasoning_pipeline-py--_entry_func_source_rel`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_entry_func_source_rel.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/entry_reasoning_pipeline-py/_entry_func_source_rel.json) · [具体 bug 报告](../fm_agent/bug_validation/src--entry_reasoning_pipeline-py--_entry_func_source_rel.md) · [probe](../fm_agent/bug_validation/probe_src--entry_reasoning_pipeline-py--_entry_func_source_rel.py)
- 触发/冲突：FQN with leading '::' does not produce absolute path on this Linux platform; os.path.join ignores empty string components
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- entry_func is a non-empty FQN string whose components are delimited by "::" - The last component of entry_func is the function name - The second-to-last component of entry_func is the extraction directory name, which follows the convention of replacing the last "." in the source-filename basename with "-" and appending "-<extension>" (e.g. "loader.cpp" → "loader-cpp")
- FMA SPEC post-condition：- Returns a source-file relative path (using "/" separators) derived by reversing the FQN-to-extracted-file-path mapping convention, regardless of the host OS path separator - The returned path identifies the source file that contains the function named by entry_func
- FMA 推导 actual POST：The function returns a string representing the project-relative path to the source file that defined `entry_func`, using forward slashes ('/') as separators. The path is obtained by splitting `entry_func` on '::', joining all components into a relative extracted-file path, reversing the extraction naming convention (converting the second-to-last component `<basename>-<ext>` back to `<basename>.<ext>`, and removing the final function-name component), and finally replacing any backslashes with forward slashes (though the intermediate call already guarantees '/' separators). Formally: Let C = entry_func.split('::'), k = len(C) 2, and let extracted_rel = os.path.join(*C). Let intermediate = _extracted_file_to_source_rel(extracted_rel) (which already use…

</details>

#### FMA-MISMATCH-221 — `src--entry_reasoning_pipeline-py--_select_functions_by_source`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_select_functions_by_source.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/entry_reasoning_pipeline-py/_select_functions_by_source.json) · [具体 bug 报告](../fm_agent/bug_validation/src--entry_reasoning_pipeline-py--_select_functions_by_source.md) · [probe](../fm_agent/bug_validation/probe_src--entry_reasoning_pipeline-py--_select_functions_by_source.py)
- 触发/冲突：Call _select_functions_by_source with extractable source files but an entry_func FQN that does not match any extracted function; the spec requires ValueError, and the code correctly raises it.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is an existing directory (the project root) - entry_func is a non-empty fully-qualified function name string - end_funcs is an iterable of zero or more fully-qualified function name strings - extra_call_edges, when provided, contributes supplemental call edges through a format recognized by _build_call_graph
- FMA SPEC post-condition：- proj_dir is never mutated; all mutations occur in a temporary sibling directory that is destroyed before this function returns - Returns a tuple (all_by_source, keep_by_source) where: - all_by_source is a dict mapping each source-file relative path to the set of ALL function names that were extractable from that source file - keep_by_source is a dict mapping each source-file relative path to the set of function names that are transitively reachable from entry_func in the static call graph; when end_funcs is non-empty, this set is further restricted to function names that lie on at least one call-chain path from entry_func to some member of end_funcs - Raises ValueError when: - No extractable source files are found under proj_dir - No extractable f…
- FMA 推导 actual POST：After normal execution, the function returns a tuple (all_by_source, keep_by_source). all_by_source maps each relative source file path (as enumerated from a temporary copy of proj_dir) to a list of fully qualified names of all extractable functions in that file. keep_by_source maps each source file path to a list of fully qualified names of functions that are reachable from entry_func in the call graph; if end_funcs is non-empty, only those functions that lie on at least one call chain from entry_func to a function in end_funcs are included. The call graph is built using a full extraction of a temporary copy of proj_dir, incorporating any extra_call_edges if provided. The temporary copy and all extraction artifacts are completely removed before the…

</details>

### `src--env_check-py`

#### FMA-MISMATCH-053 — `src--env_check-py--_check_comment_checker`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/env_check-py/_check_comment_checker.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/env_check-py/_check_comment_checker.json) · [具体 bug 报告](../fm_agent/bug_validation/src--env_check-py--_check_comment_checker.md) · [probe](../fm_agent/bug_validation/probe_src--env_check-py--_check_comment_checker.py)
- 触发/冲突：When disabled_hooks is null (None) the 'in' operator raises TypeError instead of returning (False, error_message).
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- OH_MY_OPENAGENT_CONFIG is a string path to the oh-my-openagent JSON configuration file - The filesystem is accessible for existence checks and file reads at that path
- FMA SPEC post-condition：- Returns (True, None) when the config file at OH_MY_OPENAGENT_CONFIG exists, parses as valid JSON, and the value of key "disabled_hooks" (defaulting to an empty list when absent) contains the string "comment-checker" - Returns (False, error_message) when the config file does not exist at OH_MY_OPENAGENT_CONFIG, with the error_message identifying the missing path - Returns (False, error_message) when the config file exists but cannot be parsed as valid JSON or cannot be opened for reading (IOError), with the error_message including the failure reason - Returns (False, error_message) when the config file exists and parses successfully but "disabled_hooks" does not contain "comment-checker", with the error_message describing the corrective action requ…
- FMA 推导 actual POST：After execution, the function returns a tuple (success, message). If os.path.exists(OH_MY_OPENAGENT_CONFIG) is false, then success = False and message = 'oh-my-openagent config not found at {OH_MY_OPENAGENT_CONFIG}'. If the file exists but reading or json.load fails with json.JSONDecodeError or IOError, then success = False and message = 'Failed to read {OH_MY_OPENAGENT_CONFIG}: {exception}'. If the file exists and is parsed successfully into cfg, but 'comment-checker' is not present in the list cfg.get('disabled_hooks', []), then success = False and message contains a warning about comment-checker hook not being disabled. Otherwise (file exists, valid JSON, and 'comment-checker' is in the disabled_hooks list), success = True and message = None. For…

</details>

#### FMA-MISMATCH-054 — `src--env_check-py--_check_llm_api_key`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/env_check-py/_check_llm_api_key.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/env_check-py/_check_llm_api_key.json) · [具体 bug 报告](../fm_agent/bug_validation/src--env_check-py--_check_llm_api_key.md) · [probe](../fm_agent/bug_validation/probe_src--env_check-py--_check_llm_api_key.py)
- 触发/冲突：Pass a non-string truthy value (int 42) as config.LLM_API_KEY
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- config is an object with a LLM_API_KEY attribute.
- FMA SPEC post-condition：- Returns (True, None) when the value of config.LLM_API_KEY is a non-empty string that does not appear in a fixed, predefined collection of known placeholder or sentinel values. - Returns (False, error_message) when config.LLM_API_KEY is empty (falsy) or matches an entry in the predefined collection of known placeholder values. In this case error_message is a fixed, human-readable diagnostic string. - The function performs no I/O and has no side effects.
- FMA 推导 actual POST：The function returns a tuple (ok, msg) without modifying the config parameter. ok is True if config.LLM_API_KEY evaluates to a truthy value and is not one of the placeholder values ('', 'YOUR_LLM_API_KEY', 'sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'); otherwise ok is False. msg is None when ok is True, otherwise msg is the string 'LLM_API_KEY is not set in .env file'. No exceptions are raised. Formally: ((ok == True) (config.LLM_API_KEY and config.LLM_API_KEY not in {'', 'YOUR_LLM_API_KEY', 'sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'})) ((ok == False) config.LLM_API_KEY or config.LLM_API_KEY in {'', 'YOUR_LLM_API_KEY', 'sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'}) (msg == None if ok else msg == 'LLM_API_KEY is not set in .env…

</details>

#### FMA-MISMATCH-055 — `src--env_check-py--_check_oh_my_openagent`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/env_check-py/_check_oh_my_openagent.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/env_check-py/_check_oh_my_openagent.json) · [具体 bug 报告](../fm_agent/bug_validation/src--env_check-py--_check_oh_my_openagent.md) · [probe](../fm_agent/bug_validation/probe_src--env_check-py--_check_oh_my_openagent.py)
- 触发/冲突：subprocess.run returncode is never inspected; non-zero exit from bunx (e.g., package not found) is not an exception, so the function falsely reports (True, None).
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- None. This function has no required state or arguments.
- FMA SPEC post-condition：- Returns (True, None) when the `oh-my-openagent` command is available and executable via `bunx`. - Returns (False, str) when the `oh-my-openagent` command is not available or the check times out. The returned string is a fixed error message. - The function does not raise exceptions to its caller; all failure modes are captured as (False, str).
- FMA 推导 actual POST：The function returns a tuple (success, message). If the subprocess call to ['bunx', 'oh-my-openagent', '--version'] completes without raising an exception, the return value is (True, None). If any exception occurs during that call (e.g., timeout, file not found), the return value is (False, 'oh-my-openagent is not installed (bunx unavailable or timed out)'). No exception escapes the function. Formal logic: let result be the value returned by _check_oh_my_openagent. Then (result = (True, None)) (subprocess.run(['bunx', 'oh-my-openagent', '--version'], capture_output=True, text=True, timeout=10) did not raise an exception) (result = (False, 'oh-my-openagent is not installed (bunx unavailable or timed out)')) (the same subprocess.run call raised an exc…

</details>

#### FMA-MISMATCH-056 — `src--env_check-py--is_interactive`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/env_check-py/is_interactive.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/env_check-py/is_interactive.json) · [具体 bug 报告](../fm_agent/bug_validation/src--env_check-py--is_interactive.md) · [probe](../fm_agent/bug_validation/probe_src--env_check-py--is_interactive.py)
- 触发/冲突：Removing 'sys' from the module's global namespace before calling is_interactive() causes a NameError, violating the spec that requires the function to return True/False based solely on the file descriptor table without depending on mutable state.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- None.
- FMA SPEC post-condition：- Returns True when the standard input stream (stdin) is attached to a terminal device, meaning the calling process can receive interactive user input via stdin. - Returns False when stdin is not attached to a terminal (e.g., piped input, redirection from a file, or non-TTY execution environment). - The return value does not depend on any mutable state and is determined solely by the process's file descriptor table at the time of the call.
- FMA 推导 actual POST：If `sys` is not defined, a `NameError` is raised. If `sys.stdin` does not have an `isatty` attribute, an `AttributeError` is raised. Otherwise, the function returns `True` if standard input is a terminal (TTY), `False` otherwise. Formally: normal postcondition: `result == sys.stdin.isatty()`; exceptional postconditions: `<NameError, 'sys'>` or `<AttributeError, 'isatty'>`.

</details>

#### FMA-MISMATCH-057 — `src--env_check-py--run`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/env_check-py/run.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/env_check-py/run.json) · [具体 bug 报告](../fm_agent/bug_validation/src--env_check-py--run.md) · [probe](../fm_agent/bug_validation/probe_src--env_check-py--run.py)
- 触发/冲突：The code prepends two spaces to warning messages (' [!] ...'), violating the spec which requires '[!] ...' with no leading spaces.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a directory path that exists on the filesystem. - config provides access to an LLM API key (the specific accessor used is LLM_API_KEY).
- FMA SPEC post-condition：- Returns True when any of the following holds: (a) all environment checks pass with no warnings, (b) one or more checks fail but the session is non-interactive, (c) one or more checks fail in an interactive session and the user chooses to proceed ('p'), or (d) one or more checks fail in an interactive session and the user chooses to permanently ignore the failing checks ('i'). - Returns False only when one or more checks fail in an interactive session and the user chooses to quit ('q'). No persistent state is modified in this case. - When the user chooses 'i', the union of all previously ignored check IDs and the IDs of all currently failing checks is persisted to proj_dir/fm_agent/.env_check_memory, causing all such checks to be skipped on subsequ…
- FMA 推导 actual POST：After execution of run(proj_dir, config), one of the following mutually exclusive outcomes occurs: 1. **Exception**: The function raises an exception of type OSError, KeyboardInterrupt, or EOFError. In this case, partial side effects may have occurred (e.g., work_dir may have been created, ignored set loaded, some logging/printing performed) but no return value is produced. 2. **Normal return**: The function returns a boolean value `r`. Let: - `work_dir = os.path.join(proj_dir, 'fm_agent')` - `ignored0` = set of check IDs loaded from persistence at the start (via `_load_ignored(work_dir)`, empty if none) - `FailedChecks` = { (id, label, msg) | (id, label, fn) in checks, id not in ignored0, and fn() returns (False, msg) } - `warnings` = list construc…

</details>

#### FMA-MISMATCH-222 — `src--env_check-py--_memory_path`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/env_check-py/_memory_path.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/env_check-py/_memory_path.json) · [具体 bug 报告](../fm_agent/bug_validation/src--env_check-py--_memory_path.md) · [probe](../fm_agent/bug_validation/probe_src--env_check-py--_memory_path.py)
- 触发/冲突：work_dir ends with trailing path separator causes os.path.join to skip extra separator, diverging from spec-required literal concatenation — but unreachable via public run() API
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- work_dir is a string referencing an existing directory
- FMA SPEC post-condition：- Returns the filesystem path to the persisted memory file within work_dir - The returned path is deterministic: the same work_dir value always produces the same result - The returned path is the concatenation of work_dir, the platform path separator, and the fixed filename ".env_check_memory"
- FMA 推导 actual POST：The function returns the result of `os.path.join(work_dir, '.env_check_memory')`, which is a string representing the path formed by properly joining the existing directory `work_dir` with the constant filename `.env_check_memory`. The function has no side effects; `work_dir` remains unchanged. Formally, let result be the return value of the function: result = os.path.join(work_dir, '.env_check_memory').

</details>

### `src--extract-py`

#### FMA-MISMATCH-058 — `src--extract-py--_extract_func_name_brace`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/extract-py/_extract_func_name_brace.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/extract-py/_extract_func_name_brace.json) · [具体 bug 报告](../fm_agent/bug_validation/src--extract-py--_extract_func_name_brace.md) · [probe](../fm_agent/bug_validation/probe_src--extract-py--_extract_func_name_brace.py)
- 触发/冲突：C++ operator, (comma) is not in the operator regex character class, causing operator, signatures to return None instead of 'operator,'
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- signature_text is a string containing one or more concatenated source lines forming a function signature in a brace-delimited language - lang_cfg is a language configuration entry with a "keywords" key whose value is a set of language reserved words
- FMA SPEC post-condition：- Returns the function name as a string when signature_text contains a recognized function-definition pattern and the identified name is not a language keyword; returns None otherwise - For languages that support operator overloading, an operator definition signature (e.g., one containing `operator()`, `operator[]`, or an operator symbol following the `operator` keyword) is recognized and the full operator token is returned as the function name - For other function-definition forms, returns the first non-keyword identifier that immediately precedes an opening parenthesis, after template angle-bracket content (i.e., text between `<` and matching `>`) has been removed from the signature text - The returned name does not include any tokens of lang_cfg[…
- FMA 推导 actual POST：The function returns a string containing the function name extracted from signature_text if one is found, otherwise None. The extraction proceeds as follows: (1) If signature_text contains a substring that matches the regular expression r'\b(operator\s*(?:\[\]|\(\)|[+\-*/%&|^~!=<>]+|new(?:\s*\[\s*\])?|delete(?:\s*\[\s*\])?))\s*\(', the matched operator string (e.g., 'operator+', 'operator new[]') is returned. (2) Otherwise, after applying _strip_angle_brackets to remove angle-bracket-delimited sections from signature_text, the function scans the cleaned text for substrings matching r'\b(\w+)\s*\(', i.e., word characters immediately followed by '(' (with possible whitespace). The first matched word that is not a member of lang_cfg['keywords'] is retu…

</details>

#### FMA-MISMATCH-059 — `src--extract-py--_extract_functions_indent`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/extract-py/_extract_functions_indent.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/extract-py/_extract_functions_indent.json) · [具体 bug 报告](../fm_agent/bug_validation/src--extract-py--_extract_functions_indent.md) · [probe](../fm_agent/bug_validation/probe_src--extract-py--_extract_functions_indent.py)
- 触发/冲突：Same-indentation header continuation line "b): return 42" not recognized because the regex only matches lines starting with ")" after stripping, missing valid continuations like "b):"
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- lines is a list of strings representing source code lines with trailing whitespace stripped - lang_cfg is a LANG_CONFIG entry whose body type is "indent"
- FMA SPEC post-condition：- Returns a list of (raw_name, start, end) tuples, ordered by ascending start index - Each tuple identifies one function definition found in lines: * raw_name is the function identifier extracted from the definition line * start is the zero-based index of the block's first line: either the definition line itself, or the earliest immediately-preceding decorator line when the definition line is preceded by one or more consecutive decorator lines * end is the zero-based index of the last non-blank line in the function body - The contiguous span lines[start..end] contains exactly one function definition header; every non-blank line in that span either belongs to the function body (indented more deeply than the definition header) or forms a continuation…
- FMA 推导 actual POST：Let `L` be the returned list. Then: 1. L is a list of triples (name, start, end) with 0 start end < len(lines). 2. For each (n, s, e) L, there exists an indentation level I and an index d [s, e] such that line d matches the regex `^\s*def\s+(\w+)\s*\(`, capturing I as len(leading whitespace) and n as the function name; all lines from s to d1 are decorators (start with '@'); s is the start of the contiguous decorator block; e is the last non-blank line within the function body; the body comprises lines after d with indentation > I or (indentation == I and matches `\)\s*(:|->)`), and breaks at the first non-blank line that has indentation I and does not match that continuation pattern; trailing blank lines are excluded from e. 3. The intervals in L ar…

</details>

#### FMA-MISMATCH-060 — `src--extract-py--_strip_angle_brackets`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/extract-py/_strip_angle_brackets.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/extract-py/_strip_angle_brackets.json) · [具体 bug 报告](../fm_agent/bug_validation/src--extract-py--_strip_angle_brackets.md) · [probe](../fm_agent/bug_validation/probe_src--extract-py--_strip_angle_brackets.py)
- 触发/冲突：Input '>' returns empty string instead of '>' because the code drops '>' at depth 0 instead of appending it to the result.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- text is a string
- FMA SPEC post-condition：- Returns text with all content enclosed within matching angle-bracket pairs removed - Angle-bracket pairs are matched using balanced counting: each '<' opens a new scope, each '>' closes the most recently opened scope - All characters between a matching '<' and '>' (the brackets themselves and everything between them) are omitted from the result - Characters not inside any matching pair appear in the result in their original relative order - A '>' with no preceding unmatched '<' is not inside any matching pair and appears in the result - If the input contains no '<' characters, every character in the input appears in the result in original order
- FMA 推导 actual POST：The returned string is the original string with all angle brackets '<' and '>' removed, and additionally all characters that appear inside any properly nested pair of angle brackets (including the brackets themselves and any nested content) are omitted. Formally, let s = text. Define depth(i) for i 1 as the net number of unclosed '<' after processing s[0..i-1] according to: depth(1) = 0; for each j from 1 to len(s): if s[j-1] == '<' then depth(j) = depth(j-1) + 1; else if s[j-1] == '>' and depth(j-1) > 0 then depth(j) = depth(j-1) - 1; else depth(j) = depth(j-1). Then the output string equals the concatenation of all characters s[k] for k from 0 to len(s)-1 such that depth(k) == 0 and s[k] '<' and s[k] '>'. Consequently, the returned string contains…

</details>

#### FMA-MISMATCH-223 — `src--extract-py--_extract_functions_brace`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/extract-py/_extract_functions_brace.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/extract-py/_extract_functions_brace.json) · [具体 bug 报告](../fm_agent/bug_validation/src--extract-py--_extract_functions_brace.md) · [probe](../fm_agent/bug_validation/probe_src--extract-py--_extract_functions_brace.py)
- 触发/冲突：Rust functions are correctly extracted when not annotated with #[test]; only test-attributed functions are intentionally skipped.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- lines is a list of strings representing source lines with line endings stripped - lang_key is a recognized language key - lang_cfg is the LANG_CONFIG entry for that language, with body type "brace"
- FMA SPEC post-condition：- Returns a list of (raw_name, start, end) tuples, one per top-level function definition detected in lines, ordered by first appearance in the source - Each tuple describes a contiguous span: start is the 0-based index of the first line of the function definition, end is the 0-based index of the last line of the function body (containing the matching closing brace of the body), satisfying 0 <= start <= end < len(lines) - A function definition is identified by a language-specific declarator pattern at the outermost nesting level, followed by a brace-delimited body - The raw_name is the unqualified function name as it appears in the source text - Returned spans are non-overlapping: no line index belongs to more than one span - Lines inside syntactical…
- FMA 推导 actual POST：After execution of the code block (lines 121173), the program state satisfies the following. This block is reached only from Path B2 of the preceding block (lines 81120), i.e., `lang_key == "rust"`, the `fn` regex match succeeded (`m` is not `None`), and `has_test_attr` is either `True` or `False`. The block unconditionally executes lines 121126, finding the opening brace and skipping the entire brace-delimited scope. Lines 127173 are dead code because line 126 always transfers control out of the block via `continue`. **Effects on variables:** - `functions` is unchanged: `functions = old(functions)`. - `has_test_attr` is unchanged: `has_test_attr = old(has_test_attr)`. - `sig_end` and `i` are updated according to whether an opening brace `{` is foun…

</details>

#### FMA-MISMATCH-224 — `src--extract-py--_find_brace_end`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/extract-py/_find_brace_end.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/extract-py/_find_brace_end.json) · [具体 bug 报告](../fm_agent/bug_validation/src--extract-py--_find_brace_end.md) · [probe](../fm_agent/bug_validation/probe_src--extract-py--_find_brace_end.py)
- 触发/冲突：Bug claim asserts a SyntaxError from break/continue outside loops prevents function execution, but the function imports and runs correctly with all break/continue inside enclosing loops.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- lines is a list of strings representing source code lines with line endings stripped - start_idx is a 0-based index into lines satisfying 0 <= start_idx < len(lines)
- FMA SPEC post-condition：- Returns the 0-based line index of the closing brace '}' that balances the first unmatched opening brace '{' encountered at or after start_idx - Only structural braces contribute to the brace-depth count: braces that appear inside string literals (delimited by '"'), character literals (delimited by "'"), line comments (from '//' to end of line), and block comments (delimited by '/*' and '*/') are excluded - Braces belonging to Go anonymous composite type expressions ('interface{...}' and 'struct{...}') are tracked as self-contained balanced pairs and do not affect the outer structural brace depth - If the structural depth never returns to zero after the first opening brace is found, returns len(lines) - 1 - The returned index satisfies start_idx <=…
- FMA 推导 actual POST：The code block never executes due to a compilation-time SyntaxError. The program state remains completely unmodified: for every variable v in any enclosing scope, its value after the attempt is equal to its value before (v = v). The function `_find_brace_end` is not defined, and no side effects (I/O, mutations, etc.) occur.

</details>

#### FMA-MISMATCH-225 — `src--extract-py--run_extraction`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/extract-py/run_extraction.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/extract-py/run_extraction.json) · [具体 bug 报告](../fm_agent/bug_validation/src--extract-py--run_extraction.md) · [probe](../fm_agent/bug_validation/probe_src--extract-py--run_extraction.py)
- 触发/冲突：Spec requires per-file subdirectories (e.g., util-py/) but code was claimed to use flat directory; code actually implements the per-file subdirectory pattern correctly.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a path to an existing directory - work_dir (or proj_dir if work_dir is None) contains a phases.json file whose structure includes a list of phases, each with modules containing source_files entries that are relative paths from proj_dir
- FMA SPEC post-condition：- A function is extracted from every source file listed in phases.json that (a) has a file extension recognized as a supported language, and (b) does not match test-file heuristics - Each extracted function is written as a separate file under work_dir/extracted_functions/; the output path is constructed by replacing the last dot in the source filename with a hyphen to form a directory, then placing the canonicalized function name with the original extension inside - An output file that already exists and contains both [SPEC] marker lines and [INFO] marker lines is left unchanged and counted as skipped, unless force is True - After all extractions complete, every function file in the output tree contains exactly one function body (validated) - Return…
- FMA 推导 actual POST：If the file `phases.json` does not exist at `work_dir/phases.json` (where `work_dir` defaults to `proj_dir` if `work_dir is None`), a `FileNotFoundError` is raised and no side effects occur. Otherwise, the function reads the JSON, extracts toplevel functions from the listed source files that are not test files and that exist, writes each function to an individual file under `work_dir/extracted_functions/`, validates the output, and returns a tuple `(written, skipped)`. More formally, let `W = work_dir if work_dir is not None else proj_dir`. Precondition: `os.path.exists(os.path.join(W, 'phases.json'))` is true. The phases JSON contains a `'phases'` list; for each phase, for each module, for each `source_files` entry (a relative path) we collect a fl…

</details>

### `src--file_utils-py`

#### FMA-MISMATCH-061 — `src--file_utils-py--_get_incomplete_verification_files`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/file_utils-py/_get_incomplete_verification_files.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/file_utils-py/_get_incomplete_verification_files.json) · [具体 bug 报告](../fm_agent/bug_validation/src--file_utils-py--_get_incomplete_verification_files.md) · [probe](../fm_agent/bug_validation/probe_src--file_utils-py--_get_incomplete_verification_files.py)
- 触发/冲突：A well-formed JSON file containing a non-mapping value (e.g. array) at the expected result path causes result.get("verdict") to raise an unhandled AttributeError.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- layer_files is an iterable of relative file paths (strings), each having a file extension. - output_dir is a directory path containing (or expected to contain) verification result JSON files. - work_dir is a directory path; its "bug_validation" subdirectory contains (or is expected to contain) bug validation result JSON files.
- FMA SPEC post-condition：- Returns a list that is a subsequence of layer_files, preserving the relative order of paths as they appear in layer_files. - A path is excluded from the result (considered "complete") when EITHER: 1. A readable, well-formed JSON file exists at the path formed by <output_dir>/<path_with_last_extension_replaced_by_.json>, and that JSON contains a "verdict" key whose value is any string other than "MISMATCH". OR 2. A readable, well-formed JSON file exists at that same output path, its "verdict" value is "MISMATCH", AND a readable, well-formed JSON file exists at <work_dir>/bug_validation/<bug_id>.result.json, where bug_id is derived from the relative path by stripping its file extension and replacing both the final dot and all path separators with "-…
- FMA 推导 actual POST：The function returns a list `incomplete` consisting of those relative file paths from `layer_files` for which either (1) the verification result file `os.path.join(output_dir, os.path.splitext(rel)[0] + '.json')` cannot be read successfully (any `OSError` or `json.JSONDecodeError` is raised when attempting to open and parse it), or (2) that file is read successfully and contains a JSON object with key `"verdict"` equal to `"MISMATCH"`, and the corresponding bug validation file `os.path.join(work_dir, 'bug_validation', (os.path.splitext(rel)[0].replace(os.sep, '--').replace('/', '--')) + '.result.json')` is not valid according to `_json_file_is_valid` (i.e., does not exist, is not readable, or is not well-formed JSON). The returned list preserves the…

</details>

#### FMA-MISMATCH-062 — `src--file_utils-py--_is_test_file`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/file_utils-py/_is_test_file.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/file_utils-py/_is_test_file.json) · [具体 bug 报告](../fm_agent/bug_validation/src--file_utils-py--_is_test_file.md) · [probe](../fm_agent/bug_validation/probe_src--file_utils-py--_is_test_file.py)
- 触发/冲突：When rel_path ends with a separator (e.g. "tests/"), split produces an empty last element, and parts[:-1] includes the directory name, causing True for a directory path that is not a file.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- rel_path is a non-empty string representing a relative file path
- FMA SPEC post-condition：- Returns True when rel_path identifies a file classified by the module as a test file - Returns False when rel_path is not classified as a test file - A path explicitly listed in the module-level test-file exemption set is never classified as a test file - A path is classified as a test file when any directory component (path segments excluding the filename) matches the module-level test-directory naming rules - A path is classified as a test file when its filename matches any of the module-level compiled test-filename regex patterns - Test-directory matching is case-insensitive; test-filename matching follows the compiled regex rules - The function normalizes platform path separators to forward slashes before classification
- FMA 推导 actual POST：The function returns a boolean with no side effects. Let norm = rel_path.replace('\\', '/'). If norm is in the set _TEST_FILE_EXEMPTIONS, the function returns False. Otherwise, let parts = norm.split('/'). If any part in parts[:-1] satisfies part.lower() in _TEST_DIR_NAMES, the function returns True. Else, let basename = parts[-1]. If there exists a pattern pat in _TEST_FILE_PATTERNS such that pat.match(basename) is not None (i.e., the pattern matches from the start of the basename), the function returns True. Otherwise, the function returns False. Formally: result = (norm _TEST_FILE_EXEMPTIONS) ( ( part parts[:-1] : part.lower() _TEST_DIR_NAMES) ( pat _TEST_FILE_PATTERNS : pat.match(parts[-1]) None) ) True, and False otherwise.

</details>

#### FMA-MISMATCH-063 — `src--file_utils-py--_is_under_submodules`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/file_utils-py/_is_under_submodules.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/file_utils-py/_is_under_submodules.json) · [具体 bug 报告](../fm_agent/bug_validation/src--file_utils-py--_is_under_submodules.md) · [probe](../fm_agent/bug_validation/probe_src--file_utils-py--_is_under_submodules.py)
- 触发/冲突：Path '././sub/file' with submodules ['sub'] — the while-loop strips both './' prefixes yielding 'sub/file' which matches, but the spec's single-strip gives './sub/file' which should not match.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- rel_path is a string representing a file or directory path - submodules is None, an empty iterable, or a non-empty iterable of subdirectory name strings, each not containing "/" or "\"
- FMA SPEC post-condition：- Returns True when submodules is None or empty, regardless of rel_path value - When submodules is non-empty: normalizes rel_path by replacing every backslash ("\\") with a forward slash ("/") and stripping any leading "./" prefix; returns True if the normalized path is exactly equal to any element of submodules OR if the normalized path begins with any element of submodules followed by "/", and False otherwise - The function performs no filesystem I/O and has no side effects
- FMA 推导 actual POST：The function returns True if and only if either 'submodules' is logically false (None or empty iterable), or after normalizing 'rel_path' by replacing every occurrence of '\' with '/' and then repeatedly stripping any leading './', the resulting normalized string is equal to a string in 'submodules' or starts with that string followed by '/'. Returns False otherwise. Neither 'rel_path' nor 'submodules' are modified.

</details>

#### FMA-MISMATCH-064 — `src--file_utils-py--_json_file_is_valid`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/file_utils-py/_json_file_is_valid.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/file_utils-py/_json_file_is_valid.json) · [具体 bug 报告](../fm_agent/bug_validation/src--file_utils-py--_json_file_is_valid.md) · [probe](../fm_agent/bug_validation/probe_src--file_utils-py--_json_file_is_valid.py)
- 触发/冲突：A file with invalid UTF-8 byte 0xFF causes UnicodeDecodeError to propagate because the except clause only catches OSError and json.JSONDecodeError.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- path is a string referencing a filesystem location.
- FMA SPEC post-condition：- Returns True if and only if the filesystem object at path is openable for reading and its content is well-formed JSON (parseable by the standard library JSON parser). - Returns False when the filesystem object at path does not exist, cannot be opened for reading, or its content is not well-formed JSON. - Does not raise exceptions to its caller and does not mutate any filesystem state.
- FMA 推导 actual POST：The function returns True if and only if the file at 'path' exists, is readable, and its entire content is a valid JSON document according to json.load; otherwise it returns False. The file is properly closed in all cases. No exceptions propagate. Formally: retval = (can_open_read(path) valid_json(content(file(path)))) ? True : False, where can_open_read succeeds iff open(path, 'r') does not raise OSError, and valid_json succeeds iff json.load does not raise json.JSONDecodeError.

</details>

#### FMA-MISMATCH-065 — `src--file_utils-py--_write_file_names`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/file_utils-py/_write_file_names.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/file_utils-py/_write_file_names.json) · [具体 bug 报告](../fm_agent/bug_validation/src--file_utils-py--_write_file_names.md) · [probe](../fm_agent/bug_validation/probe_src--file_utils-py--_write_file_names.py)
- 触发/冲突：_write_file_names unconditionally overwrites output_path even when it already contains a valid JSON array of strings, violating the spec requirement to return the existing parsed array without modification.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- file_names is a list of strings. - output_path is a writable filesystem path string.
- FMA SPEC post-condition：- If output_path already exists and contains a JSON-parsable array of strings, returns that parsed array without modifying the file. - Otherwise, serializes file_names as a JSON array to output_path and returns the serialized list. - The serialized array contains the elements of file_names sorted lexicographically with duplicates removed: each distinct string from file_names appears exactly once. - The write is atomic with respect to readers on the same filesystem: the content is first written to a temporary file, then renamed to output_path, so that no reader ever observes a partially written or truncated file at output_path. - The returned list has no ordering relationship to the original file_names beyond being the sorted, deduplicated sequence d…
- FMA 推导 actual POST：If the function returns normally, the returned value is a new list `result` that is the sorted, de-duplicated version of `file_names` (stable sort after removing duplicates, preserving the order of first occurrences). The file at `output_path` now exists and contains that list as a JSON array (with indentation 2, ensure_ascii=False). The prior file at `output_path`, if any, has been atomically replacedno partial or corrupted state is visible at `output_path`. No temporary file named `output_path + '.tmp'` remains. Formally: result = sorted(dict.fromkeys(file_names)) os.path.isfile(output_path) file_content(output_path) = json.dumps(result, indent=2, ensure_ascii=False) os.path.exists(output_path + '.tmp'). If an exception occurs during execution (e.…

</details>

#### FMA-MISMATCH-066 — `src--file_utils-py--collect_file_names`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/file_utils-py/collect_file_names.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/file_utils-py/collect_file_names.json) · [具体 bug 报告](../fm_agent/bug_validation/src--file_utils-py--collect_file_names.md) · [probe](../fm_agent/bug_validation/probe_src--file_utils-py--collect_file_names.py)
- 触发/冲突：collect_file_names unconditionally rescans input_dir via os.walk before checking the cache, violating the spec requirement that subsequent calls with a valid output_path return the cached list without re-scanning.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- input_dir references an existing directory on the filesystem - output_path is a writable path string (default: "file_list.json")
- FMA SPEC post-condition：- Returns a list where every element is the relative path from input_dir to a regular file located in input_dir or any of its descendant directories, using OS-native path separators - Every regular file in the input_dir tree corresponds to exactly one element in the returned list; no element appears more than once - The returned list is persisted at output_path as a JSON array of strings - For a given output_path, once the list is produced and written, subsequent calls with the same output_path return the identical list without re-scanning the directory
- FMA 推导 actual POST：If no exception occurs, the function returns a list of strings. Let L be the list of relative file paths obtained by recursively traversing input_dir via os.walk (order of discovery, no guarantee). Define P as the state of output_path before the call. Then: - If P exists and contains a valid JSON array A (a list of strings), the function returns A and output_path remains unchanged (P is not modified). - Otherwise, the function writes the JSON serialization of L to output_path (creating or overwriting it) and returns L. If an exception is raised during traversal or writing, the function terminates without a normal return; the state of output_path may be partially written (if the error happens during the write) or unchanged (if before any write). Form…

</details>

#### FMA-MISMATCH-226 — `src--file_utils-py--_has_source_code`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/file_utils-py/_has_source_code.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/file_utils-py/_has_source_code.json) · [具体 bug 报告](../fm_agent/bug_validation/src--file_utils-py--_has_source_code.md) · [probe](../fm_agent/bug_validation/probe_src--file_utils-py--_has_source_code.py)
- 触发/冲突：_has_source_code called with a non-existent proj_dir should return False per spec; the trigger condition speculated that os.walk would raise FileNotFoundError, but Python 3.12 silently handles non-existent directories and correctly returns False.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a directory path. - submodules is None or a non-empty list of subdirectory name strings.
- FMA SPEC post-condition：- Returns True when proj_dir (optionally scoped to submodules) contains at least one file whose extension matches a pipeline-supported programming language. - Returns False when no such file exists within the applicable scope, including when proj_dir does not exist, is empty, contains no recognized source files, or when submodules narrows the scope to a subset of the tree that contains no recognized source files. - When submodules is None, the search covers the entire directory tree under proj_dir, excluding directories whose names begin with "." and well-known build/package directories. - When submodules is provided and non-empty, only files whose project-relative path begins with one of the listed subdirectory names are considered.
- FMA 推导 actual POST：The function returns True if and only if the underlying iterator `_iter_project_source_files(proj_dir, submodules)` produces at least one path (i.e., a file with a pipeline-supported extension exists in the directory tree rooted at `proj_dir`, optionally confined to the submodules listed in `submodules`, excluding hidden directories and build/package directories). Otherwise it returns False. The call has no side effects. Formally: let S = { p | p is yielded by `_iter_project_source_files(proj_dir, submodules)` } ; then `_has_source_code(proj_dir, submodules)` = True S .

</details>

#### FMA-MISMATCH-254 — `src--file_utils-py--_iter_project_source_files`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/file_utils-py/_iter_project_source_files.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/file_utils-py/_iter_project_source_files.json) · [具体 bug 报告](../fm_agent/bug_validation/src--file_utils-py--_iter_project_source_files.md) · [probe](../fm_agent/bug_validation/probe_src--file_utils-py--_iter_project_source_files.py)
- 触发/冲突：推理器声称 `submodules=['nonexistent']` 会使 `os.walk` 抛出 `FileNotFoundError`，但恢复重跑生成的 probe 在 3 组变体上均得到空序列 `[]`，与 SPEC 一致。
- 成因复核：`os.walk(path)` 未传 `onerror` 时会忽略扫描目录时的 `OSError`；原 actual POST/code evidence 将不存在的扫描根误读为必然抛异常。这是新增的验证器评测样本，不是实现 bug。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is an existing directory path - submodules is None or a non-empty iterable of subdirectory name strings
- FMA SPEC post-condition：- Yields zero or more project-relative source-file paths using "/" as separator. - When submodules is provided, only qualifying files under the listed prefixes are yielded. - The function does not mutate filesystem state.
- FMA 推导 actual POST：对不存在的 scan root，原推导声称 `os.walk` 会抛出 `OSError` 并中止 generator；probe 实测否定了该 claim，返回空序列。

</details>

#### FMA-MISMATCH-255 — `src--file_utils-py--is_file_ready`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/file_utils-py/is_file_ready.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/file_utils-py/is_file_ready.json) · [具体 bug 报告](../fm_agent/bug_validation/src--file_utils-py--is_file_ready.md) · [probe](../fm_agent/bug_validation/probe_src--file_utils-py--is_file_ready.py)
- 触发/冲突：原推理声称标记行前有空白时，`fullmatch()` 会因为行首空白而失败；实际正则以 `^\s*` 开头，probe 对带缩进标记的文件实测返回 `True`。
- 成因复核：推理器只看到 `fullmatch(line)` 就忽略了 `_READY_MARKER_RE` 本身允许行首空白；这正是本分支修复 SPEC 匹配后用来回归的误报样本。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- file_path is a string that may reference an existing file or be any other string value
- FMA SPEC post-condition：- 文件仅在开头依次出现 `SPEC → SPEC → INFO → INFO`、四个标记使用同一语言注释前缀，且标记之间没有非注释内容时返回 `True`；行首空白可被接受。
- FMA 推导 actual POST：推导的总体逻辑其实已正确写出“`_READY_MARKER_RE` 匹配即消费下一标记”，但 code evidence 又错误断言带空白的标记无法 full-match，前后自相矛盾。

</details>

#### FMA-MISMATCH-227 — `src--file_utils-py--clear_test_file_exemptions`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/file_utils-py/clear_test_file_exemptions.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/file_utils-py/clear_test_file_exemptions.json) · [具体 bug 报告](../fm_agent/bug_validation/src--file_utils-py--clear_test_file_exemptions.md) · [probe](../fm_agent/bug_validation/probe_src--file_utils-py--clear_test_file_exemptions.py)
- 触发/冲突：Call clear_test_file_exemptions() after adding test file exemptions via add_test_file_exemption(); the set should be empty per spec but the reasoning engine claimed it would retain contents.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- The module-level set `_TEST_FILE_EXEMPTIONS` exists.
- FMA SPEC post-condition：- The module-level set of exempted test-file paths is empty. - All paths previously registered via `add_test_file_exemption` are no longer exempt; subsequent test-file classification functions will apply default heuristics to every path.
- FMA 推导 actual POST：The function `clear_test_file_exemptions` is bound in the module's global scope. The set `_TEST_FILE_EXEMPTIONS` exists and retains its previous contents; none of its elements have been added or removed. Formally: (clear_test_file_exemptions globals()) (_TEST_FILE_EXEMPTIONS globals()) (_TEST_FILE_EXEMPTIONS = old(_TEST_FILE_EXEMPTIONS)).

</details>

### `src--generate_batch_prompts-py`

#### FMA-MISMATCH-067 — `src--generate_batch_prompts-py--_detect_comment_prefix`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_batch_prompts-py/_detect_comment_prefix.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_batch_prompts-py/_detect_comment_prefix.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_batch_prompts-py--_detect_comment_prefix.md) · [probe](../fm_agent/bug_validation/probe_src--generate_batch_prompts-py--_detect_comment_prefix.py)
- 触发/冲突：When [SPEC] is preceded by arbitrary non-comment text (e.g. 'hello'), _detect_comment_prefix returns that text instead of None, violating the spec that the returned value must be a valid comment prefix (#, //, %, --).
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- content is a non-empty string containing source code text
- FMA SPEC post-condition：- If content contains at least one line in which the substring "[SPEC]" appears, returns the text preceding "[SPEC]" on the first such line (by ascending line order), with trailing whitespace removed from that prefix text - Otherwise, returns None - The returned value, when not None, is the single-line comment prefix used in the source file ("#" for Python, "//" for C-family languages, "%" for Erlang)
- FMA 推导 actual POST：The function returns the string obtained from the first line of `content` that contains the substring '[SPEC]', by extracting the part before '[SPEC]' and removing trailing whitespace, or `None` if no line contains '[SPEC]'. Formally: Let `lines = content.splitlines()`. If there exists an index `i` such that `lines[i].find('[SPEC]') != -1`, let `first = lines[i]` and `idx = first.find('[SPEC]')`; the function returns `first[:idx].rstrip()`. Otherwise, the function returns `None`.

</details>

#### FMA-MISMATCH-068 — `src--generate_batch_prompts-py--_info_line_mentions_name`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_batch_prompts-py/_info_line_mentions_name.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_batch_prompts-py/_info_line_mentions_name.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_batch_prompts-py--_info_line_mentions_name.md) · [probe](../fm_agent/bug_validation/probe_src--generate_batch_prompts-py--_info_line_mentions_name.py)
- 触发/冲突：When name ends with non-word character like '!',  fails between two non-word chars, returning False when True is required (demonstrated via extract_callee_spec_from_info with callee_fqn='some_func!' and first_line containing 'some_func! bar').
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- first_line is a string - name is a string
- FMA SPEC post-condition：- Returns False when name is empty - When name contains the substring "::", returns True if and only if name appears as a substring anywhere in first_line - When name does NOT contain "::", returns True if and only if name appears in first_line at a position not immediately preceded by an ASCII letter, digit, or underscore, and immediately followed by either an opening parenthesis (with optional whitespace between name and parenthesis) or a non-word-character position (including end-of-string) - The return value depends solely on first_line and name; the function is pure (no side effects) and deterministic
- FMA 推导 actual POST：The function returns a boolean value R. If name is an empty string, R is False. If name is non-empty and contains '::', R is True iff name is a substring of first_line. Otherwise (name non-empty and does not contain '::'), R is True iff the regular expression pattern formed by '(?<![A-Za-z0-9_])' + re.escape(name) + '(?:\s*\(|\b)' matches somewhere in first_line (i.e., re.search returns a Match object, not None). The function raises no exceptions and has no side effects. Formally: Let R = _info_line_mentions_name(first_line, name). Then: (name == "") (R == False) (name "" "::" in name) (R == (name in first_line)) (name "" "::" not in name) (R == (re.search(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?:\s*\(|\b)", first_line) is not None))

</details>

#### FMA-MISMATCH-069 — `src--generate_batch_prompts-py--detect_lang_and_comment`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_batch_prompts-py/detect_lang_and_comment.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_batch_prompts-py/detect_lang_and_comment.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_batch_prompts-py--detect_lang_and_comment.md) · [probe](../fm_agent/bug_validation/probe_src--generate_batch_prompts-py--detect_lang_and_comment.py)
- 触发/冲突：Path.suffix returns empty string for dotfiles like '.hidden', causing the function to classify them as 'unknown' instead of extracting the extension 'hidden' as the spec requires.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- file_rel is a string - ext_to_lang is a dict mapping file extension strings to language name strings
- FMA SPEC post-condition：- Returns a tuple (language_name, comment_prefix) of two strings - language_name is the value in ext_to_lang whose key matches file_rel's file extension (the substring after the last "." character, lowercased), if such a key exists; if file_rel has an extension but no matching key exists in ext_to_lang, language_name is the extension itself (lowercased); if file_rel has no extension (no "." character or "." is the last character), language_name is "unknown" - comment_prefix is the single-line comment marker bound to language_name by a fixed language-to-comment mapping; if language_name is absent from that mapping, comment_prefix defaults to "//"
- FMA 推导 actual POST：The function returns a tuple (lang, comment). Let ext = Path(file_rel).suffix.lstrip('.').lower(). Then lang = ext_to_lang.get(ext, ext if ext else 'unknown'). Then comment = COMMENT_PREFIX_BY_LANG.get(lang, '//'). No external state is modified, and no exceptions are raised. Formal logic: (ext = lowercase(strip_leading_dots(suffix(Path(file_rel))))) (lang = (ext_to_lang[ext] if ext dom(ext_to_lang) else (ext if ext '' else 'unknown'))) (comment = (COMMENT_PREFIX_BY_LANG[lang] if lang dom(COMMENT_PREFIX_BY_LANG) else '//')) (return_value = (lang, comment)).

</details>

#### FMA-MISMATCH-070 — `src--generate_batch_prompts-py--extract_callee_spec_from_info`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_batch_prompts-py/extract_callee_spec_from_info.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_batch_prompts-py/extract_callee_spec_from_info.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_batch_prompts-py--extract_callee_spec_from_info.md) · [probe](../fm_agent/bug_validation/probe_src--generate_batch_prompts-py--extract_callee_spec_from_info.py)
- 触发/冲突：When info_block uses a comment prefix directly followed by [SPLIT] without a space (e.g., '//[SPLIT]'), the hardcoded space in split_tag causes an incorrect delimiter, splitting fails, and the function returns the entire block instead of the first matching entry.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- info_block is a string containing zero or more callee entries, where each entry is a block of lines delimited by "[SPLIT]" markers; each entry begins with a signature line followed by Pre-condition and Post-condition lines - callee_fqn is a non-empty string representing a fully qualified function name - aliases is None or a sequence of alternative name strings for the same callee
- FMA SPEC post-condition：- If info_block contains a [SPLIT]-delimited entry whose first line mentions callee_fqn or any of the aliases (when compared with the comment prefix stripped from that line), returns the full text of that entry exactly as it appears in info_block; otherwise returns None - Entries whose content includes the literal string "(no callees)" are treated as non-matching regardless of other content - The comment prefix used for stripping is the text preceding a "[SPLIT]" marker within info_block itself, or the first whitespace-delimited token of the block's first non-empty line if no "[SPLIT]" marker is present - Within the first line of a candidate entry, the mention check succeeds if any of the search names (callee_fqn or alias) appears as a substring or…
- FMA 推导 actual POST：The function returns either `None` or a nonempty string. If the return value is a nonempty string, it is one of the entries obtained by splitting `info_block` on a delimiter `DELIM` that is determined as follows: let `PREFIX` be the substring before the first `[SPLIT]` in the first line of `info_block` that contains `[SPLIT]`, rightstripped; if no such line exists, let `PREFIX` be the first word of the first nonempty line (if that line matches `r'^(\S+)\s'`), otherwise `PREFIX` is empty; `DELIM` is `PREFIX + " [SPLIT]"` if `PREFIX` is nonempty, else `"[SPLIT]"`. The function returns the earliest such entry (in split order) whose stripped form is nonempty, does not contain the substring `"(no callees)"`, and whose first line (after removing the leadi…

</details>

#### FMA-MISMATCH-071 — `src--generate_batch_prompts-py--extract_info_block`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_batch_prompts-py/extract_info_block.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_batch_prompts-py/extract_info_block.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_batch_prompts-py--extract_info_block.md) · [probe](../fm_agent/bug_validation/probe_src--generate_batch_prompts-py--extract_info_block.py)
- 触发/冲突：When '# [INFO]' appears mid-line in source text before the first whole-line marker, content.find() selects the wrong boundary and returns incorrect text.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- filepath is a Path to an existing, readable regular file whose content is source code that may contain [INFO] annotation blocks
- FMA SPEC post-condition：- If the file content contains two or more lines matching "<prefix> [INFO]" where <prefix> is the single-line comment marker of the source language ("#", "//", or "%"), returns the text between the first such line and the second such line, exclusive of both marker lines, with leading and trailing whitespace removed - Returns None when the file content contains no recognized comment prefix, or contains fewer than two "<prefix> [INFO]" marker lines - File open/read errors (e.g., file not found, permission denied) propagate to the caller; Unicode decoding errors are replaced with the replacement character
- FMA 推导 actual POST：The function result satisfies: Let C = filepath.read_text(errors="replace") (no exceptions due to valid pre-condition). Let p = _detect_comment_prefix(C). If p is None, result is None. Else let tag = p + " [INFO]". Let i = C.find(tag). If i == -1, result is None. Else let j = C.find(tag, i + len(tag)). If j == -1, result is None. Else result = C[i + len(tag) + 1 : j].strip(). The function has no side effects on the file or its content.

</details>

#### FMA-MISMATCH-072 — `src--generate_batch_prompts-py--extract_spec_block`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_batch_prompts-py/extract_spec_block.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_batch_prompts-py/extract_spec_block.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_batch_prompts-py--extract_spec_block.md) · [probe](../fm_agent/bug_validation/probe_src--generate_batch_prompts-py--extract_spec_block.py)
- 触发/冲突：File whose first line starts with '// [SPEC]' but has extra characters (e.g. '// [SPEC]extra') followed by a closing '// [SPEC]' line is wrongly accepted instead of returning None.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- filepath is a Path to an existing, readable regular file whose content is source code that may begin with a [SPEC] annotation block
- FMA SPEC post-condition：- If the file content begins with the line "<prefix> [SPEC]" where <prefix> is the single-line comment marker of the source language ("#", "//", or "%") and contains a second "<prefix> [SPEC]" line after the first, returns the complete text from the start of the file through the closing "<prefix> [SPEC]" line inclusive, with surrounding whitespace stripped - Returns None when the file content contains no recognized comment prefix, or does not begin with a "<prefix> [SPEC]" line, or contains only one such line - File open/read errors (e.g., file not found, permission denied) propagate to the caller; Unicode decoding errors are replaced with the replacement character
- FMA 推导 actual POST：The function returns a non-None string if and only if the file content meets all of the following conditions: (1) _detect_comment_prefix(content) returns a non-None prefix p (i.e., the content contains at least one of the single-line comment starters '#', '//', or '%'); (2) the content begins with the string p + ' [SPEC]'; (3) the content contains at least two occurrences of that tag, with the second occurrence starting at an index >= len(tag) (i.e., content.find(p + ' [SPEC]', len(p + ' [SPEC]')) != -1). When all conditions hold, the returned value is content[0:end+len(tag)].strip(), where tag = p + ' [SPEC]' and end = content.find(tag, len(tag)). If any condition fails, the function returns None. No file-related exception is raised because the fil…

</details>

#### FMA-MISMATCH-073 — `src--generate_batch_prompts-py--list_staged_domain_knowledge_relpaths`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_batch_prompts-py/list_staged_domain_knowledge_relpaths.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_batch_prompts-py/list_staged_domain_knowledge_relpaths.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_batch_prompts-py--list_staged_domain_knowledge_relpaths.md) · [probe](../fm_agent/bug_validation/probe_src--generate_batch_prompts-py--list_staged_domain_knowledge_relpaths.py)
- 触发/冲突：Symlinks to regular .md files in the user_knowledge directory are incorrectly included because path.is_file() (and DirEntry.is_file()) resolve symlinks; the spec requires symlinks to be excluded.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- work_dir is a path-like object pointing to an existing workspace directory - prefix is a non-empty string used as the leading path segment for each returned path
- FMA SPEC post-condition：- If the directory <work_dir>/spec_prompts/domain_context/user_knowledge/ does not exist or is not a directory, returns an empty list - Otherwise, returns a lexicographically sorted list of strings - Each returned string has the form "<prefix_without_trailing_slash>/<relative_path>", where relative_path is the POSIX-style path of a regular file inside <work_dir>/spec_prompts/domain_context/user_knowledge/ (recursively), computed relative to work_dir - A file is included if and only if all of the following hold: a. It is a regular file (not a symlink or directory) b. Its filename is not "manifest.json" c. Its filename suffix (case-insensitive) is ".md" or ".markdown" - Returns an empty list when the directory exists but contains no files matching the…
- FMA 推导 actual POST：The function returns a sorted list of strings, each representing a staged domain knowledge relative path. If the directory `<work_dir>/spec_prompts/domain_context/user_knowledge` does not exist or is not a directory, the result is an empty list. Otherwise, for every regular file encountered by a recursive glob under that directory whose suffix (caseinsensitive) is `.md` or `.markdown` and whose name is not `manifest.json`, a string is formed by appending a `/` followed by the POSIXstyle relative path from `work_dir` to that file, with the prefix `prefix` stripped of any trailing slash. The returned list is sorted lexicographically. Formally, let `K = work_dir / 'spec_prompts' / 'domain_context' / 'user_knowledge'`. Then: - If `K.is_dir()` is False,…

</details>

#### FMA-MISMATCH-074 — `src--generate_batch_prompts-py--main`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_batch_prompts-py/main.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_batch_prompts-py/main.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_batch_prompts-py--main.md) · [probe](../fm_agent/bug_validation/probe_src--generate_batch_prompts-py--main.py)
- 触发/冲突：zip truncation in ext_to_lang construction when exts and languages differ in length silently drops extensions from the longer list
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- CLI arguments are parseable; args.batch_size is a positive integer - fm_agent/phases.json exists and is valid JSON with keys "project", "languages", "file_extensions" - fm_agent/spec_prompts/phase_NN_topdown_layers.json exists for args.phase and contains a "layers" key - args.layers specifies a range whose start and end are within [0, total_layers - 1] - Every function entry in the topdown JSON has a "file" path r…
- FMA SPEC post-condition：- Returns 0 on success; a ValueError is raised (and propagates) if batch_size 0 or the layer range is out of bounds - If args.dry_run is true: prints per-batch diagnostics to stdout and returns 0 without writing any files - If args.dry_run is false: - Creates output_dir (default: fm_agent/spec_prompts/batch_prompts_<project>_phaseNN/) - For each layer in the requested range, partitions layer functions into contiguous chunks of at most args.batch_size elements - Writes one batch prompt .txt file per chunk to output_dir; each file is named with the pattern batch_NNN_layerX_<tag>_bM.txt where <tag> is "cycle" for cycle-resolution layers and "extracted" otherwise, NNN is a global sequential batch index, X is the layer index, and M is the chunk index wit…
- FMA 推导 actual POST：After line 40, the program state satisfies: args holds the parsed CLI arguments with all attributes (phase, layers, batch_size, output_dir, dry_run, resume) and batch_size > 0. work_dir is the resolved absolute path of the 'fm_agent/' directory (parent of the script's grandparent). repo_root is work_dir.parent. fm_agent_prefix is str(work_dir.relative_to(repo_root)) + '/'. phases_json is the decoded JSON from work_dir/phases.json. project = phases_json['project']. languages = phases_json.get('languages', []). exts = phases_json.get('file_extensions', []). ext_to_lang = {ext.lower().lstrip('.'): lang for ext, lang in zip(exts, languages)}. topdown is the decoded JSON from work_dir/spec_prompts/phase_{args.phase:02d}_topdown_layers.json. layers = topd…

</details>

#### FMA-MISMATCH-075 — `src--generate_batch_prompts-py--phase_callee_info_names_key`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_batch_prompts-py/phase_callee_info_names_key.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_batch_prompts-py/phase_callee_info_names_key.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_batch_prompts-py--phase_callee_info_names_key.md) · [probe](../fm_agent/bug_validation/probe_src--generate_batch_prompts-py--phase_callee_info_names_key.py)
- 触发/冲突：Non-string dict key (int) before matching string key causes AttributeError on .endswith() call during iteration.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- func is a dictionary - phase is a non-negative integer
- FMA SPEC post-condition：- If func contains a key exactly equal to the string "phase<phase>_callee_info_names_by_caller" (where <phase> is the decimal representation of the phase argument), returns that exact key string - Otherwise, if func contains any key that starts with "phase" and ends with "_callee_info_names_by_caller", returns that key string - Otherwise, returns None - The return value is either a string that is an actual key present in func, or None
- FMA 推导 actual POST：The function returns either a string or None. Let target = f"phase{phase}_callee_info_names_by_caller". If target is a key in the dictionary func, the function returns target. Otherwise, it iterates over the keys of func in insertion order and returns the first key that starts with "phase" and ends with "_callee_info_names_by_caller". If no such key exists, it returns None. The dictionary func and integer phase are unchanged. Formally, define P(k) str(k).startswith("phase") str(k).endswith("_callee_info_names_by_caller"), T = "phase" + str(phase) + "_callee_info_names_by_caller". Then the return value r satisfies: (if T func.keys() then r = T) else (if k func.keys() such that P(k) then let K = [k for k in func.keys() if P(k)] in insertion order; r =…

</details>

#### FMA-MISMATCH-228 — `src--generate_batch_prompts-py--build_prompt`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_batch_prompts-py/build_prompt.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_batch_prompts-py/build_prompt.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_batch_prompts-py--build_prompt.md) · [probe](../fm_agent/bug_validation/probe_src--generate_batch_prompts-py--build_prompt.py)
- 触发/冲突：Build prompt with non-empty caller_expectations should miss the "CALLEE EXPECTATIONS FROM CALLERS" section header, but the code at line 303 of src/generate_batch_prompts.py already includes it.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- functions is a non-empty list of function entry dicts, each with at minimum a "name" key (FQN string) and a "file" key (relative path from fm_agent/) - all_funcs maps every FQN that appears as a caller among functions to its full function entry dict - fm_agent_prefix is a non-empty string ending with "/" - work_dir is an existing Path to the fm_agent/ workspace directory - ext_to_lang maps file extension strings (…
- FMA SPEC post-condition：- Returns a string that constitutes the complete batch prompt for the given set of functions - The prompt begins with a header line identifying the phase number and layer index - The language name and comment prefix in the header are derived from the first function's file extension via ext_to_lang; when functions is empty, "unknown" and "//" are used - The prompt references exactly these required reading files (each prepended with fm_agent_prefix): spec_prompts/system_prompt.md, spec_prompts/domain_context/engine_overview.txt, and spec_prompts/domain_context/phase_NN_types.txt where NN is the phase number zero-padded to two digits - If any staged user-provided domain knowledge files exist under fm_agent/spec_prompts/domain_context/user_knowledge/, t…
- FMA 推导 actual POST：Post-condition (natural language): After executing the code block, the list `lines` has been extended with: - For each function in `functions`, if there are corresponding entries in `caller_expectations` (extracted from earlier-layer callers), a header "### What callers expect from {fn_name}:" followed by each caller's name and expectation entry, and a blank line. - If `is_cycle` is true, a section "## CYCLE LAYER GUIDANCE" with guidance messages. - A section "## FUNCTIONS (N total ...)" listing each function with its index, file, and its earlier-layer callers. - A section "## SPEC FORMAT" providing the required [SPEC] and [INFO] format templates. - A section "## PROCESS" with step-by-step instructions. The function then returns the string formed by…

</details>

### `src--generate_topdown_layers-py`

#### FMA-MISMATCH-076 — `src--generate_topdown_layers-py--_add_resolved_extra_edge`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_topdown_layers-py/_add_resolved_extra_edge.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_topdown_layers-py/_add_resolved_extra_edge.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_topdown_layers-py--_add_resolved_extra_edge.md) · [probe](../fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_add_resolved_extra_edge.py)
- 触发/冲突：When callee_fqn is in phase_fqns but caller_fqn is not a key in callees_map, line 458 raises KeyError instead of returning a boolean as the specification requires.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- caller_fqn is a non-empty string (FQN of the calling function) - edge is a _ResolvedExtraEdge with a callee_fqn attribute of type string and an info_names attribute that is an iterable of strings - phase_fqns is a collection of FQN strings representing functions within the current phase - callees_map, callers_map, and all_callees_map are mutable dicts mapping FQN strings to mutable sets of FQN strings - edge_alias…
- FMA SPEC post-condition：- Returns True if and only if edge.callee_fqn was not a member of all_callees_map[caller_fqn] prior to the call - Returns False without modifying any map when caller_fqn equals edge.callee_fqn (self-edge) - After the call, edge.callee_fqn is a member of all_callees_map[caller_fqn] - After the call, every string from edge.info_names is a member of edge_aliases_map[edge.callee_fqn][caller_fqn] - If edge.callee_fqn is a member of phase_fqns, then edge.callee_fqn is added to callees_map[caller_fqn] and caller_fqn is added to callers_map[edge.callee_fqn] - If edge.callee_fqn is not a member of phase_fqns, neither callees_map nor callers_map is modified
- FMA 推导 actual POST：After execution, one of the following mutually exclusive scenarios holds, given the inputs and initial state (pre-state). Let P = (caller_fqn == edge.callee_fqn), S = (edge.callee_fqn in phase_fqns), K1 = (caller_fqn in callees_map), K2 = (edge.callee_fqn in callers_map), info = set(edge.info_names), and old_size = |all_callees_map_pre[caller_fqn]|. 1. If P is true: all data structures remain unchanged (equal to their pre-state values), and the function returns False. 2. If P is false: The sets all_callees_map[caller_fqn] and edge_aliases_map[edge.callee_fqn][caller_fqn] are always modified: all_callees_map_post[caller_fqn] = all_callees_map_pre[caller_fqn] {edge.callee_fqn} edge_aliases_map_post[edge.callee_fqn][caller_fqn] = edge_aliases_map_pre[e…

</details>

#### FMA-MISMATCH-077 — `src--generate_topdown_layers-py--_build_call_graph`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_topdown_layers-py/_build_call_graph.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_topdown_layers-py/_build_call_graph.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_topdown_layers-py--_build_call_graph.md) · [probe](../fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_build_call_graph.py)
- 触发/冲突：When codegraph resolves edges for a file, callee_fqns is computed from registry_edges before any file-open attempt; an unreadable file does not prevent codegraph-derived edges from being added.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- phase_files is a non-empty list of (filepath, module_name) tuples, where filepath is a path to an extracted function source file that exists and is readable, and module_name is a string from phases.json - proj_dir is the project root directory path - global_stem_to_fqns, if not None, is a dict mapping function-name stems to sets of FQN strings across all phases - extra_call_edges, if not None, is an iterable of Ca…
- FMA SPEC post-condition：- Returns a 6-tuple of dicts: (callees_map, callers_map, all_callees_map, file_map, module_map, edge_aliases_map), all keyed by FQN strings - callees_map[fqn]: set of FQNs called by fqn within the same phase; every callee FQN corresponds to an extracted function and is never equal to fqn - callers_map[fqn]: set of FQNs from the same phase that call fqn; every caller FQN is a member of the phase's FQN set - all_callees_map[fqn]: set of FQNs called by fqn across all phases a superset of callees_map[fqn]; when global_stem_to_fqns is None, this set contains only within-phase callees; when provided, it may include FQNs from other phases - file_map[fqn]: absolute path to the extracted function file for fqn - module_map[fqn]: module name string from phases…
- FMA 推导 actual POST：The function returns the tuple (callees_map, callers_map, all_callees_map, file_map, module_map, edge_aliases_map). No exceptions propagate out of the block; all OSError exceptions from file reading are caught and result in an empty text string or a `continue`. The input arguments are not mutated. - `file_map` and `module_map` satisfy the same properties as in the pre-condition: for each fqn in `fqn_map.values()`, `file_map[fqn]` is the corresponding filepath, `module_map[fqn]` is the module_name from `phase_files`. - `callees_map`, `callers_map`, `all_callees_map`, and `edge_aliases_map` are built from the processing of each `(filepath, module_name)` in `phase_files`. For each `(filepath, module_name)` in `phase_files`: Let `fqn = fqn_map[filepath]…

</details>

#### FMA-MISMATCH-078 — `src--generate_topdown_layers-py--_collect_phase_files`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_topdown_layers-py/_collect_phase_files.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_topdown_layers-py/_collect_phase_files.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_topdown_layers-py--_collect_phase_files.md) · [probe](../fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_collect_phase_files.py)
- 触发/冲突：The condition `last_dot > 0` skips '.' to '-' replacement when a source file basename has a leading dot (e.g., .hiddenfile), causing the function to look in extracted_functions/.hiddenfile instead of extracted_functions/-hiddenfile and miss files.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a path to an existing directory - phase_data is a dict that may contain a "modules" key; if present, its value is an iterable of module dicts, each with a "name" (str) and optionally "source_files" (iterable of str relative paths)
- FMA SPEC post-condition：- Returns a list of (file_path, module_name) pairs, where module_name is the "name" of a module in phase_data - For each source file declared in a module: the source file's basename extension is stripped by replacing the last "." with "-" (e.g., "loader.cpp" "loader-cpp"), and the resulting directory name is resolved under proj_dir/extracted_functions/ alongside the source file's parent directory - Every regular file found in such a directory is collected into the result, each paired with the name of the module that declared the source file - Directories that do not exist on disk are skipped with no error raised - Returns an empty list when phase_data has no "modules" key, the modules list is empty, or no extracted-function directories exist on disk…
- FMA 推导 actual POST：The function returns a list `results` with no side effects. For every module dictionary `mod` in `phase_data.get('modules', [])` (in iteration order), let `mn = mod['name']`. For every source file path `sf` in `mod.get('source_files', [])` (in iteration order), compute: `base = os.path.basename(sf)`; `last_dot = base.rfind('.')`; `dir_name = base[:last_dot] + '-' + base[last_dot+1:]` if `last_dot > 0` else `base`; `func_dir = os.path.join(proj_dir, 'extracted_functions', os.path.dirname(sf), dir_name)` if `os.path.dirname(sf)` else `os.path.join(proj_dir, 'extracted_functions', dir_name)`. If `os.path.isdir(func_dir)` evaluates to `True`, then for every filename `fn` in the arbitrary order returned by `os.listdir(func_dir)`, if `os.path.isfile(os.pa…

</details>

#### FMA-MISMATCH-079 — `src--generate_topdown_layers-py--_compute_layers`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_topdown_layers-py/_compute_layers.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_topdown_layers-py/_compute_layers.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_topdown_layers-py--_compute_layers.md) · [probe](../fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_compute_layers.py)
- 触发/冲突：Kahn's algorithm uses callers_map to decide readiness, producing layer(caller) < layer(callee); spec requires callee layer <= caller layer.
- 成因复核：同一 SPEC 内部冲突：一条要求 callee 层号 <= caller，末条却说按 callers 已分配后入层；源码/函数注释采用 caller-first。错误的层序不变量还污染了下游 [INFO]。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- phase_fqns is a non-empty iterable of unique, hashable function identifiers (FQNs) - callees_map maps each FQN to an iterable of FQNs it calls (may be empty); referenced callee FQNs that belong to this phase must be members of phase_fqns - callers_map maps each FQN to an iterable of FQNs that call it (may be empty); referenced caller FQNs that belong to this phase must be members of phase_fqns
- FMA SPEC post-condition：- Returns a list of layer dicts, sorted by ascending "layer" (0-indexed integer) - Each layer dict contains: "layer" (int), "functions" (list of FQNs in lexicographic order), and "cycle_resolution" (bool) - Every FQN in phase_fqns appears in exactly one layer's "functions" list - For every directed edge (caller callee) where both endpoints are in phase_fqns: the callee's layer index is less than or equal to the caller's layer index - Equality (callee and caller in the same layer) occurs only when the two functions belong to the same strongly connected component (mutual recursion), and the layer is marked with "cycle_resolution": true - "cycle_resolution" is true when the layer contains at least one SCC with two or more members; it is false when all…
- FMA 推导 actual POST：After execution, the function returns the list `layers`. The inputs `phase_fqns`, `callees_map`, and `callers_map` are not mutated. No exceptions are raised. Let `Phase` = set(phase_fqns), `C` = callees_map, and let `G` be the directed graph with vertices `Phase` and edge (u v) if v C.get(u, []). Then: 1. `layers` is a list of dictionaries, each with keys 'layer' (int), 'functions' (list of strings sorted lexicographically), and 'cycle_resolution' (bool). 2. For i from 0 to |layers|-1: layers[i]['layer'] == i. 3. The sets { f for l in layers for f in l['functions'] } form a partition of `Phase`: every FQN in `Phase` appears in exactly one layer's 'functions' list. 4. For any distinct a, b Phase, if b C.get(a, []) then let l_a, l_b be the indices of…

</details>

#### FMA-MISMATCH-080 — `src--generate_topdown_layers-py--_file_to_fqn`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_topdown_layers-py/_file_to_fqn.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_topdown_layers-py/_file_to_fqn.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_topdown_layers-py--_file_to_fqn.md) · [probe](../fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_file_to_fqn.py)
- 触发/冲突：When a directory component in the extracted function filepath contains '::' (e.g. 'src::engine'), Path(stem).parts produces a segment with the embedded '::', violating the spec requirement that each FQN segment must not contain '::'.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- filepath is an absolute or relative path to an extracted function file that resides under the directory <proj_dir>/extracted_functions/ - proj_dir is the project root directory path - The extracted function file has a filename that includes a file extension (e.g., .py, .cpp, .rs)
- FMA SPEC post-condition：- Returns the Fully-Qualified Name (FQN) derived from filepath by: taking the path relative to <proj_dir>/extracted_functions/, stripping the file extension to obtain the stem, and joining all directory components together with the stem using "::" as the separator - The returned FQN consists of one or more "::"-separated segments where the final segment is the filename stem and preceding segments are the directory components below extracted_functions/ - Each segment in the returned FQN is a non-empty string containing no "::" substrings - The return value is deterministic for a given (filepath, proj_dir) pair
- FMA 推导 actual POST：The function returns a fully qualified name (FQN) string constructed from the relative path of `filepath` with respect to `<proj_dir>/extracted_functions`. The file extension of the final component is removed, and all directory separators are replaced by '::'. No exceptions are raised; the return value is deterministic given the inputs. Formal logic: Let `extracted_base = os.path.join(proj_dir, "extracted_functions")`. Let `rel = os.path.relpath(filepath, extracted_base)`. Let `(stem, _) = os.path.splitext(rel)`. Then the return value `result = "::".join(Path(stem).parts)`.

</details>

#### FMA-MISMATCH-081 — `src--generate_topdown_layers-py--_get_call_regex`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_topdown_layers-py/_get_call_regex.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_topdown_layers-py/_get_call_regex.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_topdown_layers-py--_get_call_regex.md) · [probe](../fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_get_call_regex.py)
- 触发/冲突：The regex uses [^>]* to skip angle-bracket template arguments, which fails on nested templates (e.g., foo<bar<int>>(x)) valid in C++, Java, and similar languages.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- lang_key is a string identifying a programming language recognized by the system
- FMA SPEC post-condition：- Returns a compiled regular expression pattern object whose matches identify bare-name function-call sites in source code written in the language identified by lang_key - Capture group 1 of every match yields the identifier string (function name) that appears immediately before the opening parenthesis of a call - The pattern skips language-specific syntax that may appear between the identifier and the opening parenthesis: * For C, C++, Java, TypeScript, JavaScript, CUDA, and ArkTS: skips an optional angle-bracket-enclosed segment (<...>) representing template or generic arguments * For Rust: skips an optional turbofish segment (::<...>) representing generic type arguments * For Go: skips an optional bracket-enclosed segment ([...]) representing typ…
- FMA 推导 actual POST：The function returns a compiled regular expression Pattern object. The pattern depends on lang_key: - If lang_key {'cpp','c','java','typescript','javascript','cuda','arkts'}: pattern = r'\b(\w+)\s*(?:<[^>]*>)?\s*\(' - If lang_key = 'rust': pattern = r'\b(\w+)\s*(?:::<[^>]*>)?\s*\(' - If lang_key = 'go': pattern = r'\b(\w+)\s*(?:\[[^\]]*\])?\s*\(' - Otherwise: pattern = r'\b(\w+)\s*\(' Formally: result = _get_call_regex(lang_key) result is a Pattern with result.pattern equal to the string defined above for the given lang_key, and result behaves as described by re.compile.

</details>

#### FMA-MISMATCH-082 — `src--generate_topdown_layers-py--_get_keywords_for_lang`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_topdown_layers-py/_get_keywords_for_lang.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_topdown_layers-py/_get_keywords_for_lang.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_topdown_layers-py--_get_keywords_for_lang.md) · [probe](../fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_get_keywords_for_lang.py)
- 触发/冲突：The function returns empty set when both _COMMON_EXTRA_KEYWORDS and language-specific keywords are empty, violating the spec's non-empty guarantee.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- lang_key is a string identifying a source language
- FMA SPEC post-condition：- Returns a non-empty set of strings, where each string is a keyword that must be excluded from call-site detection for the given lang_key - The returned set is the union of: (a) the language-specific reserved keywords defined for lang_key, and (b) a fixed cross-language set of additional keywords that are excluded from call-site detection in every language - If no language-specific keyword set is defined for lang_key, only the cross-language set is returned - The returned set does not depend on the caller or on any mutable state outside the function
- FMA 推导 actual POST：The function returns a set containing all keywords for the given language merged with a global set of additional keywords. Specifically, if lang_key is a key in LANG_CONFIG and its value is a dictionary that contains a 'keywords' key, then the returned set is the union of that 'keywords' set and the global _COMMON_EXTRA_KEYWORDS. Otherwise, the returned set is simply a copy of _COMMON_EXTRA_KEYWORDS. No side-effects occur. Formally: result = (LANG_CONFIG.get(lang_key, {}).get('keywords', set())) _COMMON_EXTRA_KEYWORDS.

</details>

#### FMA-MISMATCH-083 — `src--generate_topdown_layers-py--_load_phases`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_topdown_layers-py/_load_phases.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_topdown_layers-py/_load_phases.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_topdown_layers-py--_load_phases.md) · [probe](../fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_load_phases.py)
- 触发/冲突：When phases.json contains valid but structurally non-conforming JSON (e.g. {}), _load_phases returns the raw parsed object without validating that it contains the required "phases" key.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string representing a directory path - os.path.join(proj_dir, "phases.json") resolves to a regular file whose content is valid JSON
- FMA SPEC post-condition：- Returns the Python object obtained by parsing the JSON content of os.path.join(proj_dir, "phases.json") - The returned object is a dict that contains the key "phases" mapping to a list - Each element of the "phases" list is a dict with integer "phase" and string "name" keys
- FMA 推导 actual POST：The function returns the Python object obtained by parsing the contents of the file at the path `os.path.join(proj_dir, 'phases.json')` as JSON. The file is closed after the read. The value of `proj_dir` remains unchanged, and no global or persistent state is modified. Under the given pre-condition, no exception is raised. Formal: Let `phases_path = os.path.join(proj_dir, 'phases.json')`. Then `\result = json.load(open(phases_path, 'r').read())` and the file handle for `phases_path` is closed. All other aspects of the program state are identical to the pre-state.

</details>

#### FMA-MISMATCH-084 — `src--generate_topdown_layers-py--_resolve_extra_call_edges`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_topdown_layers-py/_resolve_extra_call_edges.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_topdown_layers-py/_resolve_extra_call_edges.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_topdown_layers-py--_resolve_extra_call_edges.md) · [probe](../fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_resolve_extra_call_edges.py)
- 触发/冲突：Truthiness check on edge.caller.fqn skips falsy values (e.g. empty string) even when they are valid members of phase_fqns.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- extra_call_edges is None or an iterable of CallEdge objects, each carrying a caller (with optional fqn string and callsite_names iterable of strings) and a callee (with fqn string and optional info_names iterable of strings) - phase_fqns is an iterable of FQN strings belonging to the current phase - known_fqns is an iterable of all FQN strings across all phases
- FMA SPEC post-condition：- Returns (by_caller_fqn, by_callsite): two dict-like mappings that return an empty list for any key not explicitly present - by_caller_fqn: maps each caller FQN (from edge.caller.fqn) to a list of resolved-edge objects; a caller FQN appears as a key iff it is a member of phase_fqns AND at least one supplied edge whose callee.fqn is a member of known_fqns carries that exact caller FQN - by_callsite: maps each callsite name string to a list of resolved-edge objects; a callsite name appears as a key iff it is a valid source-code identifier (begins with an ASCII letter or underscore, followed by zero or more ASCII alphanumeric characters or underscores) AND at least one supplied edge whose callee.fqn is a member of known_fqns lists that callsite in edg…
- FMA 推导 actual POST：If `extra_call_edges` is None or empty, the function returns a tuple of two empty `defaultdict(list)` objects. Otherwise, let P = set(phase_fqns) and K = set(known_fqns). For each edge e in extra_call_edges, if e.callee.fqn K, a _ResolvedExtraEdge r is created with callee_fqn = e.callee.fqn, info_names = tuple(e.callee.info_names), source = e.source. Then, if e.caller.fqn is truthy and e.caller.fqn P, r is appended to by_caller_fqn[e.caller.fqn]; otherwise a debug log message is emitted. For each callsite c in e.caller.callsite_names, if re.fullmatch(r"[A-Za-z_]\w*", c) succeeds, r is appended to by_callsite[c]; otherwise a warning log message is emitted. If e.callee.fqn K, a warning log message is emitted and the edge contributes no entries. The re…

</details>

#### FMA-MISMATCH-085 — `src--generate_topdown_layers-py--_tarjan_scc`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_topdown_layers-py/_tarjan_scc.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_topdown_layers-py/_tarjan_scc.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_topdown_layers-py--_tarjan_scc.md) · [probe](../fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_tarjan_scc.py)
- 触发/冲突：Tarjan's SCC returns reverse topological order (sinks first, i > j for edge i→j), but the [SPEC] claims i ≤ j — a simple 1→2 DAG returns [{2},{1}] where edge 1→2 gives i=1, j=0 violating i ≤ j.
- 成因复核：源码 docstring 明确返回 reverse topological order；SPEC 把方向写反，probe 证明的只是 SPEC 与文档不一致。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- nodes is an iterable of hashable, equality-comparable node identifiers - edges is a mapping from each node to an iterable of successor nodes (outgoing directed edges); successor nodes that are not members of the iterable nodes are permitted — they are visited but do not contribute SCCs to the result beyond their role as intermediate targets
- FMA SPEC post-condition：- Returns a list of sets, each set representing one strongly connected component (SCC); the list is ordered in reverse topological order: for any directed edge from a node in SCC at position i to a node in SCC at position j, i j (no edge goes from a later SCC in the list to an earlier SCC) - Every node in nodes appears in exactly one SCC in the result - Each returned SCC is a maximal strongly connected subgraph restricted to nodes: for every ordered pair of distinct nodes (u, v) in the same SCC, there exists a directed path u ... v using only nodes from nodes as intermediate vertices, and no proper superset containing that SCC satisfies this property while also being a subset of nodes - A node that cannot reach any other node in nodes that can also…
- FMA 推导 actual POST：Let V be the set of nodes that are assigned an index in index_map during the traversal, and E = { (u, v) | u V, v edges.get(u, set()) if u is a key in edges else set() } (V V). The function returns a list result = [S_0, ..., S_{k-1}] where each S_i V, the S_i are pairwise disjoint and cover V, each S_i is a strongly connected component (maximal set with mutual reachability via paths in (V,E)), and for all i j, if u S_i, v S_j with a directed edge from u to v, then i > j (reverse topological order). No side effects persist outside the function; local variables (index_counter, scc_stack, on_stack, index_map, lowlink, call_stack) are discarded.

</details>

#### FMA-MISMATCH-229 — `src--generate_topdown_layers-py--_detect_lang_from_ext`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_topdown_layers-py/_detect_lang_from_ext.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_topdown_layers-py/_detect_lang_from_ext.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_topdown_layers-py--_detect_lang_from_ext.md) · [probe](../fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_detect_lang_from_ext.py)
- 触发/冲突：The code strips the leading dot from extensions (e.g., 'py' not '.py'). The bug would manifest if EXT_TO_LANG had dotted keys, but currently all 18 keys are dotless, so the function works correctly.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- filepath is a non-empty string representing a filesystem path with a file extension (i.e., the final path component contains at least one "." separating a stem from an extension)
- FMA SPEC post-condition：- Returns the programming language key string associated with the file's extension in the global language-to-extension mapping; the returned key is one of the language identifiers recognized by the FM-Agent pipeline - Returns None if and only if the file's extension is not present in the language-to-extension mapping
- FMA 推导 actual POST：The function returns the value from the global dictionary EXT_TO_LANG corresponding to the file's extension if the extension is a key in EXT_TO_LANG; otherwise returns None. The extension is the substring after the last '.' in the basename of filepath. Formally, let base = os.path.basename(filepath) and ext = base.rsplit('.', 1)[-1] (the pre-condition ensures '.' exists in base and ext is nonempty). Then the return value is EXT_TO_LANG[ext] if ext dom(EXT_TO_LANG) else None.

</details>

#### FMA-MISMATCH-230 — `src--generate_topdown_layers-py--_find_call_sites`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_topdown_layers-py/_find_call_sites.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_topdown_layers-py/_find_call_sites.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_topdown_layers-py--_find_call_sites.md) · [probe](../fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_find_call_sites.py)
- 触发/冲突：Code only strips comments but not string literals, potentially capturing identifiers inside strings — not confirmed; _strip_comments_from_source actually masks both comments and string literals with spaces.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- text is a string containing source code text - lang_key is a recognized language key string - known_stems is a non-empty set of function-name stem strings - keywords is a set of keyword strings to exclude from results
- FMA SPEC post-condition：- Returns the subset of known_stems that appear as bare-name call sites in text, excluding any identifier that is also in keywords - An identifier in known_stems is included in the result if and only if it appears as a call site in the source text after comment removal AND is not in the keywords set - Identifiers within comment regions (delimited per the lang_key language's comment syntax) are not treated as call sites - Identifiers within string or character literal contexts for the given language are not treated as call sites - The returned set is always a subset of known_stems and is disjoint from keywords - The return value is deterministic for a given (text, lang_key, known_stems, keywords) input
- FMA 推导 actual POST：The function `_find_call_sites` returns a set `found` such that `found` is the intersection of (i) all identifiers captured by group 1 of the regex pattern returned by `_get_call_regex(lang_key)` when applied to the comment-stripped text `_strip_comments_from_source(text, lang_key)`, (ii) the set `known_stems`, and then excludes all elements in `keywords`. Formally, let cleaned = _strip_comments_from_source(text, lang_key) and let re = _get_call_regex(lang_key); define M = { m.group(1) for m in re.finditer(cleaned) }. Then found = (M known_stems) \ keywords. Moreover, found known_stems and found keywords = . The input arguments are not modified.

</details>

#### FMA-MISMATCH-231 — `src--generate_topdown_layers-py--_strip_comments_from_source`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_topdown_layers-py/_strip_comments_from_source.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_topdown_layers-py/_strip_comments_from_source.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_topdown_layers-py--_strip_comments_from_source.md) · [probe](../fm_agent/bug_validation/probe_src--generate_topdown_layers-py--_strip_comments_from_source.py)
- 触发/冲突：The spec requires string-literal characters to be masked with spaces; the code correctly does this — the reported gap describes behavior the code does not exhibit.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- text is a string containing source code, which may be empty - lang_key is a string identifying a programming language
- FMA SPEC post-condition：- Returns a string of the same length as text - Every character position that lies within a comment region in the input is replaced with a space character (' ') in the output, where a comment region is defined according to the language-specific comment syntax: * When the language configuration for lang_key has comment_prefix "#": a comment region spans from a '#' character (that is not inside a string literal) to the end of the same line * When the language configuration for lang_key has comment_prefix "//": a line-comment region spans from "//" to end of line; a block-comment region spans from "/*" to the next "*/" (non-nesting) * When lang_key is not found in the language configuration, "//" comment syntax is assumed - Every character position tha…
- FMA 推导 actual POST：The function returns a string `out` such that |out| == |text| and for every index i (0 i < |text|), out[i] = ' ' if position i lies inside a comment region (as defined by the language configuration for `lang_key`, defaulting to `//` line comments, with correct handling of block comments when configured) and is **not** inside a string literal; otherwise out[i] = text[i]. String literals are recognised by singlequote (`'`), doublequote (`"`), or triplequote (`'''` or `"""`) delimiters, with backslash escaping treated properly so that any commentlike sequence inside a literal is ignored. The original arguments `text` and `lang_key` are not mutated. Formally, let `InComment(i, text, lang_key)` be true iff character `i` belongs to a comment according to…

</details>

#### FMA-MISMATCH-232 — `src--generate_topdown_layers-py--generate_topdown_layers`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/generate_topdown_layers-py/generate_topdown_layers.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/generate_topdown_layers-py/generate_topdown_layers.json) · [具体 bug 报告](../fm_agent/bug_validation/src--generate_topdown_layers-py--generate_topdown_layers.md) · [probe](../fm_agent/bug_validation/probe_src--generate_topdown_layers-py--generate_topdown_layers.py)
- 触发/冲突：The claim that the function returns after processing a single phase is false; return output_files is outside the for loop (line 756), and the function correctly iterates all 6 phases, returning 6 output paths.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a valid directory containing fm_agent/phases.json with at minimum the key "phases" (a list of phase objects) and optionally other phase metadata - Each phase in phases.json must have integer "phase" and string "name" keys - Extracted function files exist under fm_agent/extracted_functions/ for at least one phase; each filename encodes a function name - If phase_numbers is provided, every element is a v…
- FMA SPEC post-condition：- For every phase in phases.json whose phase number matches the phase_numbers filter (or for all phases if phase_numbers is None), writes one file fm_agent/spec_prompts/phase_NN_topdown_layers.json where NN is the zero-padded phase number - Each output JSON contains the phase number, phase name, total number of functions within the phase (total_functions), total number of topological layers (total_layers), and a "layers" list of layer objects sorted by ascending layer index - Each layer object has a "layer" key (0-indexed integer); if the layer resolves a strongly connected component (mutual recursion), it also contains "cycle_resolution": true - Within each layer, "functions" is a list of entries, each with: "name" (FQN), "file" (relative path from…
- FMA 推导 actual POST：The function terminates by returning the list `output_files`. This list contains exactly one element: `out_path` = os.path.join(output_dir, f"phase_{phase_num:02d}_topdown_layers.json"). The file at `out_path` exists and contains a valid JSON object, which was written with json.dump using indent=2 and ensure_ascii=False. The JSON object has the following structure and values: - "phase": the integer phase_num (equal to phase_info['phase']). - "phase_name": the string phase_name (equal to phase_info['name']). - "total_functions": len(phase_fqns), where phase_fqns = set(file_map.keys()) from the 6-tuple returned by _build_call_graph for this phase. - "total_layers": len(layers), where layers is the result of _compute_layers(phase_fqns, callees_map, cal…

</details>

### `src--git-py`

#### FMA-MISMATCH-086 — `src--git-py--_get_head_commit`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/git-py/_get_head_commit.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/git-py/_get_head_commit.json) · [具体 bug 报告](../fm_agent/bug_validation/src--git-py--_get_head_commit.md) · [probe](../fm_agent/bug_validation/probe_src--git-py--_get_head_commit.py)
- 触发/冲突：When git is not found on PATH, subprocess.run raises FileNotFoundError which _get_head_commit does not catch (only catches CalledProcessError), causing the exception to propagate instead of returning None as the spec requires.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string representing a filesystem path.
- FMA SPEC post-condition：- If proj_dir refers to a git repository whose HEAD commit is resolvable, returns the full SHA-1 hash of HEAD as a non-empty stripped string. - If proj_dir is not a git repository or does not have a resolvable HEAD commit, returns None. - The function does not raise exceptions to its callers; all failures are expressed via a None return.
- FMA 推导 actual POST：Natural language: The function `_get_head_commit` takes a string `proj_dir` and, if it returns normally, returns either a string representing the latest Git commit ID (the stripped stdout of `git rev-parse HEAD` executed in `proj_dir`) or `None`. When `proj_dir` is a valid Git repository, the function returns that commit string and no additional side effect occurs. When `proj_dir` is not a Git repository (i.e., `git rev-parse` fails with a `CalledProcessError`), the function logs an info message containing `proj_dir` and returns `None`. If an unexpected exception (e.g., missing `git`) is raised, the function propagates the exception and does not return. The passed `proj_dir` remains unchanged. Formal logic: Let R be the return value of the function…

</details>

#### FMA-MISMATCH-087 — `src--git-py--_git`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/git-py/_git.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/git-py/_git.json) · [具体 bug 报告](../fm_agent/bug_validation/src--git-py--_git.md) · [probe](../fm_agent/bug_validation/probe_src--git-py--_git.py)
- 触发/冲突：_git passes a list (not a string) to subprocess.run with check=True, so CalledProcessError.cmd is a list rather than the single command string the spec claims.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is bound in the enclosing lexical scope to a string path - args consists of individual string tokens forming a valid git subcommand and its arguments - kwargs may contain keyword arguments forwarded to the subprocess execution
- FMA SPEC post-condition：- Returns the stdout output of the executed git subcommand with leading and trailing whitespace characters removed - The git subcommand is executed with proj_dir as the effective working directory - If the git subcommand exits with a non-zero status, subprocess.CalledProcessError is raised; the exception carries the command string, the non-zero exit code, and the captured stdout and stderr
- FMA 推导 actual POST：After executing the code block, one of the following holds: (1) The function `_git` returns normally, in which case the return value is the stripped standard output string (`stdout.strip()`) of the git subprocess run with the command line `['git', '-C', proj_dir] + args`, using `check=True`, `capture_output=True`, `text=True`, and any additional keyword arguments from `kwargs`. The git process has been executed inside the directory `proj_dir`, potentially modifying the file system and the Git repository state according to the semantics of the git subcommand composed by `args`. (2) The git subprocess terminates with a non-zero exit code, which causes `subprocess.run` to raise a `CalledProcessError` exception; the function does not return a value, and…

</details>

#### FMA-MISMATCH-088 — `src--git-py--_is_git_repo`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/git-py/_is_git_repo.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/git-py/_is_git_repo.json) · [具体 bug 报告](../fm_agent/bug_validation/src--git-py--_is_git_repo.md) · [probe](../fm_agent/bug_validation/probe_src--git-py--_is_git_repo.py)
- 触发/冲突：git not in PATH causes subprocess.run to raise FileNotFoundError, which is not caught by the narrow except subprocess.CalledProcessError clause, violating the spec that the function never raises exceptions.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string representing a filesystem path.
- FMA SPEC post-condition：- Returns True if and only if proj_dir is a git repository with a resolvable HEAD commit (the directory is recognized by git as a repository and contains at least one commit). - Returns False if proj_dir is not a git repository or is a git repository with no commits. - The function does not raise exceptions to its callers; all outcomes are expressed via the boolean return value.
- FMA 推导 actual POST：After the execution of the block, the function _is_git_repo either returns a boolean or raises an exception. (1) If it returns True, then proj_dir is a valid git repository containing at least one commit (the command 'git -C proj_dir rev-parse --verify HEAD' exits with status 0). (2) If it returns False, then the command raised subprocess.CalledProcessError (nonzero exit status), meaning proj_dir is either not a git repository or has no commits. (3) If an exception is raised, it is not subprocess.CalledProcessError; it could be any other exception from subprocess.run (e.g., FileNotFoundError, PermissionError). The function has no side effects: proj_dir and the global state remain unchanged. Formally: (return = True) (git_exit_code = 0 valid_git_repo…

</details>

#### FMA-MISMATCH-089 — `src--git-py--_record_version`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/git-py/_record_version.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/git-py/_record_version.json) · [具体 bug 报告](../fm_agent/bug_validation/src--git-py--_record_version.md) · [probe](../fm_agent/bug_validation/probe_src--git-py--_record_version.py)
- 触发/冲突：Pass a truthy non-string commit_id (e.g. integer 123) which causes TypeError on int + str concatenation instead of converting to str per spec.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- work_dir is a path to an existing, writable directory
- FMA SPEC post-condition：- If commit_id is truthy: the string representation of commit_id followed by a platform-native newline is appended to the file at work_dir/version.log. If that file does not exist, it is created. If work_dir does not exist or is not writable, an OSError is raised by the underlying open() call. - If commit_id is falsy: no file I/O is performed and the filesystem is unchanged.
- FMA 推导 actual POST：If the function returns normally (no exception is raised): if commit_id is falsy, the file version.log inside work_dir is unchanged; otherwise, a new line consisting of commit_id followed by a newline character is appended to the previous contents of that file. In both cases the function returns None. If an I/O exception (such as OSError) occurs, it is propagated and the state of version.log is unspecified it may be partially modified or unchanged.

</details>

#### FMA-MISMATCH-090 — `src--git-py--frozen_worktree`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/git-py/frozen_worktree.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/git-py/frozen_worktree.json) · [具体 bug 报告](../fm_agent/bug_validation/src--git-py--frozen_worktree.md) · [probe](../fm_agent/bug_validation/probe_src--git-py--frozen_worktree.py)
- 触发/冲突：git add -A respects .gitignore and silently skips gitignored untracked files, so they are absent from the snapshot despite the spec requiring 'all untracked files'.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a filesystem path; it may or may not be a git repository and may or may not contain commits - exclude is an iterable of strings naming subdirectories of proj_dir to keep out of the git snapshot commit - copy_excluded is a boolean
- FMA SPEC post-condition：- A new, unique temporary directory is created under the system tempdir. Its name begins with "fm_agent_wt_" followed by the basename of proj_dir. - When proj_dir is a git repository with a reachable HEAD commit: - A private git index (GIT_INDEX_FILE) is used so that proj_dir's real index and working tree are never modified. - The snapshot commit captures the full state of proj_dir at entry time: HEAD tree + all tracked modifications + all untracked files, with every path in exclude removed from the snapshot commit tree. - That commit becomes a detached git worktree checked out inside the tempdir at a "snapshot" subdirectory. The yielded path is this snapshot subdirectory. - If copy_excluded is truthy: for each name in exclude, if the corresponding…
- FMA 推导 actual POST：If the generator body executed without raising an exception (i.e., after the generator has been advanced to its single yield and then exhausted naturally), the following holds: 1. The generator yields exactly one value a string wt which is the absolute, normalized path of a newly created snapshot directory. 2. wt exists and is a directory in a temporary location (its parent is the base directory returned by tempfile.mkdtemp). 3. The original proj_dir is completely unchanged: its working tree, index, HEAD, and all refs are exactly as they were before the function was called. 4. Two cases depending on the git state of proj_dir: a. Git case (is_git = True): - A new detached worktree was added to proj_dir's git repository, linked to wt, using a temporar…

</details>

### `src--incremental_reasoner-py`

#### FMA-MISMATCH-091 — `src--incremental_reasoner-py--_extract_leading_spec_comments`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_extract_leading_spec_comments.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_extract_leading_spec_comments.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_extract_leading_spec_comments.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_extract_leading_spec_comments.py)
- 触发/冲突：When spec_marker contains trailing whitespace, .strip() creates a weaker comparison that incorrectly matches a line lacking that whitespace, causing the function to return a prefix instead of None as the specification requires.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- content is a non-empty string representing file content with one or more lines - comment_prefix is a non-empty string (e.g., "#" for Python) - spec_marker is a non-empty string (e.g., "# [SPEC]")
- FMA SPEC post-condition：- Returns None when the first non-blank line of content, after stripping leading and trailing whitespace, does not equal the spec_marker value. - Returns None when the spec_marker line is the only comment line in the leading block (no subsequent line whose stripped text begins with comment_prefix appears before the first non-blank, non-comment line). - Otherwise, returns the prefix of content from the first line through (but not including) the first line that is neither blank nor a comment line. The returned string includes: all leading blank lines, the spec-marker line, all subsequent lines whose stripped text begins with comment_prefix, and any blank lines interspersed among comment lines. - The returned string, when prepended to the suffix of con…
- FMA 推导 actual POST：The function returns None if any of the following holds: (i) after splitting content by lines (keeping line endings), every line is blank (whitespace-only); (ii) the first non-blank line's stripped content is not equal to the result of stripping spec_marker; (iii) after the first non-blank line (the marker line), there is no line, before the first non-blank line that does not start with comment_prefix, whose stripped content is non-empty and starts with comment_prefix (i.e., no additional comment line after the marker). If none of these hold, the function returns a string that is the concatenation of all lines from the beginning up to (but not including) the first non-blank line that is not a comment line, including any leading blank lines, the mark…

</details>

#### FMA-MISMATCH-092 — `src--incremental_reasoner-py--_extracted_func_dir`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_extracted_func_dir.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_extracted_func_dir.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_extracted_func_dir.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_extracted_func_dir.py)
- 触发/冲突：When src_rel has a basename starting with a dot and no other dots (e.g., '.gitignore'), rfind('.') returns 0 and the condition last_dot > 0 is False, so the dot is not replaced with a hyphen as the spec requires.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- extracted_base is a non-empty string path to the extracted_functions directory - src_rel is a non-empty string representing a source file path relative to the project root, using forward slash separators, following the phases.json convention
- FMA SPEC post-condition：- Returns the absolute directory path where extracted-function files for the source file identified by src_rel are (or would be) stored, following the naming convention that mirrors the extraction mapping - The returned path is formed by joining extracted_base, the directory portion of src_rel (if any), and a directory name derived from the basename of src_rel - The directory name derivation rule: the last dot in the source file basename is replaced with a hyphen; if the basename contains no dot, it is used as-is - Example: for src_rel = "src/engine/loader.cpp" and extracted_base pointing to extracted_functions/, the returned path ends with "src/engine/loader-cpp" - The returned path uses the platform-native path separator
- FMA 推导 actual POST：The function returns a string that is the path (constructed via os.path.join) to the directory where extracted-function files for the source file `src_rel` are stored. The directory consists of `extracted_base` followed by the directory part of `src_rel` (if any) and a derived directory name. The derived directory name is obtained from the base name of `src_rel` by locating the last dot at index > 0; if found, the dot is replaced with a hyphen (e.g., `"foo.ext"` becomes `"foo-ext"`), otherwise the base name is used unchanged (e.g., `"Makefile"` stays `"Makefile"`). No side effects occur, and no exceptions are raised under the pre-condition. Formally: Let `src_dir = os.path.dirname(src_rel)`, `src_base = os.path.basename(src_rel)`, `i = src_base.rfin…

</details>

#### FMA-MISMATCH-093 — `src--incremental_reasoner-py--_funcs_from_commit`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_funcs_from_commit.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_funcs_from_commit.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_funcs_from_commit.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_funcs_from_commit.py)
- 触发/冲突：If an I/O error occurs during tmp.write(text), the try/finally block that calls os.unlink(tmp_path) is never entered, leaving the temporary file behind on disk.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- rel_path is a source file path relative to the repository root - lang_key is a recognized language key for function extraction - ext is a file extension string - old_commit_id (from enclosing scope) is a valid commit identifier in the repository
- FMA SPEC post-condition：- Returns a dict whose keys are function name strings and whose values are the corresponding full source text strings, extracted from the version of rel_path stored at old_commit_id - The returned dict is empty when the file at old_commit_id contains no extractable functions for the language identified by lang_key - No filesystem side effects persist after this function returns: any temporary file created during the call is removed before return, even when an exception is raised - Raises subprocess.CalledProcessError when old_commit_id is not a valid commit or rel_path does not exist at that commit
- FMA 推导 actual POST：Post-condition: Natural language: The function returns a dictionary mapping each top-level function name to its source text, extracted from the file at `rel_path` as it exists in the commit `old_commit_id`. The file content is retrieved via `git show`, written to a temporary file with the suffix `{ext}`, and then passed to `extract_functions_from_file`. Regardless of success or failure (e.g., git command failure, file write error, extraction error), if the temporary file is created and its path is stored in `tmp_path`, that file is deleted in a `finally` block before the function exits. If the temporary file creation itself fails before assigning `tmp_path`, an exception is raised and no cleanup is needed (the file may not exist or may be left behin…

</details>

#### FMA-MISMATCH-094 — `src--incremental_reasoner-py--_git`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_git.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_git.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_git.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_git.py)
- 触发/冲突：When git is not on PATH, _git raises FileNotFoundError instead of CalledProcessError, violating the spec which only allows CalledProcessError for nonzero exit codes.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- subcommand is a valid git subcommand name - args are zero or more string arguments to that subcommand - proj_dir (from enclosing scope) is a directory path containing a git repository cloned from the appropriate remote
- FMA SPEC post-condition：- Executes git with -C proj_dir subcommand args using subprocess - Returns the stdout output of the git command as a single string - Raises subprocess.CalledProcessError when the git command exits with a nonzero exit code
- FMA 推导 actual POST：If the `git` executable is found, the command `git -C proj_dir *args` is executed with `check=True`, `capture_output=True`, and `text=True`. Under the pre-condition that `args[0]` is a valid git subcommand and the rest are acceptable arguments, and `proj_dir` is a directory containing a git repository, execution yields exactly one of: (1) the command exits with code 0, and the returned value is the captured stdout as a string; (2) the command exits with a non-zero code, and a `subprocess.CalledProcessError` is raised, with `returncode`, `cmd`, `output`, and `stderr` attributes reflecting the failure. If the `git` executable does not exist, a `FileNotFoundError` is raised. No other side effects occur beyond any performed by the git command itself on…

</details>

#### FMA-MISMATCH-095 — `src--incremental_reasoner-py--_modified_function_targets`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_modified_function_targets.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_modified_function_targets.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_modified_function_targets.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_modified_function_targets.py)
- 触发/冲突：Dotfiles like .hidden have the dot at index 0, so last_dot > 0 is false and the code treats them as having no dot, but the spec applies the dot-to-hyphen replacement for any basename containing a dot.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is an absolute path to a project root directory whose fm_agent/extracted_functions/ subdirectory exists - modified_functions is a dict mapping absolute source-file paths to dicts, where each inner dict has string-valued keys drawn from {"added", "removed", "modified"} with list-of-string values (function names declared in that source file) - classes is a non-empty tuple of string-valued change-category la…
- FMA SPEC post-condition：- Returns a dict mapping each fully-qualified function name (FQN) to the absolute filesystem path of the corresponding extracted-function file under proj_dir/fm_agent/extracted_functions/ - A (source-file, function-name) pair is included when the function name appears in at least one of the change-category lists specified by classes within modified_functions - Function names whose change categories all fall outside classes are excluded from the result - The FQN key is derived from the extracted-function file path via the project's FQN convention: the fm_agent/extracted_functions/ prefix is stripped, the file extension is removed, and remaining path components are joined with "::" separators, where the source file's final dot was already replaced by…
- FMA 推导 actual POST：The function returns a dictionary mapping fully-qualified function names (FQNs) to absolute file paths. The mapping contains exactly one entry for each (source_file_path, change_class, function_name) triple where source_file_path is a key in modified_functions, change_class is an element of classes, and function_name is an element of modified_functions[source_file_path][change_class]. For each such triple: let rel = os.path.relpath(source_file_path, proj_dir); let src_dir = os.path.dirname(rel); let src_base = os.path.basename(rel); if src_base contains a '.' (last_dot > 0) then dir_name = src_base[:last_dot] + '-' + src_base[last_dot+1:] and ext = src_base[last_dot+1:], otherwise dir_name = src_base and ext = ''. Then func_dir = os.path.join(proj_d…

</details>

#### FMA-MISMATCH-096 — `src--incremental_reasoner-py--_opencode_select_json`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_opencode_select_json.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_opencode_select_json.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_opencode_select_json.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_opencode_select_json.py)
- 触发/冲突：The specification requires returning dict or list on success, but json.load(f) at line 106 returns any JSON value without type checking, so non-dict/list JSON values (e.g., strings, numbers) are returned in violation of the spec.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a valid writable directory - work_dir is a directory path - prompt_relpath identifies a path under proj_dir whose parent directory exists - prompt_content is a non-empty string - result_relpath identifies a path under proj_dir whose parent directory exists - stage is a non-empty string identifier - input_files is a list (possibly empty) of file paths
- FMA SPEC post-condition：- The full prompt_content is present at proj_dir/prompt_relpath when the LLM agent is invoked - Any pre-existing file at proj_dir/result_relpath is removed before the first LLM invocation - An LLM agent is invoked to read the prompt and may write a JSON artifact to result_relpath - The invocation is retried up to a configurable maximum number of times when result_relpath is not produced - A fixed delay elapses between consecutive retry attempts - Each invocation attempt is traced as an observable event - Returns the parsed JSON value (dict or list) when result_relpath is produced and its content is valid JSON - Returns None when result_relpath is never produced within the retry limit, or when the file content is not valid JSON or cannot be read - A…
- FMA 推导 actual POST：After execution (no unhandled exceptions), the function returns either None or a Python object representing the JSON content of the file at `result_path`. The following holds: 1. **Prompt file**: `prompt_path = os.path.join(proj_dir, prompt_relpath)` exists and its content is exactly `prompt_content`. Any previous file at that path is overwritten atomically via a temporary file. 2. **Result file cleanup**: If `result_path = os.path.join(proj_dir, result_relpath)` existed before the call, it is removed before the first attempt. 3. **Retry loop**: For each attempt `i` from 1 to `OPENCODE_MAX_RETRIES` (inclusive), unless an earlier attempt already caused a break: - The LLM command `cmd` returned by `build_llm_cli_command(...)` is executed via `run_open…

</details>

#### FMA-MISMATCH-097 — `src--incremental_reasoner-py--_path_exists_in_commit`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_path_exists_in_commit.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_path_exists_in_commit.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_path_exists_in_commit.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_path_exists_in_commit.py)
- 触发/冲突：Specification requires returning False when the git command fails for any reason, but the code raises an OSError (e.g., FileNotFoundError) if git cannot be started, giving no return value.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir (captured from enclosing scope) is a directory containing a git repository - old_commit_id (captured from enclosing scope) is a commit identifier valid in that repository - rel_path is a non-empty string representing a path relative to the repository root
- FMA SPEC post-condition：- Returns True when a blob identified by rel_path exists in the tree of old_commit_id - Returns False when rel_path does not identify any blob in the tree of old_commit_id, or when the git command fails for any reason - Does not read the blob content - Does not modify the repository state or any filesystem entry
- FMA 推导 actual POST：After executing this function under the given pre-conditions, the outcome is one of: (1) return True, iff the git command `git -C proj_dir cat-file -e old_commit_id:rel_path` runs and exits with code 0, indicating the path exists in the specified commit; (2) return False, iff the git command runs and exits with non-zero status (path missing or any other error reported by git); (3) an exception derived from OSError (e.g., FileNotFoundError for missing git, PermissionError, or subprocess.SubprocessError) is raised if the subprocess cannot be started, and no return value is produced. Formally: let cmd = ['git', '-C', proj_dir, 'cat-file', '-e', f'{old_commit_id}:{rel_path}']; then ( (function returns r) (r = True subprocess.run(cmd, check=False, captur…

</details>

#### FMA-MISMATCH-098 — `src--incremental_reasoner-py--_reconcile_caller`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_reconcile_caller.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_reconcile_caller.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_reconcile_caller.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_reconcile_caller.py)
- 触发/冲突：When file_map contains relative paths (due to a relative proj_dir), _reconcile_caller returns cpath as-is without converting to absolute, violating the spec's post-condition that requires an absolute path.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- caller_fqn is a non-empty FQN of a caller function whose extracted file has valid [SPEC] and [INFO] blocks. - updates is a list of (callee_fqn: str, callee_new_spec: str) tuples, each representing a callee whose [SPEC] changed. - base_idx is a non-negative integer used to construct a unique artifact identifier.
- FMA SPEC post-condition：- For each callee in updates, if the LLM determines that the callee's updated [SPEC] requires a change to the caller's existing [INFO] entry for that callee, the caller's [INFO] block is replaced with a corrected callee-expectation contract as determined by the LLM. - The original source code (everything after the [SPEC] and [INFO] leading comment blocks) is preserved identically. - If no update across all callees in updates results in a changed [INFO] block, or if the caller file cannot be read, lacks a valid leading-spec block, or has no [INFO] block, the file is not modified. - Returns the absolute path to the caller file if any [INFO] block was modified by this call; returns None otherwise.
- FMA 推导 actual POST：After the function _reconcile_caller finishes execution normally (i.e., without raising an exception), the following holds: Natural language: 1. If cpath is None or not a regular file, or if the file's extension does not map to a known programming language (clang is None), the function returns None without reading or modifying any file. 2. Otherwise, the function iterates over the `updates` list. For each (callee_name, callee_new_spec), it reads the contents of the file at cpath. It attempts to extract the leading [SPEC]/[INFO] block; if no such block exists, the update is skipped. If the extraction succeeds, it obtains the current [INFO] block (c_info) and the remaining source code (csource). If c_info is None (no callee-contract block), the update…

</details>

#### FMA-MISMATCH-099 — `src--incremental_reasoner-py--_resolve_callee_fqns`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_resolve_callee_fqns.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_resolve_callee_fqns.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_resolve_callee_fqns.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_resolve_callee_fqns.py)
- 触发/冲突：callee_names contains whitespace-padded strings; code strips whitespace causing mismatched comparison against stems with whitespace
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- caller_fqn is a non-empty string that exists as a key in callees_map. - callee_names is an iterable of non-empty strings; each represents a callee name (the final component of a callee FQN, derived from its [INFO] entry in a caller's spec). - callees_map maps each caller FQN to an iterable of callee FQNs (strings of the form "path::component::...::FunctionName"). - edge_aliases_map, when provided, maps callee_fqn…
- FMA SPEC post-condition：- Returns a (possibly empty) set of callee FQN strings. - Every returned FQN belongs to callees_map[caller_fqn]. - A callee FQN is included if and only if its final "::"-separated component (the stem) matches any string in callee_names, case-insensitively, OR any alias in edge_aliases_map for that (callee FQN, caller_fqn) pair matches any string in callee_names, case-insensitively. - A callee FQN whose stem or alias matches more than one name in callee_names is included exactly once (duplicate callee FQNs are not returned).
- FMA 推导 actual POST：The function `_resolve_callee_fqns` returns a `set` of callee FQNs from `callees_map[caller_fqn]` that match any of the given callee names (case-insensitively), considering both the stem (final `::`-separated component) of each callee FQN and any aliases provided by `edge_aliases_map`. The desired names are cleaned by stripping whitespace; empty or blank entries are discarded. The function does not mutate its inputs. Formally, let \( W = \{ \text{strip}(n) \mid n \in \text{callee\_names},\ n \neq \text{empty},\ \text{strip}(n) \neq \text{empty} \} \). Then the returned set \( \text{resolved} \) satisfies: \( \text{resolved} = \{ c \mid c \in \text{callees\_map}[\text{caller\_fqn}] \land \big( \exists w \in W: \big( (\text{stem} = c.\text{split}(\tex…

</details>

#### FMA-MISMATCH-100 — `src--incremental_reasoner-py--_topdown_ordered_fqns`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_topdown_ordered_fqns.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_topdown_ordered_fqns.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_topdown_ordered_fqns.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_topdown_ordered_fqns.py)
- 触发/冲突：Ascending layer sort places callees (lower layer numbers) before callers (higher layer numbers), producing bottom-up order instead of the spec-required top-down order.
- 成因复核：实现按升序 layer 返回 caller-first；mismatch 的 actual POST 错误沿用了“callee 在低层”的 [INFO]/domain-context 说法，是跨函数错误传播。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- work_dir is the path to an fm_agent workspace directory that contains spec_prompts/ as a subdirectory and a valid phases.json at work_dir/phases.json. - extra_call_edges, when provided, is passed through to generate_topdown_layers and must conform to the format that function expects.
- FMA SPEC post-condition：- Returns a list of fully-qualified function names (FQNs), ordered such that callers precede the callees they depend on (top-down order). - The ordering follows: ascending phase number, then ascending layer number within each phase, then the order of functions as listed within each layer (the order produced by the full run's generate_topdown_layers). - Every FQN present in the per-phase topdown-layer JSON files appears exactly once in the returned list. - As a side effect, the per-phase topdown-layer JSON files under work_dir/spec_prompts/ (phase_NN_topdown_layers.json) are regenerated via generate_topdown_layers(work_dir, extra_call_edges=extra_call_edges), mirroring the full run's layer generation.
- FMA 推导 actual POST：If no exception occurs during the execution of `_topdown_ordered_fqns`, the function returns a list `ordered` of fully qualified function names (FQNs) in the top-down order that `run_pipeline` uses for spec generation: phases in ascending phase number, layers within each phase in ascending layer number, and functions within each layer in the order they appear. The return value is exactly the concatenation of `func['name']` for all functions from all phases that have a corresponding `phase_{phase_num:02d}_topdown_layers.json` file under `work_dir/spec_prompts/`. As a side effect, the directory `work_dir/spec_prompts/` has been populated with regenerated `phase_NN_topdown_layers.json` files for every phase present in `work_dir/phases.json`, as a resul…

</details>

#### FMA-MISMATCH-101 — `src--incremental_reasoner-py--_validate`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_validate.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_validate.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_validate.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_validate.py)
- 触发/冲突：The spec says _validate produces/overwrites a result JSON file at a path derived from rel, but the code only reads it — no JSON is ever produced or overwritten at the specified path.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- rel is a non-empty relative path string identifying an extracted function file. - output_dir, proj_dir, and work_dir are valid directory paths accessible from the enclosing scope.
- FMA SPEC post-condition：- A bug validation is performed for the function identified by rel, producing or overwriting a result JSON file at the path derived by replacing the extension of rel with ".json" and resolving it relative to output_dir. - Returns rel unchanged.
- FMA 推导 actual POST：The function returns the original `rel` value unchanged. It constructs a relative path `result_json_rel` = `os.path.join(os.path.relpath(output_dir, proj_dir), os.path.splitext(rel)[0] + '.json')` and calls `_validate_single_bug(result_json_rel, proj_dir, work_dir)`. After this call, if the verification result JSON at `result_json_rel` contained a MISMATCH verdict, then a bug validation report and a verdict file have been created under `bug_validation/` directory inside `proj_dir`; otherwise (i.e., verdict is not MISMATCH), no such files are produced. The function terminates normally, propagating any unhandled exception from `_validate_single_bug` (e.g., if the JSON file does not exist or is invalid). Formally, let `out_rel` = os.path.relpath(output…

</details>

#### FMA-MISMATCH-102 — `src--incremental_reasoner-py--check_last_run_existence`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/check_last_run_existence.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/check_last_run_existence.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--check_last_run_existence.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--check_last_run_existence.py)
- 触发/冲突：A stray non-function file without [SPEC]/[INFO] markers in extracted_functions/ causes the function to incorrectly return False; the spec requires ignoring non-function files.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a path to a project directory for which run_pipeline has been previously executed (or attempted). - submodules is None or a non-empty list of project-relative directory paths using "/" separators.
- FMA SPEC post-condition：- Returns True if and only if, under proj_dir/fm_agent/, all of the following hold simultaneously: 1. The file phases.json exists. 2. The directory extracted_functions/ exists and contains at least one function file within the scope determined by submodules. 3. Every function file in extracted_functions/ that falls within the submodules scope carries both [SPEC] and [INFO] markers (as determined by is_file_ready). - Returns False when any of the three conditions above fails, including: * phases.json does not exist. * extracted_functions/ does not exist. * No function file exists within the selected scope. * At least one function file within the selected scope exists but lacks [SPEC] and/or [INFO] markers. - When submodules is None, the scope is the…
- FMA 推导 actual POST：If no exception is raised during execution, the function returns True if and only if all of the following hold: (1) the file located at os.path.join(proj_dir, 'fm_agent', 'phases.json') exists; (2) the directory os.path.join(proj_dir, 'fm_agent', 'extracted_functions') exists; (3) there exists at least one regular file in that directory tree (including subdirectories) that belongs to the selected scope (if submodules is None, all files are selected; otherwise a file is selected if its path relative to the extracted_functions directory, with backslashes replaced by '/', has one of the entries in submodules as a prefix); and (4) every selected file satisfies is_file_ready (i.e., contains at least two [SPEC] markers and at least two [INFO] markers). If…

</details>

#### FMA-MISMATCH-103 — `src--incremental_reasoner-py--flush`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/flush.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/flush.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--flush.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--flush.py)
- 触发/冲突：Calling flush() when self._console.flush() raises OSError causes the exception to propagate unhandled, violating the spec guarantee that all buffered console output has been delivered.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self._console is a writable file-like object with a working flush() method - self._log_stream is a writable file-like object whose closed property reflects whether the underlying stream is open
- FMA SPEC post-condition：- All buffered output written to self._console has been delivered to the underlying output device - When self._log_stream is in an open state (closed is False), all buffered output written to self._log_stream has been delivered to the underlying output device - When self._log_stream is in a closed state (closed is True), no flush is performed on it and no error is raised
- FMA 推导 actual POST：If the method returns normally (i.e., no exception propagates), all pending buffered data in self._console has been written to the underlying output device. Additionally, if self._log_stream was not closed immediately before the 'if' check on line 3 (i.e., the stream was open), then all pending buffered data in self._log_stream has been written to the underlying output device. If self._log_stream was closed at that time, no flush is attempted on it and its state remains unchanged. The closed/open state of both streams is not modified by this method.

</details>

#### FMA-MISMATCH-104 — `src--incremental_reasoner-py--write`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/write.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/write.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--write.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--write.py)
- 触发/冲突：When self._console.write(data) raises an exception, the method propagates it immediately, failing to deliver data to console and not returning len(data)
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self is an initialized StdoutTee instance configured with a writable console output and a log file stream. - data is a string.
- FMA SPEC post-condition：- The content of data has been delivered to the console output. - If the log stream is open at the time of the call, the content of data has also been persisted to the log. - If the log stream is closed, the log write is silently skipped; no exception is raised. - Returns len(data), the number of characters in data.
- FMA 推导 actual POST：After execution: (1) If no exception is raised, then data has been written to self._console; if at the moment of the check self._log_stream was not closed, data has also been written to self._log_stream; and the method returns len(data). (2) If self._console.write(data) raises an exception, the method terminates immediately with that exception, data is not written to self._log_stream, and no value is returned. (3) If self._console.write(data) succeeds but self._log_stream is not closed and self._log_stream.write(data) raises an exception, the method terminates with that exception, the console write remains, and no value is returned.

</details>

#### FMA-MISMATCH-233 — `src--incremental_reasoner-py--_collect_caller_context`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_collect_caller_context.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_collect_caller_context.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_collect_caller_context.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_collect_caller_context.py)
- 触发/冲突：Truthiness check 'if caller_spec or expectation:' at line 1445 would incorrectly omit callers with empty [SPEC] blocks if extract_spec_block returned content without markers, but current implementation includes markers so bug is latent.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- fqn is a non-empty FQN string identifying a function - callers_map maps FQN strings to iterables of caller FQN strings - file_map maps FQN strings to filesystem path strings - edge_aliases_map, if provided, maps callee FQNs to dicts that map caller FQNs to iterables of alias strings
- FMA SPEC post-condition：- Returns a list of (caller_fqn, caller_spec, callee_expectation) tuples - Each caller_fqn is a member of callers_map[fqn] whose mapped file exists on disk and contains at least one of a [SPEC] block or a matching [INFO] entry for fqn - caller_spec is the textual content of the caller's [SPEC] block, or None if the caller's file has no [SPEC] block - callee_expectation is the textual content of the [INFO] entry within the caller's file that describes expectations for fqn, or None if no matching entry exists or the caller has no [INFO] block - When edge_aliases_map is provided and contains an alias entry for fqn under a given caller, matching is widened: a [INFO] entry whose callee name matches any alias of fqn for that caller is treated as a match f…
- FMA 推导 actual POST：The function returns a list of triples (caller_fqn, caller_spec, callee_expectation). Let L be the iterable of caller FQN strings obtained from callers_map for fqn (empty iterable if fqn is not a key). Let S be the sorted list produced by sorting the elements of L. The returned list is built by processing each element of S in order: for each caller_fqn in S, retrieve its filesystem path from file_map. If the path is present and is an existing regular file, extract its [SPEC] block via extract_spec_block and its [INFO] block via extract_info_block. If an [INFO] block was found, use it to extract the callee specification for fqn under aliases obtained from edge_aliases_map (if provided) by extracting the tuple of aliases for caller_fqn as a caller of…

</details>

#### FMA-MISMATCH-234 — `src--incremental_reasoner-py--_collect_changed_functions`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_collect_changed_functions.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_collect_changed_functions.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_collect_changed_functions.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_collect_changed_functions.py)
- 触发/冲突：Code claim that submodules parameter is ignored in files list comprehension is false; _is_under_submodules(f, submodules) IS present and correctly filters files.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a directory path containing a git repository - old_commit_id is a valid commit identifier in that repository - submodules is None or a list of subdirectory paths relative to proj_dir
- FMA SPEC post-condition：- Returns a dict mapping absolute file paths (str) to change-category dicts, each with keys "added", "removed", and "modified" whose values are sorted lists of function name strings. - A source file is considered only when its extension maps to a recognized key in EXT_TO_LANG, it is not classified as a test file, it is not under the fm_agent workspace directory, and when submodules is provided it resides under one of the specified subdirectory paths. - For a file present in the working tree but absent from old_commit_id (including untracked files): every function name extracted from the current version appears under "added"; "removed" and "modified" are empty lists. - For a file present at old_commit_id but absent from the working tree: every functi…
- FMA 推导 actual POST：The code block completes without raising `subprocess.CalledProcessError`. The local function `_git` executed the two git commands `git -C proj_dir diff --name-only old_commit_id -- *.ext1 *.ext2 ...` and `git -C proj_dir ls-files --others --exclude-standard -- *.ext1 ...` successfully, where the pathspec extensions are those in `EXT_TO_LANG`. The output lines are stored in `changed` and `untracked` respectively. The local function `_is_workspace_file` is defined but does not modify any state. The variable `files` is an ordered list containing every relative file path `p` that satisfies all of the following conditions: (1) `p` appears as a line in either `changed` or `untracked`; (2) `_is_test_file(p)` returns `False`; (3) `_is_workspace_file(p)` ret…

</details>

#### FMA-MISMATCH-235 — `src--incremental_reasoner-py--_order_key`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_order_key.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_order_key.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_order_key.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_order_key.py)
- 触发/冲突：The default for absent keys is len(order_index), which can be smaller than the integer value stored for some present key. The specification requires that absent entries sort after all present entries, but if order_index contains a value >= len(order_index), the tuple ordering makes the absent entry appear first, breaking the guarantee.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- fqn is a string representing a fully-qualified function name - order_index is a dict mapping some FQN strings to non-negative integer indices
- FMA SPEC post-condition：- Returns a two-element tuple (position, fqn) suitable as a sort key for top-down topological ordering - When fqn is a key in order_index, position equals the integer value associated with fqn in order_index - When fqn is not a key in order_index, position equals the number of entries in order_index - For any two FQNs a, b both present in order_index: a sorts before b iff order_index[a] < order_index[b] - Any FQN not present in order_index sorts after all FQNs that are present in order_index
- FMA 推导 actual POST：The function _order_key returns a tuple (index, fqn) where index equals order_index[fqn] if fqn is a key in order_index, otherwise index equals len(order_index). The dictionary order_index is not modified, and no exceptions are raised. Formally: result = (order_index.get(fqn, len(order_index)), fqn) and for all k in order_index, order_index[k] is unchanged and the set of keys is unchanged.

</details>

#### FMA-MISMATCH-236 — `src--incremental_reasoner-py--_project_call_graph`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_project_call_graph.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_project_call_graph.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_project_call_graph.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_project_call_graph.py)
- 触发/冲突：Empty all_files list passed to _build_call_graph when phases.json has no phases or no files from any phase, but the implementation handles empty input gracefully, returning empty mappings without error.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- work_dir is a path to a project directory whose fm_agent/ subdirectory contains phases.json with a "phases" key whose value is a list of phase objects, each containing at least a "modules" key - extra_call_edges is None or an object providing supplemental caller→callee edges keyed by callee FQN and caller FQN, with optional edge labels
- FMA SPEC post-condition：- Returns a 4-tuple (callees_map, callers_map, file_map, edge_aliases_map) - callees_map is a dict mapping every FQN that appears in any phase of phases.json to the set of FQNs it directly calls, spanning all phases and including any supplemental edges from extra_call_edges - callers_map is a dict mapping every FQN to the set of FQNs that directly call it the exact inverse of callees_map (FQN A callees_map[B] B callers_map[A]) - file_map is a dict mapping every FQN to the absolute filesystem path of the extracted-function file that defines it - edge_aliases_map maps callee FQN caller FQN supplemental edge labels as provided by extra_call_edges; for FQN pairs without supplemental labels the inner mapping is absent or empty - Each distinct extracted-f…
- FMA 推导 actual POST：If the function returns, it returns a 4-tuple (callees_map, callers_map, file_map, edge_aliases_map) such that: (1) callees_map is a dict mapping each fully qualified function name (FQN) extracted from any phase in the project to a set of FQNs it directly calls; (2) callers_map is the inverse mapping each FQN to the set of FQNs that directly call it; (3) file_map maps each FQN to the absolute path of its extracted-function file; (4) edge_aliases_map maps callee FQN to a dict that maps caller FQN to supplemental edge labels (from extra_call_edges). These four maps are exactly the 1st, 2nd, 4th, and 6th elements of the 6-tuple returned by _build_call_graph when applied to the unique (by file path) list of (absolute file path, module name) pairs produc…

</details>

#### FMA-MISMATCH-237 — `src--incremental_reasoner-py--_remove_stale_extracted`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_remove_stale_extracted.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_remove_stale_extracted.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_remove_stale_extracted.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_remove_stale_extracted.py)
- 触发/冲突：The code only removes the extracted file for the first removed function per source file (because _modified_function_targets returns a single path per source file) — but empirical test shows ALL removed functions' files are deleted, and the [INFO] block was an incorrect LLM-generated description.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is an absolute path to the project root directory, under which a child path fm_agent/extracted_functions/ exists - modified_functions is a dict mapping absolute source-file paths to dicts, each having at minimum a "removed" key whose value is a list of function names declared in that source file
- FMA SPEC post-condition：- For every function name appearing in any "removed" list within modified_functions, the corresponding extracted-function file under fm_agent/extracted_functions/ no longer exists on the filesystem - For every function directory under fm_agent/extracted_functions/ that contained only files deleted by this operation, the directory itself no longer exists - Every file and directory under fm_agent/extracted_functions/ whose function does not appear in any "removed" list is unchanged
- FMA 推导 actual POST：After the code block executes, either an exception (e.g., OSError) is raised, or it completes normally. In the normal case, for every sourcefile path S such that modified_functions[S]['removed'] is a nonempty list, let P = _modified_function_targets(proj_dir, modified_functions, classes=('removed',))[S]. Then os.path.isfile(P) is False (the extractedfunction file has been removed). Moreover, for each such P, letting D = os.path.dirname(P), if D existed and became an empty directory after the removal of P, then os.path.isdir(D) is False (D has been deleted). If an exception occurred, there exists a prefix of the iteration order of the values returned by _modified_function_targets such that for all paths in that prefix the same properties hold, and no…

</details>

#### FMA-MISMATCH-238 — `src--incremental_reasoner-py--_setup_incremental_logging`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_setup_incremental_logging.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_setup_incremental_logging.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_setup_incremental_logging.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_setup_incremental_logging.py)
- 触发/冲突：The code assumes _StdoutTee exposes _console as a direct instance attribute, which it does (set in __init__); Python's attribute lookup finds it before __getattr__ is invoked, so repeated calls always resolve the real console correctly.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- work_dir is an absolute or relative filesystem path (the parent directory does not need to exist yet)
- FMA SPEC post-condition：- If work_dir does not exist, it has been created as a directory - A new log file named incremental_<YYYYmmdd_HHMMSS>.log exists under work_dir, where the timestamp captures the moment this function was called; repeated calls produce distinct timestamped files - The root logger has exactly two handlers: a FileHandler writing formatted records to that log file, and a StreamHandler writing the same formatted records to the real console stream; any handlers previously installed on the root logger have been removed - sys.stdout is replaced so that every bare print() call writes to the real console stream and also appends the same content to the log file; logging.* records are written to the log file once (via the FileHandler) and are not duplicated by t…
- FMA 推导 actual POST：If the function returns normally, the following holds: 1. The directory `work_dir` exists (created if necessary). 2. There exists a timestamp `t` such that `log_path` = os.path.join(work_dir, 'incremental_' + t.strftime('%Y%m%d_%H%M%S') + '.log') is the returned string, and a new file at that path is open for appending. 3. The root logger has exactly two handlers: a FileHandler writing to `log_path` and a StreamHandler writing to the original console stream (the real sys.stdout, unwrapped from any prior _StdoutTee by inspecting `_console` attribute). Both handlers use a Formatter with format `'%(asctime)s %(levelname)s %(name)s: %(message)s'`. The root logger level is set to `logging.INFO`. Any previously installed handlers are removed. 4. `sys.stdo…

</details>

#### FMA-MISMATCH-239 — `src--incremental_reasoner-py--collect_relevent_function_scope`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/collect_relevent_function_scope.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/collect_relevent_function_scope.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--collect_relevent_function_scope.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--collect_relevent_function_scope.py)
- 触发/冲突：LLM-based module description assessment returns no modules, but a module containing a file in changed_functions should still be selected via the OR clause at lines 142-146.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a path to a project directory whose fm_agent/ subdirectory contains phases.json (with a "phases" list of phase objects, each containing a "modules" list) and extracted_functions/ - developer_intent is a non-empty string describing the modification goal - changed_functions is a dict mapping absolute source file paths to dicts with string-list values under at least the keys "added", "modified", and "remo…
- FMA SPEC post-condition：- Returns a list of paths, each relative to the extracted_functions/ directory, ordered by descending relevance to developer_intent; paths with equal relevance are ordered lexicographically - Every returned path refers to an existing regular file under extracted_functions/ - When range is not None, the returned list has length range - Returns an empty list when phases.json defines no modules, or when no module is selected by the relevance assessment - A module is selected when EITHER its natural-language description (as recorded in phases.json) is assessed as relevant to the developer intent, OR the module contains at least one source file whose path, relativized against proj_dir, matches a key in changed_functions - Within each selected module, a s…
- FMA 推导 actual POST：The function returns a list of strings. If the flattened module list from phases.json is empty, the returned list is empty. Otherwise, the list is formed by identifying the most relevant functions via a three-pass process: (1) LLM selects relevant modules based on module descriptions; (2) for each relevant module, its source files are examined to select relevant files; (3) within each relevant file, rank_functions_in_file is called to score and rank functions by relevance to developer_intent, yielding a set of function entries each with a score. All such entries are collected, sorted by descending score, and converted to relative file paths (matching the naming convention under proj_dir/fm_agent/extracted_functions/). If the parameter range is a non…

</details>

#### FMA-MISMATCH-256 — `src--incremental_reasoner-py--_llm_check_caller_info_update`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_llm_check_caller_info_update.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_llm_check_caller_info_update.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_llm_check_caller_info_update.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_llm_check_caller_info_update.py)
- 触发/冲突：`_validate_caller_info_update` 只检查 `info_updated: bool` 和非空 `new_info: str`，因此 `new_info="arbitrary garbage"` 也会通过并返回。
- 成因复核：这不只是 SPEC 的语义理想化；下游 `_reconcile_caller` 会把 `new_info` 直接覆写到 extracted-function 文件。完整语义一致性难以用本地 validator 证明，但至少应校验完整 `[INFO]` 标记和基本块结构，否则 LLM 的合法 JSON 可直接损坏后续验证输入。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- caller_info_block 是含开闭标记的完整 `[INFO]` 块；callee_new_spec 是完整 `[SPEC]` 块；路径和语言参数有效。
- FMA SPEC post-condition：- LLM 结果必须包含 `info_updated` 和 `new_info`；更新时 `new_info` 是含标记的完整替换块，保留其他 callee 条目。
- FMA 推导 actual POST：- 返回 `_llm_select_json` 经 `_validate_caller_info_update` 处理的 dict 或 `None`；现有 validator 只能保证字段类型和非空性。

</details>

#### FMA-MISMATCH-257 — `src--incremental_reasoner-py--_llm_check_spec_update`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_llm_check_spec_update.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_llm_check_spec_update.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_llm_check_spec_update.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_llm_check_spec_update.py)
- 触发/冲突：原 code evidence 声称 `knowledge_section` “计算了但未使用”，实际 `prompt_content` 的 f-string 明确包含 `f"{knowledge_section}"`。
- 成因复核：probe 向 domain knowledge 注入唯一字符串，并在发送给 LLM 的 prompt 中找到该字符串；该 mismatch 是漏读字符串拼接项。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- 路径、FQN、语言、developer intent 和现有 SPEC/INFO 块均符合函数声明的输入域。
- FMA SPEC post-condition：- prompt 包含当前源码、SPEC/INFO、callee 列表、developer intent 以及 work_dir 下的 domain knowledge。
- FMA 推导 actual POST：- 推导的返回结构与实现基本一致，但错误断言 `knowledge_section` 未被插入 prompt。

</details>

#### FMA-MISMATCH-258 — `src--incremental_reasoner-py--_opencode_generate_spec`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_opencode_generate_spec.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_opencode_generate_spec.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_opencode_generate_spec.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_opencode_generate_spec.py)
- 触发/冲突：当 `_opencode_select_json` 返回可解析但缺少预期字段的 `{"unexpected": "dict"}` 时，本函数不校验 schema，而是原样返回。
- 成因复核：函数 docstring 明确声称与 `_opencode_check_spec_update` 返回相同 shape，后续 `_plan_spec_update` 也依赖这些字段。`_opencode_select_json` 只保证 JSON 可解析，此处缺少与 `_validate_spec_update` 等价的边界校验。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- 项目/workspace 可读写，FQN、语言、intent 和源码有效，callee_names/caller_context 符合声明结构。
- FMA SPEC post-condition：- 成功时返回含 `spec_updated/new_spec/info_updated/new_info/updated_callees` 五个字段的 dict；无法解析为该结构时返回 `None`。
- FMA 推导 actual POST：- 实际仅透传 `_opencode_select_json` 的返回值，所以任意合法 JSON 值都可能逃过本函数。

</details>

#### FMA-MISMATCH-259 — `src--incremental_reasoner-py--_plan_spec_update`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_plan_spec_update.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_plan_spec_update.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_plan_spec_update.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_plan_spec_update.py)
- 触发/冲突：LLM 若在 `updated_callees` 中返回 FQN，计划会原样透传，没有归一化为最后一段短名。
- 成因复核：下游 `_resolve_callee_fqns` 仅将该值与 callee stem/别名匹配，FQN 会导致更新传播静默丢失。prompt 给出的 known callees 是短名，但 LLM 输出是不可信边界；应在 validator、plan 或 resolver 中统一归一化。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- 嵌套 plan 函数所需的 file_map/call graph/语言配置和路径状态已初始化。
- FMA SPEC post-condition：- 成功时 plan 的 `updated_callees` 是 callee FQN 最后一段的短名列表，供下游传播。
- FMA 推导 actual POST：- `"updated_callees": result.get("updated_callees") or []` 未做任何短名转换。

</details>

#### FMA-MISMATCH-260 — `src--incremental_reasoner-py--_reapply_existing_specs`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_reapply_existing_specs.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_reapply_existing_specs.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_reapply_existing_specs.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_reapply_existing_specs.py)
- 触发/冲突：对 2 个实际写入 SPEC 头的文件，函数返回 `None`，而不是声明的修改数 `2`。
- 成因复核：这一返回契约同时出现在源码 docstring，不是仅由 LLM SPEC 发明；实现没有 counter 和 `return`。当前 caller 忽略返回值，所以运行影响较低，但函数自身的明示 API 契约确实未实现。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- specs 是 `extract_existing_specs` 生成的映射，extracted-functions 树包含刚重新抽取的原始函数文件。
- FMA SPEC post-condition：- 向尚无 SPEC 头的现存文件恢复 SPEC/INFO，并返回实际写入的文件数。
- FMA 推导 actual POST：- 文件内容会按预期被重写，但函数落到末尾时隐式返回 `None`。

</details>

#### FMA-MISMATCH-261 — `src--incremental_reasoner-py--_split_spec_and_info`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_split_spec_and_info.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_split_spec_and_info.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_split_spec_and_info.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_split_spec_and_info.py)
- 触发/冲突：probe 传入 `extra\n[SPEC]\ncontent\n[SPEC]`，然后指责返回的 spec_block 包含 `extra`。
- 成因复核：前置条件和源码 docstring 都规定 `block` 来自 `_extract_leading_spec_comments`；该 callee 要求第一个非空行就是 SPEC marker，不可能产生这个反例。probe 越过上游合约直接构造了不可达状态。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- block 是 `_extract_leading_spec_comments` 返回的 leading SPEC/INFO 注释块，comment_prefix/spec_marker 与该块匹配。
- FMA SPEC post-condition：- 返回 `(spec_block, info_block)`，从第一对 SPEC marker 切出 SPEC，并在存在时切出 INFO。
- FMA 推导 actual POST：- 实现从 `lines[0]` 取到第二个 SPEC marker；对合法 callee 输出，`lines[0]` 本来就是第一个 marker。

</details>

#### FMA-MISMATCH-262 — `src--incremental_reasoner-py--_update_specs_for_intent`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_update_specs_for_intent.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_update_specs_for_intent.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_update_specs_for_intent.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_update_specs_for_intent.py)
- 触发/冲突：原报告把嵌套 `_plan_spec_update` 中的 `return None` 当成了外层 `_update_specs_for_intent` 的返回。
- 成因复核：probe 分别执行空 seed 和非空 seed 路径，外层函数都返回 list；推理器混淆了嵌套函数的控制流边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- 项目路径、调用图产物、changed_functions 和 relevant file 列表符合增量管线 schema。
- FMA SPEC post-condition：- 按 caller-before-callee 轮次更新 SPEC/INFO，并返回排序后的已更新 extracted-function 相对路径列表。
- FMA 推导 actual POST：- 原推导将内层 plan 的早返回错归到外层；实际外层空 seed 返回 `[]`，正常结束返回 `sorted(changed_spec_files)`。

</details>

#### FMA-MISMATCH-263 — `src--incremental_reasoner-py--_verify_incremental_functions`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/_verify_incremental_functions.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/_verify_incremental_functions.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--_verify_incremental_functions.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--_verify_incremental_functions.py)
- 触发/冲突：SPEC 将 `submodules=[]` 解释为“启用筛选但没有任何允许前缀”，因而指责 `if submodules:` 会验证全部函数。
- 成因复核：仓库的 `_normalize_submodules` 在用户没有指定 `--submodule` 时就返回 `[]`，整条管线一贯用真值表示“是否限定 scope”。若按生成 SPEC 的 `is not None` 语义，默认运行反而会验证零个函数，与 CLI/README 的全项目默认行为相反。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- submodules 为 `None` 或相对目录列表，其余参数符合增量验证管线结构。
- FMA SPEC post-condition：- 当 `submodules is not None` 时必须执行路径过滤。
- FMA 推导 actual POST：- 实现在 `submodules` 为非空真值时执行过滤；这与上游将空列表视为“未限定”的协议一致。

</details>

#### FMA-MISMATCH-264 — `src--incremental_reasoner-py--extract_existing_specs`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/extract_existing_specs.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/extract_existing_specs.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--extract_existing_specs.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--extract_existing_specs.py)
- 触发/冲突：probe 人工构造行首缩进的 SPEC/INFO 标记，再要求恢复结果保留这些缩进；重建过程确实会将部分行左移。
- 成因复核：该函数的声明输入是“上一次完整 full run 产生的 extracted-functions”，`md/system_prompt.md` 的格式模板和实际生成器都把 `<C> [SPEC]`/`<C> [INFO]` 放在文件行首。probe 使用的缩进头不是该管线可产生的 baseline。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir 是项目目录，其 `fm_agent/extracted_functions/` 来自上次 full run，也可不存在。
- FMA SPEC post-condition：- 收集每个已生成 SPEC 的文件，保存完整 SPEC 块和可选完整 INFO 块，不修改磁盘。
- FMA 推导 actual POST：- INFO body 由 `extract_info_block(...).strip()` 提取，marker 再用 SPEC 检测到的 comment prefix 重建；人工缩进样本不会字节保真。

</details>

#### FMA-MISMATCH-265 — `src--incremental_reasoner-py--run_incremental_pipeline`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/incremental_reasoner-py/run_incremental_pipeline.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/incremental_reasoner-py/run_incremental_pipeline.json) · [具体 bug 报告](../fm_agent/bug_validation/src--incremental_reasoner-py--run_incremental_pipeline.md) · [probe](../fm_agent/bug_validation/probe_src--incremental_reasoner-py--run_incremental_pipeline.py)
- 触发/冲突：原报告只读到删除 `logic_verification_results/` 和 `bug_validation/` 的第一个 cleanup loop，便断言顶层增量 prompt/result 不会删除。
- 成因复核：紧接着的第二个 cleanup block 定义了 `stale_artifact_globs`，完整覆盖 `select_relevant_*`、`relevant_*` 和 `spec_update_*`；probe 也确认全部要求的前缀都能匹配。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- 项目、旧 commit、intent 文件、可选 submodules/domain knowledge/extra edges 符合增量管线输入。
- FMA SPEC post-condition：- 在新产物生成前删除旧 verification/bug-validation 目录，并清理上一轮的 scope-selection/spec-update 中间文件。
- FMA 推导 actual POST：- 推导只截取了第一个目录删除代码块，遗漏后面的 glob 文件清理，因而生成不完整 actual POST。

</details>

### `src--languages--c-py`

#### FMA-MISMATCH-105 — `src--languages--c-py--function_spans`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/c-py/function_spans.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/c-py/function_spans.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--c-py--function_spans.md) · [probe](../fm_agent/bug_validation/probe_src--languages--c-py--function_spans.py)
- 触发/冲突：Calling function_spans with a valid proj_dir that initializes codegraph but a filepath not in the index returns None instead of a list, violating the spec mandate that None is only for when codegraph cannot be initialized.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a path to an existing project directory - filepath is a path to a C source file with a ".c" extension
- FMA SPEC post-condition：- Returns None when a codegraph instance cannot be initialized from proj_dir - Otherwise returns a list of (function_name, start_idx, end_idx) tuples for every function defined in the C source file at filepath, where start_idx and end_idx are 0-indexed inclusive line numbers
- FMA 推导 actual POST：The code block either raises an exception during CodeGraphExtractor construction or method call, or it terminates normally and returns a value r. In the normal case, r is either None (indicating the codegraph is unavailable or does not index the given file) or a list of tuples, each of the form (name: str, start: int, end: int) with start <= end and both indices nonnegative, representing 0indexed inclusive line spans of C function definitions extracted from filepath. Formally: (normal_termination) ( (r = None) ( (r = [(name_1, start_1, end_1), , (name_k, start_k, end_k)]) ( i {1,,k} : type(name_i)=str type(start_i)=int type(end_i)=int 0 start_i end_i) ) ).

</details>

#### FMA-MISMATCH-240 — `src--languages--c-py--call_edges`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/c-py/call_edges.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/c-py/call_edges.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--c-py--call_edges.md) · [probe](../fm_agent/bug_validation/probe_src--languages--c-py--call_edges.py)
- 触发/冲突：Docstring claims tuple format but CodeGraphExtractor.get_call_edges actually returns FQN string keys matching the specification.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string path to an existing project directory
- FMA SPEC post-condition：- Returns None when no codegraph backend for the C language can be initialized from proj_dir; this signals the caller to fall back to regex-based call-edge detection for this language - Otherwise returns a dict where each key is a fully-qualified caller function name and each value is a set of fully-qualified callee function names that the caller directly invokes - An empty dict (distinct from None) indicates the backend initialized successfully but found zero call edges
- FMA 推导 actual POST：Returns either None if the internal CodeGraphExtractor initialization fails (i.e., CodeGraphExtractor.from_proj_dir(proj_dir) returns None), or a dictionary where each key is a tuple (caller_stem, caller_module) and the corresponding value is a set of callee stems representing the direct function calls from that caller to its callees, as produced by cg.get_call_edges('c'). No side effects occur.

</details>

### `src--languages--codegraph-py`

#### FMA-MISMATCH-106 — `src--languages--codegraph-py--_bare_function_name`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/codegraph-py/_bare_function_name.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/codegraph-py/_bare_function_name.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--codegraph-py--_bare_function_name.md) · [probe](../fm_agent/bug_validation/probe_src--languages--codegraph-py--_bare_function_name.py)
- 触发/冲突：For input '(*T).Method()', the function-pointer regex matches '(*T)' and returns 'T' before the suffix regex can extract 'Method' after the dot.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- name is a string that may be a raw function name, a scope-qualified name, a decorated function signature (function-pointer or pointer-return syntax), or an empty string
- FMA SPEC post-condition：- Returns a string containing the bare, unqualified function identifier extracted from name, with no surrounding syntactic decorations - When name is empty or consists only of whitespace characters, returns the empty string "" - When name contains a scope qualifier double-colon '::', member-access dot '.', or a parenthesized receiver expression ending with '.' or ')' returns the rightmost identifier component after the last such separator - When name is a function-pointer expression matching the pattern '(*identifier)(...)' possibly followed by a parameter list, returns the captured identifier - When name starts with '*' followed by an identifier (pointer-return syntax), returns that identifier - When name starts with word characters (alphanumeric a…
- FMA 推导 actual POST：The returned string r satisfies the following: Let t = name.strip(). If t is empty, r = ''. Otherwise, in order: if t contains a suffix conforming to the regex ([:.)])(\w+)$, then r is the captured word characters; else if t matches the regex ^\(\s*\*\s*(\w+)\s*\), then r is the captured word; else if t matches the regex ^\*\s*(\w+), then r is the captured word; else if t matches the regex ^(\w+), then r is the captured word; else r = t.

</details>

#### FMA-MISMATCH-107 — `src--languages--codegraph-py--_fqn_for`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/codegraph-py/_fqn_for.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/codegraph-py/_fqn_for.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--codegraph-py--_fqn_for.md) · [probe](../fm_agent/bug_validation/probe_src--languages--codegraph-py--_fqn_for.py)
- 触发/冲突：On Linux, backslashes in file_path are not treated as path separators because the code only normalizes os.sep ('/'); backslashes persist as literal chars in FQN components.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- file_path is a string representing a filesystem path to a source file - name is a non-empty canonicalized function name string (template parameters stripped, operator names normalized to safe identifiers)
- FMA SPEC post-condition：- Returns a fully-qualified function name (FQN) string whose components are separated by "::" - The FQN consists of, in order: the non-empty directory components of file_path (excluding the source filename), a single file-derived component, and name - The file-derived component is obtained from the filename portion of file_path: if the filename contains at least one "." after a non-empty prefix, the last "." is replaced by "-"; otherwise the filename is used unchanged - Directory components are extracted independently of OS path separator convention and empty components (from leading or consecutive separators) are excluded - The returned FQN is deterministic and identical to the FQN that the call-graph builder computes for the extracted function fil…
- FMA 推导 actual POST：The function returns a string `fqn` defined as follows: Let `norm = file_path.replace(os.sep, '/')` Let `d = os.path.dirname(norm)` Let `base = os.path.basename(norm)` Let `last_dot = base.rfind('.')` If `last_dot > 0`: `dashed = base[:last_dot] + '-' + base[last_dot+1:]` Else: `dashed = base` Let `parts = [p for p in d.split('/') if p] + [dashed, name]` Then `fqn = '::'.join(parts)`. No side effects; the function always returns this value for given valid inputs (assuming `os.sep` and `os.path` functions behave standardly).

</details>

#### FMA-MISMATCH-108 — `src--languages--codegraph-py--from_proj_dir`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/codegraph-py/from_proj_dir.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/codegraph-py/from_proj_dir.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--codegraph-py--from_proj_dir.md) · [probe](../fm_agent/bug_validation/probe_src--languages--codegraph-py--from_proj_dir.py)
- 触发/冲突：A non-database file named codegraph.db triggers a false-positive return of a broken CodeGraphExtractor instance instead of None.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string representing a filesystem path to a directory
- FMA SPEC post-condition：- Returns an initialized CodeGraphExtractor instance when a codegraph database exists within the project directory structure reachable from proj_dir - Returns None when no codegraph database is found in the project directory structure, indicating the codegraph backend is unavailable for the project - The returned instance is bound to the discovered database and is ready to serve query operations (get_call_edges, function_spans, batch_extract) against the project's indexed source files
- FMA 推导 actual POST：The method returns an instance of the class (initialized with a live connection to the codegraph database) if a file named 'codegraph.db' exists under the '.codegraph' subdirectory of either `proj_dir` itself or its parent directory (obtained via `os.path.abspath` then `os.path.dirname`), checking `proj_dir` first. If neither directory contains that file, the method returns `None`. The returned instance, if any, is ready to resolve function definitions and call edges for all indexed languages. Formally, given the file system state FS at call time, define candidate_dirs = [proj_dir, dirname(abspath(proj_dir))] and for each candidate c let db_path(c) = join(c, '.codegraph', 'codegraph.db'). The result is cls(db_path(candidate_dirs[0])) if FS.exists(db…

</details>

#### FMA-MISMATCH-109 — `src--languages--codegraph-py--get_call_edges`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/codegraph-py/get_call_edges.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/codegraph-py/get_call_edges.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--codegraph-py--get_call_edges.md) · [probe](../fm_agent/bug_validation/probe_src--languages--codegraph-py--get_call_edges.py)
- 触发/冲突：Languages in _CG_LANG but absent from _CONSTRUCTOR_FILTER (go, rust, c, cuda) silently skip constructor call synthesis, omitting constructor callees from instantiates edges.
- 成因复核：源码明确说明 Go/Rust/C 没有传统 constructor 并故意不合成 instantiates 边；SPEC 将这种 语言设计选择写成遗漏。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self is an initialized CodeGraphExtractor instance with a valid database connection - lang_key is a string identifying a supported language
- FMA SPEC post-condition：- Returns a dict whose keys are fully-qualified caller function names and whose values are sets of fully-qualified callee function names - Every key-value pair represents that the caller directly invokes each callee in the associated set, as recorded by the project's codegraph analysis - Returns an empty dict when lang_key is not a recognized language or when the project contains no call edges for the given language - Constructor calls are included: when a function instantiates a class, the class's constructor method appears in the callee set of the instantiating function - Every FQN in the returned dict uses the canonical naming convention (path components separated by "::", source file extension replaced by a hyphen in the parent directory compone…
- FMA 推导 actual POST：Natural Language: If lang_key is not found in _CG_LANG (i.e., _CG_LANG.get(lang_key) is falsy), the method returns an empty dictionary {} early. Otherwise, it opens a connection to the database (self._db) and queries the edges and nodes tables to construct a mapping of call-edges. It first builds a map fqn_of from node IDs to fully qualified names using _node_fqn_map. Then it queries all 'calls' edges where the source node's language is in cg_langs. For each such edge, if both source and target have FQN entries, it adds callee to the caller's set. Next, if the language has a configured constructor filter (_CONSTRUCTOR_FILTER.get(lang_key)), it performs a second query to synthesize constructor calls: for each 'instantiates' edge where the source node…

</details>

#### FMA-MISMATCH-110 — `src--languages--codegraph-py--get_function_spans`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/codegraph-py/get_function_spans.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/codegraph-py/get_function_spans.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--codegraph-py--get_function_spans.md) · [probe](../fm_agent/bug_validation/probe_src--languages--codegraph-py--get_function_spans.py)
- 触发/冲突：On Windows, if abs_filepath is on a different drive than the project root, os.path.relpath raises ValueError instead of returning None.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self is a valid CodeGraphExtractor instance - lang_key is a string identifying a language - abs_filepath is an absolute filesystem path to a source file
- FMA SPEC post-condition：- Returns None when the codegraph backend does not support the language identified by lang_key, or when the file at abs_filepath is not present in the codegraph index, or when the file is indexed but contains no function or method definitions - Otherwise returns a list of (name, start_idx, end_idx) tuples, one per function or method definition that the codegraph backend has indexed in the file - name is a string containing the bare function identifier: namespace and class qualifiers removed, template parameters stripped, canonicalized according to the project's name-normalization rules - start_idx and end_idx are 0-indexed inclusive integers delimiting the source lines occupied by the function body - Tuples in the returned list are ordered by ascend…
- FMA 推导 actual POST：After execution, the function either raises an exception (e.g., from filesystem operations, SQLite connectivity, or data integrity errors) or returns a value v satisfying one of the following: (1) v = None if lang_key is not a key in _CG_LANG (i.e., unsupported language) or if the database query yields no rows (file not indexed or contains no functions/methods); (2) v is a list of triples (name, start, end) where name = canonicalize(_bare_function_name(row.name)), start = int(row.start_line) - 1, end = int(row.end_line) - 1 for each row returned by the query `SELECT name, start_line, end_line FROM nodes WHERE kind IN ('function','method') AND language IN (cg_langs) AND file_path = rel ORDER BY start_line`, with cg_langs = _CG_LANG[lang_key] and rel…

</details>

#### FMA-MISMATCH-111 — `src--languages--codegraph-py--get_functions_by_file`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/codegraph-py/get_functions_by_file.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/codegraph-py/get_functions_by_file.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--codegraph-py--get_functions_by_file.md) · [probe](../fm_agent/bug_validation/probe_src--languages--codegraph-py--get_functions_by_file.py)
- 触发/冲突：When proj_dir is None, the code uses file_path from the database directly without converting to an absolute path, violating the spec requirement for absolute file path keys.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self is a valid CodeGraphExtractor instance - lang_key is a string identifying a language - proj_dir, when provided, is a filesystem path to a project root directory
- FMA SPEC post-condition：- Returns an empty dict {} when the codegraph backend does not support the language identified by lang_key - Otherwise returns a dict mapping absolute file paths (str) to lists of (func_name: str, body: str) tuples for every function and method definition indexed across all source files of the given language in the project - func_name is the canonicalized bare function identifier: namespace and class qualifiers removed, template parameters stripped, with a deterministic numeric suffix (_1, _2, ...) appended when multiple functions in the same source file share the same canonicalized bare name; the first occurrence receives no suffix - body is the full source text of the function definition as read from the original source file, including the signatu…
- FMA 推导 actual POST：The method returns a dictionary `result` with the following properties: 1. **Pre-condition on inputs**: `self` is a valid `CodeGraphExtractor` instance with a database path `self._db`. `lang_key` is a string that may or may not be present in `_CG_LANG`. `proj_dir` is either `None` or a valid filesystem path string. 2. **Empty-language case**: If `_CG_LANG.get(lang_key)` returns a falsy value (e.g., missing key, empty list), the function immediately returns `{}`. 3. **Normal execution**: Otherwise, the SQLite database at `self._db` is queried for all rows from the `nodes` table where `kind` is `'function'` or `'method'` and `language` is one of the values in `cg_langs`. The rows are ordered by `file_path` then `start_line`. The database connection is…

</details>

#### FMA-MISMATCH-112 — `src--languages--codegraph-py--try_codegraph_init`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/codegraph-py/try_codegraph_init.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/codegraph-py/try_codegraph_init.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--codegraph-py--try_codegraph_init.md) · [probe](../fm_agent/bug_validation/probe_src--languages--codegraph-py--try_codegraph_init.py)
- 触发/冲突：When .codegraph/ directory exists without codegraph.db and force=False, the function does not remove the existing .codegraph/ directory before running codegraph init, violating the spec's requirement.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a non-empty string representing a directory path on the filesystem. - force is True or False.
- FMA SPEC post-condition：- Returns None; never raises an exception. - When the `codegraph` executable is not found on the system PATH: returns immediately without creating, modifying, or removing any files under proj_dir. - When proj_dir/.codegraph/codegraph.db exists AND force is False: returns immediately; the existing index file and its parent directory are preserved. - Otherwise (force is True, or proj_dir/.codegraph/codegraph.db does not exist): - If a proj_dir/.codegraph/ directory exists, it is removed prior to rebuilding (recursively, with errors ignored). - `codegraph init` is executed with proj_dir as its working directory. - If `codegraph init` exits with code 0: proj_dir/.codegraph/codegraph.db exists after return and reflects the file tree of proj_dir at the ti…
- FMA 推导 actual POST：After execution, no unhandled exceptions propagate. Let init_db_pre be the file `<proj_dir>/.codegraph/codegraph.db`. If init_db_pre exists and force is False, the function returns immediately with no side effects (filesystem unchanged, no output). Otherwise (init_db_pre does not exist, or force is True): - If init_db_pre exists (and force True), a removal of `<proj_dir>/.codegraph` is attempted via `shutil.rmtree` with `ignore_errors=True`, and the message "[Pipeline] Rebuilding codegraph index for current working tree..." is printed. The directory and its contents may or may not be fully removed; removal errors are silently ignored. - If init_db_pre does not exist, the message "[Pipeline] Building codegraph index..." is printed and no removal is a…

</details>

#### FMA-MISMATCH-241 — `src--languages--codegraph-py--_node_fqn_map`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/codegraph-py/_node_fqn_map.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/codegraph-py/_node_fqn_map.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--codegraph-py--_node_fqn_map.md) · [probe](../fm_agent/bug_validation/probe_src--languages--codegraph-py--_node_fqn_map.py)
- 触发/冲突：Calling _node_fqn_map with an empty cg_langs list after creating a nodes table with test data — the bug claim asserted invalid SQL, but SQLite treats IN () as matching 0 rows gracefully.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- cur is a database cursor connected to a codegraph database containing a nodes table with columns id, name, file_path, start_line, kind, and language - cg_langs is a non-empty sequence of language key strings
- FMA SPEC post-condition：- Returns a dict mapping each node's id to its fully-qualified function name (FQN) - The mapping includes exactly the rows from the nodes table whose kind is either 'function' or 'method' and whose language is one of the given cg_langs values, ordered by (file_path ASC, start_line ASC) - Each FQN is derived from the node's file_path and a canonicalized, deduplicated function name in the canonical convention where path components are joined by "::" and the source file extension in the parent directory component is replaced by a hyphen - Function name canonicalization strips angle-bracket template parameters and normalizes operator-overload names to safe identifier forms - When N > 1 nodes share the same file_path and canonicalized name, the first suc…
- FMA 推导 actual POST：After successful execution, the function returns a dictionary `result` mapping each node id (integer) of all rows in the `nodes` table where `kind` is either 'function' or 'method' and `language` is one of the languages in the nonempty sequence `cg_langs`, to a fully qualified name string. The FQN is constructed by processing the rows in the order given by `ORDER BY file_path, start_line`. For each row, a bare function name is extracted by stripping any anglebracket template parameters from `name`, then canonicalized into a safe identifier (`cname`). For each distinct `(file_path, cname)` pair, the first occurrence (by the ordering) receives `cname` as the deduplicated name; subsequent occurrences receive `cname_1`, `cname_2`, etc., where the append…

</details>

### `src--languages--cpp-py`

#### FMA-MISMATCH-113 — `src--languages--cpp-py--batch_extract`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/cpp-py/batch_extract.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/cpp-py/batch_extract.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--cpp-py--batch_extract.md) · [probe](../fm_agent/bug_validation/probe_src--languages--cpp-py--batch_extract.py)
- 触发/冲突：Passing None as proj_dir raises TypeError instead of returning empty dict as spec requires.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a non-empty string representing a directory path that contains C++ source files (.cpp, .cc, .cxx) and may have a codegraph index (.codegraph/codegraph.db).
- FMA SPEC post-condition：- Returns a dictionary where each key is an absolute file path (str) and each value is a list of (function_name: str, body: str) tuples. - Every key corresponds to a C++ source file under proj_dir for which codegraph extracted at least one top-level function. - Each function_name is the canonical name of a function defined in the corresponding source file. - Each body is the full source text of that function as returned by codegraph. - If codegraph is not available for proj_dir (CodeGraphExtractor.from_proj_dir returns a falsy value), the returned dictionary is empty. - The returned dictionary does not include entries for non-C++ files or for files from which codegraph extracted zero functions.
- FMA 推导 actual POST：If the function terminates normally, it returns a dictionary d: if the CodeGraphExtractor initialization from proj_dir failed (returned a falsy value), then d == {}; otherwise, d == cg.get_functions_by_file('cpp', proj_dir), i.e., a mapping from each absolute file path of a C++ source file (.cpp, .cc, .cxx) under proj_dir to a list of (function_name: str, body: str) tuples for all top-level functions in that file. If an exception is raised (e.g., due to an inaccessible directory, permission error, or internal error), the exception propagates and no return value is produced.

</details>

### `src--languages--erlang-py`

#### FMA-MISMATCH-114 — `src--languages--erlang-py--__init___1`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/__init___1.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/__init___1.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--__init___1.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--__init___1.py)
- 触发/冲突：_ContentModifiedError.__init__ passes str(error) to super().__init__() which renders the full dict repr as the exception message instead of using the human-readable 'message' field from the JSON-RPC error dict.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- error is a dict
- FMA SPEC post-condition：- The exception instance is initialized with a string representation derived from the error dict, suitable for use as the exception message - self.error is set to the provided error dict, making the full JSON-RPC error response accessible to exception handlers
- FMA 推导 actual POST：After normal execution: (1) The parent class __init__ has been invoked with argument str(error). (2) The instance attribute 'error' is bound to the input dict error. If super().__init__ raises an exception, 'error' attribute is not set and the exception propagates. Formally: (exceptional self.error = error super().__init__(str(error)) called) (exceptional 'error' dir(self))

</details>

#### FMA-MISMATCH-115 — `src--languages--erlang-py--_analyze_project`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_analyze_project.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_analyze_project.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_analyze_project.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_analyze_project.py)
- 触发/冲突：When the in-memory cache contains a matching fingerprint entry, _analyze_project returns cached data without contacting ELP, bypassing the required exception when ELP is unavailable.
- 成因复核：缓存命中不联系 ELP 正是缓存的目的；SPEC 要求每次验证 ELP 可用性，反而取消缓存语义。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a non-empty string representing a filesystem path to an existing, accessible project directory
- FMA SPEC post-condition：- Returns an ErlangAnalysis object whose .functions attribute is a dict mapping absolute .erl file paths to lists of (func_name, source_text) tuples, whose .edges attribute is a dict mapping caller FQNs to sets of callee FQNs, and whose .spans attribute is a dict mapping absolute file paths to lists of (func_name, start_line, end_line) tuples - The returned ErlangAnalysis is populated from the Erlang Language Platform analysis of the project at proj_dir - Raises an exception when the ELP backend is unavailable or analysis cannot complete (including process failure or inaccessible project)
- FMA 推导 actual POST：The function either (1) returns an ErlangAnalysis object for the project at `proj_dir` or (2) raises an exception from the uncached analysis routine, leaving the in-memory cache and persistent storage unchanged. The in-memory cache is protected by `_CACHE_LOCK` which is never held after the call. Normal termination (return): - Let `root = os.path.abspath(proj_dir)`, `fp = _project_fingerprint(root)`. - If before the call the cache `_CACHE` contained an entry for `root` whose fingerprint matches `fp`, the function returns that cached analysis value; the cache and persistent storage are not modified. - Otherwise, the function computes `analysis = _analyze_project_uncached(root)`. Persistence is attempted via `_persist_analysis(root, fp, analysis)`; an…

</details>

#### FMA-MISMATCH-116 — `src--languages--erlang-py--_caller_module`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_caller_module.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_caller_module.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_caller_module.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_caller_module.py)
- 触发/冲突：Any path whose basename starts with a dot and contains at least one dot (e.g., '.hidden') — dot > 0 check causes the basename to be returned unchanged instead of replacing the leading dot with '-'.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- path is a string representing a filesystem path (typically an absolute path to a source file)
- FMA SPEC post-condition：- Returns the Erlang module name derived from the file's base name by replacing the last occurrence of "." in the base name with "-" - When the base name contains no "." character, returns the base name unchanged - The result is deterministic: identical path strings always produce identical return values - The result depends only on the basename portion of path (the final path component after the last "/" or "\")
- FMA 推导 actual POST：The function returns a string that is the basename of the input path, but with the last '.' replaced by '-', unless the basename starts with '.' or contains no '.', in which case it returns the basename unchanged. In other words: let b = os.path.basename(path). If b has no '.' or b[0] == '.', then the result equals b; otherwise, let i be the index of the last '.' in b (so b[i] == '.', i > 0, and no later '.' exists), then the result is b[:i] + '-' + b[i+1:].

</details>

#### FMA-MISMATCH-117 — `src--languages--erlang-py--_callgraph_project_root`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_callgraph_project_root.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_callgraph_project_root.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_callgraph_project_root.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_callgraph_project_root.py)
- 触发/冲突：_callgraph_project_root returns proj_dir instead of parent when the only .erl files in the parent reside inside a _SKIP_DIRS directory (e.g., test/), because _iter_project_files silently skips those directories.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string representing a valid filesystem path to a project directory
- FMA SPEC post-condition：- Returns the absolute, normalized path to the original source-project root directory - If proj_dir does not contain an "extracted_functions" subdirectory, returns abspath(proj_dir) - If proj_dir is the filesystem root (parent directory resolves to itself), returns abspath(proj_dir) - If proj_dir contains "extracted_functions" and is not the filesystem root, and the parent directory contains at least one Erlang source file (.erl extension), returns the parent directory of proj_dir - If proj_dir contains "extracted_functions" and is not the filesystem root, but the parent directory contains no Erlang source files, returns abspath(proj_dir)
- FMA 推导 actual POST：Let `R = os.path.abspath(proj_dir)`. Let `HAS_EF = os.path.isdir(os.path.join(R, 'extracted_functions'))`. Let `P = os.path.dirname(R)`. Let `HAS_ERL = (next(_iter_project_files(P, {'.erl'}), None) is not None)`, where `_iter_project_files` yields absolute paths of files under `P` (recursively) with extension `.erl`, ignoring directories whose name appears in the global set `_SKIP_DIRS`. The function returns a string `result` such that: if `not HAS_EF` then `result == R`; else (`HAS_EF` is true), if `P == R` then `result == R`, else if `HAS_ERL` then `result == P`, else `result == R`. In all cases, `result` is the absolute path of either `proj_dir` or its immediate parent directory. The function does not modify the filesystem, raise exceptions under…

</details>

#### FMA-MISMATCH-118 — `src--languages--erlang-py--_elp_argv`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_elp_argv.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_elp_argv.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_elp_argv.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_elp_argv.py)
- 触发/冲突：Setting ELP_COMMAND to an unbalanced-quoted string causes shlex.split to raise ValueError instead of returning a list
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- The process environment is available for reading
- FMA SPEC post-condition：- Returns a non-empty list of strings representing the argument vector used to launch the Erlang Language Platform server subprocess - The last element of the returned list is the string "server" - The returned value is deterministic across calls: given an unchanged value of the ELP_COMMAND environment variable and the same operating-system platform (POSIX vs non-POSIX), repeated calls return the same list - When the ELP_COMMAND environment variable changes, the returned list reflects the new command
- FMA 推导 actual POST：The function returns a list of strings with no other side effects. The returned list is computed as follows: let env_val = os.environ.get('ELP_COMMAND', 'elp'); let stripped = env_val.strip(); let command = stripped if stripped else 'elp'; let posix = (os.name != 'nt'); let argv = shlex.split(command, posix=posix); then the return value is argv + ['server']. Since command is never empty, argv is never empty and the dead-code fallback to ['elp'] is unreachable.

</details>

#### FMA-MISMATCH-119 — `src--languages--erlang-py--_escape_component`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_escape_component.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_escape_component.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_escape_component.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_escape_component.py)
- 触发/冲突：Input containing underscore followed by a non-alphanumeric character (e.g., '_:') produces forbidden '__' in output.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- value is a string
- FMA SPEC post-condition：- Returns an escaped representation of value suitable for use as a component in a fully-qualified name (FQN) where double-underscore ("__") serves as the component separator - The returned string contains no occurrence of the substring "__" - When value is non-empty, the returned string is non-empty - Each character of value that is an ASCII alphanumeric or underscore is preserved as-is at its original position - Every other character is replaced by an underscore followed by the lowercase hexadecimal representation of its Unicode code point (zero-padded to at least 2 digits), preserving the original relative order of all characters
- FMA 推导 actual POST：The returned string is the concatenation, in order, of the transformation of each character c in the input string value: if c is an ASCII alphanumeric character (as determined by c.isascii() and c.isalnum()) or the underscore '_', then c itself; otherwise the string consisting of an underscore followed by the two-digit hexadecimal representation of ord(c) (using lowercase letters). Formally: result == ''.join(c if (c.isascii() and (c.isalnum() or c == '_')) else f'_{ord(c):02x}' for c in value).

</details>

#### FMA-MISMATCH-120 — `src--languages--erlang-py--_fingerprint_digest`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_fingerprint_digest.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_fingerprint_digest.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_fingerprint_digest.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_fingerprint_digest.py)
- 触发/冲突：json.dumps without sort_keys=True causes equal tuples with differently-ordered dicts to produce different SHA-256 digests
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- fingerprint is a tuple whose elements are all JSON-serializable (each element is one of: str, int, float, bool, None, list, dict, or tuple — any value that json.dumps can serialize without raising TypeError)
- FMA SPEC post-condition：- Returns a 64-character lowercase hexadecimal string (SHA-256 digest) - The result is deterministic: for any two tuples t1 and t2, t1 == t2 implies _fingerprint_digest(t1) == _fingerprint_digest(t2) - Two tuples that are not equal produce different digests with overwhelming probability (consistent with SHA-256 collision resistance) - The digest is computed from a compact JSON serialization of the tuple (no indentation, no whitespace between keys/values, and Unicode characters preserved without ASCII escaping)
- FMA 推导 actual POST：The function returns a string `d` such that `d` equals `hashlib.sha256(json.dumps(fingerprint, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()`. Given the pre-condition, `json.dumps` does not raise `TypeError`; therefore the function completes normally, has no side effects, and the result is the SHA-256 hexadecimal digest of the compact, non-ASCII-escaped JSON representation of the input tuple.

</details>

#### FMA-MISMATCH-121 — `src--languages--erlang-py--_function_id`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_function_id.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_function_id.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_function_id.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_function_id.py)
- 触发/冲突：Label with a signed arity (e.g. '+2') passes int() validation but the sign persists in the returned identifier.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- uri is a string convertible to a filesystem path - label is a string of the form "<name>/<arity>" where <name> is a non-empty function name and <arity> is a non-negative integer represented as a decimal string; the "/" delimiter must appear at least once when scanning from the right side of label
- FMA SPEC post-condition：- Returns a function identifier string of the form "<module>__<unqualified_name>__<arity>" where: - <module> is the escaped module identifier derived from uri - <unqualified_name> is the escaped function name with any colon-separated module qualifier prefix stripped (unless the name starts with a single-quote character, in which case the full name including the prefix is preserved) - <arity> is the exact decimal string from label (after the last "/"), stripped of any leading sign - The double-underscore ("__") separator between <module>, <unqualified_name>, and <arity> is unambiguous for splitting the identifier back into its three components - Raises ValueError when label does not contain a "/" character, or when the substring after the last "/" is…
- FMA 推导 actual POST：Under the given precondition, the function returns a string `r` constructed as follows: Let `name` and `arity` be the result of `label.rsplit("/", 1)`, i.e. the substring before the last `'/'` and the substring after it. Because the precondition guarantees that `arity` is a nonnegative integer represented as a decimal string, `int(arity)` succeeds and no exception is raised. If `name` contains a colon (`':'`) and does not start with a single quote (`"'"`), let `name'` be the substring after the last colon in `name` (i.e. `name.rsplit(':', 1)[1]`); otherwise let `name' = name`. Let `module = _module_from_uri(uri)`. Then the returned value is `r = _escape_component(module) + "__" + _escape_component(name') + "__" + arity`. The two helper functions `_m…

</details>

#### FMA-MISMATCH-122 — `src--languages--erlang-py--_iter_project_files`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_iter_project_files.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_iter_project_files.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_iter_project_files.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_iter_project_files.py)
- 触发/冲突：When suffixes contains uppercase characters, the all-lowercase extension computed by Path(filename).suffix.lower() never matches, violating the case-insensitive comparison required by the spec.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string representing a valid filesystem path to an existing, accessible directory - suffixes is a non-empty set of strings, each including a leading dot
- FMA SPEC post-condition：- Yields the absolute filesystem path of every regular file found recursively under proj_dir whose filename extension matches a member of suffixes, where the comparison is case-insensitive - Directories whose name matches a member of _SKIP_DIRS (case-insensitive) are excluded from traversal; no file under or within any excluded directory is ever yielded - Every yielded path is an absolute path, resolved by the OS according to the filesystem containing proj_dir - Each path is yielded at most once - Files are yielded in the order produced by a recursive depth-first directory traversal starting from proj_dir - If no regular files under proj_dir have a matching extension, the iterator yields nothing and terminates normally
- FMA 推导 actual POST：The function returns a generator object. When iterated over, the generator yields absolute filesystem paths (as strings) for all regular files found by recursively walking the directory 'proj_dir', subject to these conditions: (1) any directory whose lowercased name appears in the set `_SKIP_DIRS` is excluded from traversal (its entire subtree is skipped); (2) only files whose lowercased extension (including the leading dot) is present in the `suffixes` argument are yielded. The order of yielded paths follows the depthfirst order of `os.walk`. The generator finishes normally (implicit return) after yielding all matching files, raising `StopIteration` on subsequent next() calls. The function raises no exceptions provided the precondition holds (proj_…

</details>

#### FMA-MISMATCH-123 — `src--languages--erlang-py--_module_from_uri`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_module_from_uri.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_module_from_uri.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_module_from_uri.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_module_from_uri.py)
- 触发/冲突：URI with path /__init__.py causes PurePosixPath.stem to return '__init__' which contains '__', violating the spec that the result contains no double-underscore sequence.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- uri is a non-empty string
- FMA SPEC post-condition：- Returns the filename stem (final path component with its last dot-extension removed) of the path portion of uri - Percent-encoded characters in the URI path are decoded before stem extraction - Backslash characters in the decoded path are normalized to forward slash before stem extraction; path components are interpreted using POSIX semantics - Query, fragment, and scheme components of the URI, if present, do not affect the result - The returned string contains no instances of the double-underscore sequence ("__") - The returned string is non-empty
- FMA 推导 actual POST：The function returns a string `result` such that `result` equals `PurePosixPath(unquote(urlparse(uri).path).replace('\\', '/')).stem`. No exceptions are raised. Formally: `result = PurePosixPath(unquote(urlparse(uri).path).replace('\\', '/')).stem` and `isinstance(result, str)`.

</details>

#### FMA-MISMATCH-124 — `src--languages--erlang-py--_next_message`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_next_message.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_next_message.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_next_message.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_next_message.py)
- 触发/冲突：Setting deadline to time.monotonic() with a message already in self._messages causes TimeoutError instead of returning the message.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- deadline is a monotonic clock time in fractional seconds - self._messages is an active queue that receives parsed JSON-RPC messages from the LSP backend
- FMA SPEC post-condition：- Blocks until a message is available from self._messages and returns that message, provided the message is not an instance of BaseException - Raises TimeoutError when the wall-clock monotonic time reaches or exceeds deadline before a message becomes available - Raises RuntimeError when the received message is an instance of BaseException
- FMA 推导 actual POST：After execution, one of three outcomes holds:\n1. (Normal return) The method returns a value `m` that is not an instance of BaseException; `m` was the head of `self._messages` before the call, and `self._messages` now lacks that head element; `time.monotonic() <= deadline`.\n2. (TimeoutError raised) A `TimeoutError` is raised, `time.monotonic() >= deadline`, and `self._messages` is unchanged (no element removed).\n3. (RuntimeError raised) A `RuntimeError` chained from an item `e` is raised; `e` was the head of `self._messages` before the call and is an instance of BaseException; `self._messages` now lacks `e`; `time.monotonic() < deadline`.\nFormally, let `Q` be the pre-state value of `self._messages`, `Q'` the post-state value, and `t` be `time.mon…

</details>

#### FMA-MISMATCH-125 — `src--languages--erlang-py--_persist_analysis`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_persist_analysis.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_persist_analysis.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_persist_analysis.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_persist_analysis.py)
- 触发/冲突：When analysis.edges contains a caller not present in analysis.functions, caller_files.get() returns None, producing null for caller_file instead of a relative path.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a non-empty string that resolves to an absolute filesystem path - fingerprint is a hashable tuple representing the project state fingerprint that uniquely identifies the version of the project being analyzed - analysis is a populated ErlangAnalysis object with non-None .functions, .edges, .spans, and .server_info attributes
- FMA SPEC post-condition：- Creates or overwrites the file .codegraph/erlang_callgraph.json under the directory identified by the resolved absolute path of proj_dir - The output file contains a single JSON object with the following guaranteed keys: "schema_version" (integer, value 1), "status" (string, value "success"), "backend" (string, value "elp"), "server_info" (the contents of analysis.server_info), "elp_command" (a list of strings), and "project_fingerprint" (a string digest) - The JSON object contains a "functions" key whose value is a list of {"id": function_id, "file": relative_path} objects, one per function in analysis.functions, where relative_path is the file path relative to the resolved proj_dir using "/" separators - The JSON object contains an "edges" key w…
- FMA 推导 actual POST：After the function returns (normally or via exception), the following post-condition holds. Let R = os.path.abspath(proj_dir), O_dir = os.path.join(R, '.codegraph'), O_path = os.path.join(O_dir, 'erlang_callgraph.json'). Let D be the dictionary {'schema_version': 1, 'status': 'success', 'backend': 'elp', 'server_info': analysis.server_info, 'elp_command': list(_elp_argv()), 'project_fingerprint': _fingerprint_digest(fingerprint), 'functions': a list of {'id': function_id, 'file': rel_path} for each (path, file_functions) in sorted(analysis.functions.items()) and each (function_id, _source) in file_functions with rel_path = os.path.relpath(path, R).replace(os.sep, '/'), 'edges': a list of {'caller': caller, 'caller_module': caller_module, 'caller_fil…

</details>

#### FMA-MISMATCH-126 — `src--languages--erlang-py--_project_fingerprint`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_project_fingerprint.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_project_fingerprint.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_project_fingerprint.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_project_fingerprint.py)
- 触发/冲突：The hardcoded _PROJECT_CONFIG_FILES tuple ignores project-level build configuration files not in the list (elp.toml, rebar.config, rebar.lock), causing missing file_records entries and a fingerprint invariant violation.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string identifying a filesystem path to an accessible directory
- FMA SPEC post-condition：- Returns a 2-tuple (tool_config, file_records) - tool_config captures the ELP tool invocation configuration; it is identical across calls with the same ELP environment and differs when the configuration changes - file_records is a tuple of (relative_path, file_size_bytes, modification_time_ns) entries, one per file under proj_dir that constitutes Erlang project content Erlang source files, Erlang header files, and project-level build configuration files that exist at the project root and no files outside that set - Each relative_path is relative to the project root, using the OS path separator - No file path appears more than once in file_records - file_records entries are sorted lexicographically by relative_path - The returned fingerprint is dete…
- FMA 推导 actual POST：If the function completes normally (no exception), it returns a tuple `(argv_tuple, records_tuple)` where: - `argv_tuple = _elp_argv()` (a tuple of strings, constant across calls in the same ELP environment). - Let `root = os.path.abspath(proj_dir)`. - Let `S` be the union of: * all absolute paths yielded by `_iter_project_files(root, {".erl", ".hrl"})` (regular files under `root` with `.erl` or `.hrl` extension, accessible at that moment); * those paths `os.path.join(root, name)` for `name` in `_PROJECT_CONFIG_FILES` that pass `os.path.isfile(...)` (i.e., exist as regular files at that moment). - Let `ordered_paths` be the sorted list of the unique elements of `S` in ascending lexical string order. - Then `records_tuple` is a tuple of the same leng…

</details>

#### FMA-MISMATCH-127 — `src--languages--erlang-py--_symbol_line_span`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_symbol_line_span.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_symbol_line_span.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_symbol_line_span.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_symbol_line_span.py)
- 触发/冲突：int(0.5) truncates to 0, causing the code to subtract 1 from end when character is a non-zero float.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- symbol_range is a dict with keys "start" and "end", each a dict containing at least a "line" key whose value is an integer. These represent an LSP Range: a half-open interval [start, end) in 0-based line/character coordinates.
- FMA SPEC post-condition：- Returns a tuple (start, end) where both values are non-negative 0-based integers and start <= end - The tuple represents an inclusive line span: the symbol occupies every line from start through end inclusive - start is the "start" position's line, clamped to a minimum of 0 - When the "end" position's character is non-zero, end is the "end" position's line (clamped to a minimum of start), reflecting that the half-open LSP range includes at least one character on that line - When the "end" position's character is 0 and the end line is strictly greater than start, end is one less than the "end" position's line, because a character of 0 means the symbol occupies no part of that final line
- FMA 推导 actual POST：The function returns a tuple (start, end) of two integers representing a 0-based inclusive line span. start is set to max(0, symbol_range['start']['line']). Let raw_end = max(start, symbol_range['end']['line']) (the end line from the input). If raw_end > start and the 'character' field of the 'end' dictionary is 0 (or missing, defaulting to 0), then end is set to raw_end - 1; otherwise end is raw_end. Formally, given the pre-condition that symbol_range['start'] and symbol_range['end'] each contain an integer 'line', let S = int(symbol_range['start']['line']), E_line = int(symbol_range['end']['line']), E_char = int(symbol_range['end'].get('character', 0)). Then the returned tuple (s, e) satisfies: s = max(0, S); e = (max(s, E_line) - 1) if max(s, E_l…

</details>

#### FMA-MISMATCH-128 — `src--languages--erlang-py--_symbol_range`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_symbol_range.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_symbol_range.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_symbol_range.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_symbol_range.py)
- 触发/冲突：When symbol['location'] is a truthy non-dict (e.g. string), (symbol.get('location') or {}).get('range') raises AttributeError because strings lack .get(); spec requires returning None.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- symbol is a dict representing an LSP symbol, which may be either a DocumentSymbol (containing a "range" key directly) or a SymbolInformation (containing a "location" key which itself contains a "range")
- FMA SPEC post-condition：- Returns the "range" value associated with the symbol, or None when no range can be located - When symbol contains a "range" key, returns its value - When symbol lacks a "range" key but contains a truthy "location" key, returns the "range" value from that location - When symbol lacks both a "range" key and a truthy "location" key containing a "range", returns None - The returned value is the raw range dict without transformation
- FMA 推导 actual POST：The function returns the range of the LSP symbol without modifying `symbol`. If `"range"` is a key in `symbol`, its value is returned. Otherwise, if `symbol` has a key `"location"` whose value is truthy (e.g., a dict), the value of the `"range"` key inside that sub-dict is returned; if `"location"` is missing or falsy, `None` is returned. No exceptions are raised. Formally: post-condition (unchanged(symbol) return = (symbol['range'] if 'range' symbol else (symbol.get('location') or {}).get('range')))

</details>

#### FMA-MISMATCH-129 — `src--languages--erlang-py--batch_extract`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/batch_extract.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/batch_extract.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--batch_extract.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--batch_extract.py)
- 触发/冲突：The _escape_component function produces collisions (e.g., my@func and my_40func both map to my_40func), causing _function_id to generate non-unique identifiers; the seen set then silently drops colliding functions.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a valid filesystem path to a project directory
- FMA SPEC post-condition：- Returns a mapping from absolute .erl file paths to lists of (function_identifier, source_text) tuples - Each function_identifier is a string uniquely naming a top-level Erlang function within its source module - Each source_text is the complete function body as found in the corresponding file - If Erlang-specific analysis is unavailable for the project at proj_dir, returns an empty dict
- FMA 推导 actual POST：The return value is a dictionary. If the analysis of the project directory is successful, the dictionary maps absolute file paths (strings) of Erlang files to lists of (function_id, body) tuples; otherwise, it returns an empty dictionary. Formally, let `R` be the return value. Then `isinstance(R, dict)` is true. For all keys `k` in `R`, `k` is a string representing an absolute file path. For each `k`, `R[k]` is a list of tuples, where each tuple is of type `(str, str)`. The condition `R == {}` holds if and only if the analysis for `proj_dir` could not be performed (i.e., no Erlang sources or tool unavailable); otherwise, `R` is non-empty and contains all extracted function definitions from the project.

</details>

#### FMA-MISMATCH-130 — `src--languages--erlang-py--call_edges`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/call_edges.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/call_edges.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--call_edges.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--call_edges.py)
- 触发/冲突：call_edges returns ErlangAnalysis.edges directly with tuple keys instead of FQN strings, and performs no callee-existence validation.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a valid filesystem path to a project directory
- FMA SPEC post-condition：- Returns a mapping from caller fully-qualified names to sets of callee fully-qualified names - FQNs follow the format: path::components::delimited::by::double::colons, where the last component is the function name - Each callee in the returned graph is a function that exists within the analyzed Erlang project - If Erlang-specific analysis is unavailable for the project at proj_dir, returns an empty dict
- FMA 推导 actual POST：The function returns a dictionary resulting from the call-graph analysis of the effective project root (which may be a subdirectory of `proj_dir` as determined by `_callgraph_project_root`). If the analysis is available, the dictionary contains a module-qualified Erlang call edges mapping (caller to callees); otherwise, it is an empty dictionary. No exceptions are raised; the function always terminates normally under the given pre-condition. Formally: `result = _analysis_or_empty(_callgraph_project_root(proj_dir)).edges` and `isinstance(result, dict)` holds, with `result` being either the nonempty edges dictionary or `{}` when analysis is unavailable.

</details>

#### FMA-MISMATCH-131 — `src--languages--erlang-py--close`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/close.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/close.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--close.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--close.py)
- 触发/冲突：proc.terminate() at line 279 is not wrapped in try/except; if it raises an OSError (e.g., process no longer exists), the exception propagates to the caller, violating the spec's no-exception-leak guarantee.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self._proc is either None or a subprocess.Popen instance that may be running or already terminated
- FMA SPEC post-condition：- If self._proc was None on entry, the method returns immediately with no observable side effects - If self._proc was a running process, it is no longer executing after the method returns - The subprocess is first asked to shut down gracefully; if it does not exit within a bounded interval, it is forcibly terminated; if it still does not exit after a second bounded interval, it is forcibly killed - All I/O streams connected to the subprocess (stdin and stdout) are closed before the method returns, regardless of whether individual shutdown or stream-close operations succeed or fail - self._proc is set to None - No exception raised during any shutdown or cleanup step propagates to the caller
- FMA 推导 actual POST：self._proc is None. If the pre-call value of self._proc (denoted old(self._proc)) was a subprocess.Popen instance p, then p.stdin and p.stdout have been closed (or were already None). Additionally, if p was still running at the beginning of the method (p.poll() returned None), then p has been sent a shutdown request and an exit notification, and an attempt to wait for its termination was made; if the wait timed out, p.terminate() was called and another wait attempted; if that also timed out, p.kill() was called. No guarantees are made about whether p has fully terminated by the end of the method. These side effects are guaranteed even if an exception escapes the method, because they are performed in a finally block.

</details>

#### FMA-MISMATCH-132 — `src--languages--erlang-py--function_spans`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/function_spans.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/function_spans.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--function_spans.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--function_spans.py)
- 触发/冲突：When ELP backend is available and a file has been indexed but contains no function definitions, spans.get() returns None instead of the spec-required empty list [].
- 成因复核：源码 docstring 规定 None 同时表示未索引或无函数，并触发 regex fallback；SPEC 擅自要求 []。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a non-empty string path to the project root directory - filepath is a non-empty string path to a source file
- FMA SPEC post-condition：- When the Erlang Language Platform (ELP) backend is available and has indexed filepath, returns a list of (func_name, start_line, end_line) tuples for every function definition found in the file - start_line and end_line are 0-based inclusive line numbers within the file - Returns None when the ELP backend is unavailable or filepath has not been indexed, signaling the caller to fall back to a regex-based extractor - The returned list is empty when filepath contains no function definitions and the backend is available
- FMA 推导 actual POST：The function computes path = os.path.abspath(filepath) and returns _analysis_or_empty(proj_dir).spans.get(path). The return value is either a list of (func_name: str, start_line: int, end_line: int) tuples, each representing a function's 0based inclusive sourceline span, or None if the path is not present in the spans mapping. Formally: let p = os.path.abspath(filepath), s = _analysis_or_empty(proj_dir).spans. Then result = s.get(p). result is None (result is a list t result : t = (name, start, end) name is str start, end start end).

</details>

#### FMA-MISMATCH-133 — `src--languages--erlang-py--initialize`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/initialize.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/initialize.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--initialize.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--initialize.py)
- 触发/冲突：The deadline is computed after request/notify/open_document instead of at the call start, allowing the method to wait longer than self.timeout seconds from entry.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self is an ElpClient instance with a running LSP backend process and an open JSON-RPC communication channel - self.root_uri is a non-empty string, self.proj_dir is a non-empty string, and self.timeout is a positive number - bootstrap_path is a non-empty string
- FMA SPEC post-condition：- Sends an LSP "initialize" JSON-RPC request containing the process PID, client identification ("fm-agent", "0.1.0"), the root URI, a workspace folder entry with the root URI and the base name of self.proj_dir, and a capabilities object advertising hierarchical documentSymbol support with server-status and workspace-configuration notifications enabled - Sends an "initialized" JSON-RPC notification after receiving the initialization response - Opens the document at bootstrap_path in the LSP backend, providing bootstrap_source as the document text when bootstrap_source is a non-None string, or signalling the backend to read the file from disk when bootstrap_source is None - Blocks, processing every server message received, until the server-reported st…
- FMA 推导 actual POST：After the `initialize` method finishes execution, one of the following two outcomes holds: 1. **Exceptional termination**: An exception (for example a `TimeoutError` from `self._next_message`) was raised. In this case, the method does not return a value. The LSP communication and client state may be partially updated (e.g., the `initialize` request and/or `initialized` notification may have been sent, and `open_document` may have been called), but no final guarantees are providedthe server status might not have reached `running` and the deadline may have expired. 2. **Normal return**: The method returned a value (referred to as `server_info`) without raising an exception. In this case the following conditions hold: - The `initialize` JSONRPC request…

</details>

#### FMA-MISMATCH-134 — `src--languages--erlang-py--position_to_offset`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/position_to_offset.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/position_to_offset.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--position_to_offset.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--position_to_offset.py)
- 触发/冲突：position_to_offset adds character index to byte offset base, producing wrong byte offset for lines with multi-byte UTF-8 characters such as 'é'.
- 成因复核：checker 把 Python str 下标误当 UTF-8 byte offset。line_offsets 由 len(str) 构造，最终也用于 str 切片；对 'éa' 返回 1 是正确的字符下标，probe 的 expected=2 使用了错误 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self is a _SourceIndex instance whose .lines attribute is a list of strings, .line_offsets is a list of integers, and .source is a string - position is a dict with keys 'line' (int, 0-based) and 'character' (int, 0-based)
- FMA SPEC post-condition：- Returns a 0-based offset into self.source corresponding to the given (line, character) position, where character is measured in UTF-16 code units (1 unit per BMP character, 2 units per supplementary-plane character with code point > U+FFFF) - When position["line"] is not less than len(self.lines), returns len(self.source) - When position["character"] exceeds the total UTF-16 code units of the line at position["line"], returns the byte offset at the end of that line - Negative line or character values in position are treated as 0
- FMA 推导 actual POST：The method returns an integer offset `r` into `self.source` such that: let `line_num = max(0, int(position.get("line", 0)))` and `char_target = max(0, int(position.get("character", 0)))`. If `line_num >= len(self.lines)`, then `r = len(self.source)`. Otherwise, let `line = self.lines[line_num]` and `base = self.line_offsets[line_num]`. Then `r = base + i`, where `i` is the largest integer in `[0, len(line)]` satisfying that the total UTF16 code units of the first `i` characters of `line` (with a character counting as 2 units if `ord(char) > 0xFFFF`, else 1 unit) does not exceed `char_target`. Formally: let `units(s, k) = _{j=0}^{k-1} (2 if ord(s[j]) > 0xFFFF else 1)`. Then `i = max{ k | 0 k len(line) units(line, k) char_target }`. Thus, if the targe…

</details>

#### FMA-MISMATCH-135 — `src--languages--erlang-py--request`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/request.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/request.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--request.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--request.py)
- 触发/冲突：Passing a list as the params argument sends a JSON-RPC params array instead of the spec-required params object (dict).
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self is an ElpClient instance with an active LSP JSON-RPC communication channel (stdin open for writes via self._send, stdout readable for response parsing via self._wait_for_response) - self.timeout is a positive number representing the maximum allowed wall-clock duration in seconds - self._next_id is an integer - method is a non-empty string
- FMA SPEC post-condition：- Sends a JSON-RPC 2.0 request to the LSP backend containing the given method, a params object (an empty dict when params is None), and a unique monotonically increasing integer request id - Returns the response result extracted from the backend's JSON-RPC response when the request succeeds before the deadline - When the backend returns a "content modified" error (signaling the document was modified during indexing), the identical request is retried to the same backend after a delay that grows exponentially with each retry attempt, bounded above by 5.0 seconds and by the remaining time before the deadline - Raises RuntimeError when the backend repeatedly returns "content modified" errors for all allowed retry attempts - Raises TimeoutError when self…
- FMA 推导 actual POST：After the call, let k be the number of attempts made (number of times _send was called). Then self._next_id = old self._next_id + k. Exactly k JSON-RPC request messages were sent, each with unique id from the range [old_id, old_id + k - 1], method 'method', and params equal to {} if the input params was None, else the given params. The deadline was deadline = time.monotonic() + self.timeout captured at start. If the function returns a value result, then there exists an attempt index i (1 i _MAX_CONTENT_MODIFIED_RETRIES) with k = i such that: - _wait_for_response(old_id + i - 1, deadline) returned result; - for all j < i, _wait_for_response(old_id + j - 1, deadline) raised _ContentModifiedError, retries remained, remaining time > 0, and time.sleep(mi…

</details>

#### FMA-MISMATCH-136 — `src--languages--erlang-py--run`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/run.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/run.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--run.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--run.py)
- 触发/冲突：A mock stream returning empty bytes on readline() triggers an EOFError which is caught by except BaseException, causing run() to return in violation of the spec.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self._stream is an open, readable byte stream sourced from the stdout of a running ELP (Erlang Language Platform) process operating in LSP JSON-RPC mode. - self._messages is a thread-safe queue that accepts any Python object.
- FMA SPEC post-condition：- This method never returns; it runs an indefinite loop that consumes LSP JSON-RPC messages from self._stream and places decoded message objects or termination exceptions onto self._messages. - Each complete message consists of a header block (ASCII key-value lines terminated by an empty line) containing a Content-Length field, followed by a body of exactly Content-Length bytes containing a UTF-8-encoded JSON payload. - For each complete message fully received: the JSON payload is decoded and the resulting Python object is placed onto self._messages. - When self._stream reaches EOF before the empty-line terminator of the header block: an EOFError is placed onto self._messages. - When self._stream delivers fewer than Content-Length payload bytes afte…
- FMA 推导 actual POST：After the `run` method returns (which can only happen if an exception terminates the infinite loop), `self._messages` contains all Python objects that were successfully parsed from well-formed JSON-RPC payloads received before the error, followed by the exception instance that caused termination. The stream may be in an inconsistent or closed state. The original contents of the queue (if any) remain before the newly enqueued items. Formally, let `Q_before` be the sequence of items in `self._messages` before `run()` is called. After `run()` returns, there exist sequences `M` (zero or more valid parsed JSON objects) and a single item `E` such that the queues contents are `Q_before ++ M ++ [E]`, where `E` is an instance of `BaseException` (specifically…

</details>

#### FMA-MISMATCH-242 — `src--languages--erlang-py--_analyze_project_uncached`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/_analyze_project_uncached.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/_analyze_project_uncached.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--_analyze_project_uncached.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--_analyze_project_uncached.py)
- 触发/冲突：The early return for empty directories constructs ErlangAnalysis without explicitly passing spans/server_info, but dataclass defaults fill both attributes.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a non-empty string representing a filesystem path
- FMA SPEC post-condition：- Returns an ErlangAnalysis object whose .functions attribute is a dict mapping each .erl file absolute path to a list of (function_id, source_text) tuples, where function_id is a canonical string identifier and source_text is the source code of that function - Returns an ErlangAnalysis whose .edges attribute is a dict mapping (function_id, caller_module) tuples to sets of callee function_ids - Returns an ErlangAnalysis whose .spans attribute is a dict mapping each .erl file absolute path to a list of (function_id, start_line, end_line) tuples, where start_line and end_line are 1-based inclusive line numbers - Returns an ErlangAnalysis whose .server_info attribute is populated from the ELP server initialization response - When no .erl files exist un…
- FMA 推导 actual POST：After execution of the function _analyze_project_uncached, the program state is one of the following: (1) If _erlang_files(proj_dir) returns an empty list, the function returns early with an ErlangAnalysis built from empty functions and empty edges. (2) If _erlang_files(proj_dir) returns a nonempty list but any operation (reading a source file with Path.read_text, initializing the ElpClient, or making a client request) raises an exception, that exception propagates to the caller; no ErlangAnalysis is returned. (3) Otherwise, all files are processed via ElpClient and the function returns an ErlangAnalysis containing the functions and edges dictionaries built from the document symbols of the .erl files. During processing, malformed function symbols (t…

</details>

#### FMA-MISMATCH-243 — `src--languages--erlang-py--build`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/build.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/build.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--build.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--build.py)
- 触发/冲突：Empty source produces empty line_offsets but position_to_offset guard prevents IndexError when accessing position (0,0).
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- source is a string containing the full text content of a source file - cls is a class type whose constructor accepts keyword arguments for initializing a source index
- FMA SPEC post-condition：- Returns an instance of cls initialized from source - The returned instance supports mapping a (start_line, end_line) line-number pair to the substring of source spanning from the start line (inclusive) to the end line (exclusive) - The returned instance supports converting a (line, character) position to a 0-based byte offset within source - Line-break characters in source are preserved exactly as they appear in the input string
- FMA 推导 actual POST：After execution, the method returns an instance obj of cls, such that: obj.source == source, obj.lines == source.splitlines(keepends=True), and obj.line_offsets is a list with len(obj.line_offsets) == len(obj.lines) where obj.line_offsets[0] == 0 and for all i in range(1, len(obj.line_offsets)): obj.line_offsets[i] == obj.line_offsets[i-1] + len(obj.lines[i-1]).

</details>

#### FMA-MISMATCH-244 — `src--languages--erlang-py--open_document`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/erlang-py/open_document.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/erlang-py/open_document.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--erlang-py--open_document.md) · [probe](../fm_agent/bug_validation/probe_src--languages--erlang-py--open_document.py)
- 触发/冲突：open_document calls self.notify without explicit channel check, but self.notify delegates to self._send which checks self._proc is None and raises RuntimeError
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- self is an ElpClient instance with an open LSP communication channel to the backend - path is a non-empty string
- FMA SPEC post-condition：- Sends a `textDocument/didOpen` LSP notification to the backend for the document at the absolute, resolved path derived from path - The notification URI is the `file://` URI of the resolved path - When source is a non-None string, the notification carries source as the document text - When source is None, the notification carries the file contents at the resolved path as the document text - The document is registered with language identifier "erlang" and version 1 - Returns None upon successful notification delivery - Raises an exception when source is None and the file at the resolved path cannot be read, or when the LSP communication channel is not open
- FMA 推导 actual POST：The code block finishes execution either normally or by raising an exception. If it finishes normally, a 'textDocument/didOpen' notification has been sent to the LSP backend with parameters: 'textDocument.uri' = Path(path).resolve().as_uri(), 'textDocument.languageId' = 'erlang', 'textDocument.version' = 1, 'textDocument.text' = (source if source is not None else the text content read from the resolved file using UTF-8 encoding and 'replace' error handling). The self object remains an ElpClient instance with the open communication channel. If an exception is raised, no notification was sent; the exception originates from either the path resolution (Path(path).resolve()) or, when source is None, the file read operation (document.read_text(...)). Form…

</details>

### `src--languages--go-py`

#### FMA-MISMATCH-137 — `src--languages--go-py--function_spans`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/go-py/function_spans.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/go-py/function_spans.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--go-py--function_spans.md) · [probe](../fm_agent/bug_validation/probe_src--languages--go-py--function_spans.py)
- 触发/冲突：Passing None as proj_dir causes CodeGraphExtractor.from_proj_dir to raise TypeError via os.path.abspath(None), which propagates instead of returning None as the spec requires.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a non-empty string referencing a project directory. - filepath is a string identifying a Go source file within that project.
- FMA SPEC post-condition：- Returns a list of (function_name, start_line, end_line) tuples for every top-level function definition found in the file at filepath. - start_line and end_line are 0-indexed and inclusive. - The returned list is ordered by function occurrence within the file. - Returns None when the codegraph backend is unavailable or does not index the file at filepath.
- FMA 推导 actual POST：After the function call, either an exception was raised (due to an error in `CodeGraphExtractor.from_proj_dir(proj_dir)` or, if that succeeded and returned a truthy extractor `cg`, from `cg.get_function_spans("go", filepath)`), or the function returned a value. If it returned, then `cg = CodeGraphExtractor.from_proj_dir(proj_dir)` (without raising) and: if `cg` is falsy (i.e., `None`), the return value is `None`; otherwise, the return value is the list of `(name, start_idx, end_idx)` tuples produced by `cg.get_function_spans("go", filepath)` (which also completed without exception). Format: formal logic: ( E : Exception) ( (E raised during `CodeGraphExtractor.from_proj_dir(proj_dir)`) ( cg : cg = `CodeGraphExtractor.from_proj_dir(proj_dir)` complete…

</details>

### `src--languages--java-py`

#### FMA-MISMATCH-138 — `src--languages--java-py--function_spans`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/java-py/function_spans.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/java-py/function_spans.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--java-py--function_spans.md) · [probe](../fm_agent/bug_validation/probe_src--languages--java-py--function_spans.py)
- 触发/冲突：function_spans delegates to cg.get_function_spans without reordering, so an unordered backend result violates the spec's 'ordered by appearance' guarantee.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string path to a valid project root directory containing Java source files. - filepath is a string path to a Java source file (.java) located within proj_dir.
- FMA SPEC post-condition：- If the codegraph backend is available and indexes the given Java file, returns a list of (name, start_idx, end_idx) tuples, one per function definition found in the file, ordered by appearance in the source. Each tuple contains the function name as a string and 0-indexed inclusive line indices delimiting the function body. - If the codegraph backend is unavailable or does not index the file, returns None, signalling that the caller must fall back to regex-based extraction.
- FMA 推导 actual POST：The function returns either None or a list of (name: str, start_idx: int, end_idx: int) tuples. It returns None if the code graph backend cannot be initialised for the project directory (i.e. CodeGraphExtractor.from_proj_dir returns None) or if the Java source file is not indexed by the backend. Otherwise it returns a list where each tuple gives the function name, inclusive 0indexed start line and inclusive 0indexed end line of a function definition in the file. Formal postcondition: result = ( let cg = CodeGraphExtractor.from_proj_dir(proj_dir) ; if cg = None then None else cg.get_function_spans('java', filepath) ). Therefore (result = None) (cg None result = cg.get_function_spans('java', filepath) (result = None (result is a list of (str, int, int…

</details>

### `src--languages--registry-py`

#### FMA-MISMATCH-139 — `src--languages--registry-py--batch_extract_all`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/registry-py/batch_extract_all.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/registry-py/batch_extract_all.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--registry-py--batch_extract_all.md) · [probe](../fm_agent/bug_validation/probe_src--languages--registry-py--batch_extract_all.py)
- 触发/冲突：batch_extract_all merges handler results via funcs.update(result) without normalizing file paths, so a handler returning a non-normalized absolute path (e.g. /tmp/a/../b/file.py) appears verbatim in funcs instead of the normalized form.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string representing a path to an existing directory. - REGISTRY is a non-empty dict mapping language key strings to LanguageHandler objects, each exposing a batch_extract callable that accepts a single directory-path argument.
- FMA SPEC post-condition：- Returns a tuple (funcs, langs) where: funcs is a dict mapping normalized absolute file paths (str) to lists of (func_name: str, func_body: str) tuples. langs is a set of language key strings. - Every registered handler's batch_extract is invoked exactly once with proj_dir as its sole argument. - For each handler whose batch_extract returns a truthy dict result: every key-value pair in that dict is included in funcs (with later handlers overwriting earlier entries for duplicate keys), and the handler's language key is included in langs. - A handler whose batch_extract returns a falsy result contributes nothing to funcs or langs. - If no handler returns a truthy result: funcs is an empty dict and langs is an empty set. - If any handler's batch_extra…
- FMA 推导 actual POST：If any handler.batch_extract(proj_dir) raises an exception, that exception propagates and the function terminates abnormally. Otherwise (all calls complete without raising), the function returns a tuple (funcs, langs) where: - funcs: dict | None? Actually funcs is always a dict (initialized as {}). It contains exactly the union of all key-value pairs from the results of handler.batch_extract(proj_dir) for each (lang, handler) in REGISTRY.items() for which the returned value was truthy (i.e., a nonempty dict mapping absolute file paths to lists of (func_name, body) tuples). If multiple handlers produce truthy results that share a key (absolute file path), the value from the last handler in REGISTRYs iteration order takes precedence (because dict.upda…

</details>

#### FMA-MISMATCH-140 — `src--languages--registry-py--function_spans_for_file`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/registry-py/function_spans_for_file.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/registry-py/function_spans_for_file.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--registry-py--function_spans_for_file.md) · [probe](../fm_agent/bug_validation/probe_src--languages--registry-py--function_spans_for_file.py)
- 触发/冲突：When handler.function_spans() raises an exception (e.g. codegraph DB corruption), the exception propagates through function_spans_for_file uncaught instead of returning None for the caller to fall back to regex extraction.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string - filepath is a string - lang_key is a string
- FMA SPEC post-condition：- When lang_key is not present in REGISTRY, returns None - When lang_key is present in REGISTRY, returns the registered handler's function_spans result for (proj_dir, filepath) without modification - A non-None return value is a list where each element is a tuple (name, start, end): * name is the function name string * start is the 0-based inclusive start-line index of a top-level function body * end is the 0-based inclusive end-line index of a top-level function body - None signals codegraph unavailability; the caller must fall back to regex extraction
- FMA 推导 actual POST：Natural language: If `lang_key` is not present in `REGISTRY` (i.e., `REGISTRY.get(lang_key)` returns `None`), the function returns `None` immediately. Otherwise, it delegates to `handler.function_spans(proj_dir, filepath)` and returns whatever that call returns. The return value is therefore either `None` (when the handler does not support the file, the file is not in the codegraph index, or the language is unregistered) or a list of tuples `(func_name, start_idx, end_idx)` where `start_idx` and `end_idx` are 0based inclusive line numbers; `handler.function_spans` never returns anything else according to its specification. If the call to `handler.function_spans` raises an exception, that exception is not caught and propagates to the caller; in that…

</details>

### `src--languages--rust-py`

#### FMA-MISMATCH-141 — `src--languages--rust-py--batch_extract`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/rust-py/batch_extract.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/rust-py/batch_extract.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--rust-py--batch_extract.md) · [probe](../fm_agent/bug_validation/probe_src--languages--rust-py--batch_extract.py)
- 触发/冲突：batch_extract delegates to cg.get_functions_by_file without filtering out files that contain zero functions, returning dictionaries with empty lists that violate the non-empty-list specification.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string representing a filesystem path to a project directory
- FMA SPEC post-condition：- Returns a dictionary where each key is an absolute filesystem path (str) to a Rust source file located within or under the project directory - Each value is a non-empty list of (str, str) tuples: the first element is a function name declared in that file, and the second element is the complete source text of the function body - A source file containing N detected functions produces N entries in its value list - Returns an empty dictionary when no Rust codegraph backend is available for the given project
- FMA 推导 actual POST：If the function returns normally, it yields a dictionary. Calling CodeGraphExtractor.from_proj_dir(proj_dir) either returns a configured instance (cg None) or None. When cg is None the result is {}. When cg is not None the result is cg.get_functions_by_file("rust", proj_dir), a dict mapping each absolute path of a Rust source file under proj_dir to a list of (function_name, function_body) tuples. No sideeffects on proj_dir occur. Any exception raised by from_proj_dir or get_functions_by_file propagates uncaught to the caller, and the function does not return a value in that case.

</details>

#### FMA-MISMATCH-248 — `src--languages--rust-py--function_spans`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/rust-py/function_spans.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/rust-py/function_spans.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--rust-py--function_spans.md) · [probe](../fm_agent/bug_validation/probe_src--languages--rust-py--function_spans.py)
- 触发/冲突：Codegraph available but filepath not indexed: function_spans delegates to get_function_spans which correctly returns None when no matching rows found in the codegraph DB for the given filepath and language.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a filesystem path to a project directory - filepath is a path to a single Rust source file within the project
- FMA SPEC post-condition：- If codegraph is available and indexes filepath: returns a list of (function_name, start_line, end_line) tuples, one per top-level function declared in the file. Each start_line and end_line is a 0-indexed inclusive line number bounding the function's source span. - If filepath contains no top-level function declarations: returns an empty list. - If codegraph is unavailable or does not index filepath: returns None. A None return signals the caller to fall back to regex-based extraction.
- FMA 推导 actual POST：The function returns either None (if the CodeGraphExtractor cannot be initialized for the project) or a list of tuples `(name: str, start_idx: int, end_idx: int)` for each top-level Rust function in `filepath`, where `start_idx` and `end_idx` are 0indexed inclusive line numbers. No side effects occur. Formally: let `cg = CodeGraphExtractor.from_proj_dir(proj_dir)`; then `(cg = None result = None) (cg None result = cg.get_function_spans("rust", filepath) result is a list of (name, start_idx, end_idx) with 0-indexed inclusive line indices)`. The preconditions of `get_function_spans` are satisfied because `"rust"` is a supported language and `filepath` lies within the project indexed by `cg`.

</details>

### `src--languages--typescript-py`

#### FMA-MISMATCH-142 — `src--languages--typescript-py--batch_extract`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/typescript-py/batch_extract.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/typescript-py/batch_extract.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--typescript-py--batch_extract.md) · [probe](../fm_agent/bug_validation/probe_src--languages--typescript-py--batch_extract.py)
- 触发/冲突：A TypeScript project containing nested function declarations causes batch_extract to return nested functions alongside top-level functions, violating the specification that only top-level functions should be returned.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a filesystem path to a project directory
- FMA SPEC post-condition：- If codegraph is available: returns a dict whose keys are absolute file paths to TypeScript source files within proj_dir, and whose values are lists of (function_name, function_body) tuples for every top-level function declared in the corresponding file. - Each function_name is the identifier of the function declaration. - Each function_body is the full source text of the function definition. - If proj_dir contains no TypeScript files with top-level functions: returns an empty dict. - If codegraph is unavailable: returns an empty dict {}.
- FMA 推导 actual POST：Returns a dictionary. If cg = CodeGraphExtractor.from_proj_dir(proj_dir) is not None, the result is cg.get_functions_by_file('typescript', proj_dir), i.e., a dict mapping absolute file paths (str) of TypeScript source files under proj_dir to lists of (function_name: str, function_body: str) tuples. Otherwise, returns an empty dict {}.

</details>

#### FMA-MISMATCH-143 — `src--languages--typescript-py--call_edges`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/typescript-py/call_edges.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/typescript-py/call_edges.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--typescript-py--call_edges.md) · [probe](../fm_agent/bug_validation/probe_src--languages--typescript-py--call_edges.py)
- 触发/冲突：CodeGraphExtractor.get_call_edges includes callee stems for functions in symlinked external files that are not part of the project source, violating the spec requirement that every callee correspond to a function reachable from a project TypeScript source file.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a path to a project root directory containing TypeScript source files
- FMA SPEC post-condition：- When a codegraph backend initializes successfully from proj_dir, returns a dict whose keys are (caller_stem, caller_module) pairs where caller_stem is a functionlevel identifier and caller_module is the containing module identifier and whose values are sets of callee function stem strings that the corresponding caller directly invokes within the project's TypeScript source - When no codegraph backend is available, returns None - Every callee stem in the returned value sets corresponds to a function reachable from at least one TypeScript source file in the project
- FMA 推导 actual POST：If the function returns normally, it returns either None (when no compatible codegraph backend exists for proj_dir) or a dictionary mapping each caller identity tuple (caller_stem, caller_module) to the set of callee stem strings for all call relationships detected in the TypeScript source files of proj_dir. If an exception is raised by CodeGraphExtractor.from_proj_dir or CodeGraphExtractor.get_call_edges, the function does not return normally and propagates the exception.

</details>

#### FMA-MISMATCH-144 — `src--languages--typescript-py--function_spans`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/typescript-py/function_spans.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/typescript-py/function_spans.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--typescript-py--function_spans.md) · [probe](../fm_agent/bug_validation/probe_src--languages--typescript-py--function_spans.py)
- 触发/冲突：When a TypeScript file indexed by codegraph contains no function declarations, function_spans returns None instead of the non-empty list required by the specification.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a path to a project root directory - filepath is a path to a single TypeScript source file residing under proj_dir
- FMA SPEC post-condition：- When a codegraph backend initializes successfully from proj_dir AND the backend indexes the TypeScript file at filepath, returns a nonempty list of (name, start_idx, end_idx) tuples covering every function defined in the file, where name is the function's declared name as a string, and start_idx and end_idx are 0indexed inclusive line positions delimiting the function body - When no codegraph backend is available, or the backend exists but does not index the file at filepath, returns None - The order of tuples in the returned list corresponds to the definition order of functions in the source file
- FMA 推导 actual POST：The function returns a value R satisfying: if CodeGraphExtractor.from_proj_dir(proj_dir) is None, then R is None; otherwise, let cg be the returned instance. If cg.get_function_spans('typescript', filepath) returns a list L of (name, start_idx, end_idx) tuples (where name is a string, start_idx and end_idx are nonnegative integers giving 0indexed inclusive line indices), then R = L; else (when the file is not indexed by the backend) R = None. No exceptions are raised; the inputs proj_dir and filepath remain unchanged.

</details>

### `src--llm_client-py`

#### FMA-MISMATCH-145 — `src--llm_client-py--_http_status_from_exc`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/llm_client-py/_http_status_from_exc.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/llm_client-py/_http_status_from_exc.json) · [具体 bug 报告](../fm_agent/bug_validation/src--llm_client-py--_http_status_from_exc.md) · [probe](../fm_agent/bug_validation/probe_src--llm_client-py--_http_status_from_exc.py)
- 触发/冲突：Deleting the 'code' attribute from an urllib.error.HTTPError instance causes exc.code access to raise AttributeError instead of returning None.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- exc is any object
- FMA SPEC post-condition：- If exc is an instance of urllib.error.HTTPError, returns the integer HTTP status code stored on exc - If exc is not an instance of urllib.error.HTTPError, returns None - Never raises an exception regardless of input
- FMA 推导 actual POST：The function returns the value of exc.code if exc is an instance of urllib.error.HTTPError; otherwise, it returns None. No side effects occur, and no exceptions are raised. Formal: (isinstance(exc, urllib.error.HTTPError) result = exc.code) (isinstance(exc, urllib.error.HTTPError) result = None)

</details>

#### FMA-MISMATCH-146 — `src--llm_client-py--_llm_json_call`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/llm_client-py/_llm_json_call.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/llm_client-py/_llm_json_call.json) · [具体 bug 报告](../fm_agent/bug_validation/src--llm_client-py--_llm_json_call.md) · [probe](../fm_agent/bug_validation/probe_src--llm_client-py--_llm_json_call.py)
- 触发/冲突：When trace_dir is None, record_llm_exchange is a silent no-op that produces no durable record, violating the spec requirement that every LLM attempt must produce a durable outcome record.
- 成因复核：trace_dir=None 时不落盘是 trace_writer 的显式 no-op 协议；SPEC 却要求在没有目标目录时仍有持久记录，这是不可满足契约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- client can send conversation messages for the given model and return a text response - model is a non-empty string identifying the LLM to use - messages is a list of conversation message dicts, each with at least "role" and "content" keys - validator is a callable that accepts a parsed JSON value (dict, list, str, int, float, bool, or None) and returns a result or raises ValueError with an error message - schema_d…
- FMA SPEC post-condition：- Up to max_retries attempts are made to obtain a JSON response from the LLM that validator accepts - On each attempt, the current conversation messages are sent to the LLM and a text response is received; if sending fails, the failure is durably recorded and the exception is re-raised without further retries - Each received text response is parsed as JSON; if parsing succeeds and validator returns a value without raising ValueError, that value becomes the function result; the successful outcome is durably recorded - If parsing fails or validator raises ValueError, the conversation is extended with the rejected response text and a corrective user message that includes the error description and schema_description; the failed outcome is durably record…
- FMA 推导 actual POST：Let N = max_retries. For each attempt i in 1..N, let S_i be true if _retry_create succeeds (returns (response, usage)), let P_i be true if _parse_json_response(response) succeeds without ValueError, and let V_i be the final validation result (if P_i then V_i = validator(parsed_json) which does not raise ValueError). The function execution guarantees: - (Exception) k [1,N] (S_k ( j < k, S_j (P_j V_j is valid without ValueError))) the function raises the same exception as _retry_create on attempt k. - (Success) k [1,N] (S_k P_k validator returns V_k without ValueError j < k, (S_j (P_j V_j is valid without ValueError))) the function returns V_k (which may be None if validator returns None). - (Exhausted) ( i [1,N], S_i (P_i validator returns a value wi…

</details>

#### FMA-MISMATCH-147 — `src--llm_client-py--_matches_inject_target`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/llm_client-py/_matches_inject_target.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/llm_client-py/_matches_inject_target.json) · [具体 bug 报告](../fm_agent/bug_validation/src--llm_client-py--_matches_inject_target.md) · [probe](../fm_agent/bug_validation/probe_src--llm_client-py--_matches_inject_target.py)
- 触发/冲突：URL schemes other than http/https (e.g. ftp://) are not treated as absolute URL prefixes, causing incorrect hostname matching instead of string prefix matching.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- url is a non-empty string whose trailing slash characters have been removed by the caller - target is a non-empty string from the provider-specific set of URL patterns requiring user-id injection
- FMA SPEC post-condition：- When target is an absolute URL prefix, returns True if and only if url begins with target as a string prefix covering all paths at or beneath the target's path hierarchy - When target is a hostname, returns True if and only if the hostname that url refers to is either exactly equal to target, or is a subdomain of target (the hostname ends with a period followed by target) - Returns False when url does not satisfy either matching rule including when url refers to a hostname unrelated to target, or when url cannot be resolved to a hostname while target is a hostname
- FMA 推导 actual POST：The function returns a boolean. If the lowercased target starts with 'http://' or 'https://', the result is url.startswith(target) (case-sensitive). Otherwise, if parsing the URL with urllib.parse.urlparse raises any exception, the result is False. If no exception occurs, let host be the extracted hostname (or the empty string if hostname is None); the result is True if host equals target exactly, or if host ends with '.' + target; otherwise False. Formally, let R be the return value. Then (target.lower().startswith(('http://', 'https://')) R = url.startswith(target)) (target.lower().startswith(('http://', 'https://')) (exception during urllib.parse.urlparse(url) R = False) (no exception R (host == target host.endswith('.' + target)) with host = (ur…

</details>

#### FMA-MISMATCH-148 — `src--llm_client-py--_messages_to_anthropic`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/llm_client-py/_messages_to_anthropic.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/llm_client-py/_messages_to_anthropic.json) · [具体 bug 报告](../fm_agent/bug_validation/src--llm_client-py--_messages_to_anthropic.md) · [probe](../fm_agent/bug_validation/probe_src--llm_client-py--_messages_to_anthropic.py)
- 触发/冲突：A single system message with surrounding whitespace is not stripped, violating the spec requirement that system_text always has leading/trailing whitespace removed.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- messages is a list of dictionaries, each optionally containing keys "role" and "content".
- FMA SPEC post-condition：- Returns a pair (system_text, anthropic_messages) where: - anthropic_messages is a list of dicts, each with exactly the keys "role" and "content", containing every input message whose role is "user" or "assistant", in their original relative order. - For an input message whose "content" value is a string, it passes through unchanged. When "content" is a list of dicts (content blocks), it is replaced with a single string formed by joining the "text" value of each dict in the list with newline separators. A dict in the list without a "text" key contributes an empty string at that position. - system_text is the empty string when no input message has role "system". When one or more system-role messages are present, system_text is the concatenation of t…
- FMA 推导 actual POST：The function either raises a TypeError if any message's 'content' is neither a string nor an iterable, or returns normally with a tuple (system_text, out). When returning normally, system_text is a string composed of the processed 'content' from all messages where role is 'system', concatenated with '\n\n' separator when multiple, with stripping applied only after concatenations (i.e., if there is exactly one system message, its content is used as is; otherwise the concatenated result is stripped). For each system message, if its content is a string it is used directly; if it is a list (or iterable) of dictionaries, it is flattened into a newline-separated string of their 'text' values, ignoring non-dict items. Similarly, out is a list of dictionari…

</details>

#### FMA-MISMATCH-149 — `src--llm_client-py--_read_error_body`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/llm_client-py/_read_error_body.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/llm_client-py/_read_error_body.json) · [具体 bug 报告](../fm_agent/bug_validation/src--llm_client-py--_read_error_body.md) · [probe](../fm_agent/bug_validation/probe_src--llm_client-py--_read_error_body.py)
- 触发/冲突：When exc.read() raises a BaseException subclass (not an Exception subclass), the except Exception clause does not catch it, violating the spec's 'any exception' tolerance.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- exc is an object whose read() method, called with no arguments, returns the raw response body as bytes, or raises any exception - limit is a positive integer (default 800) specifying the maximum character count of the returned string
- FMA SPEC post-condition：- Returns the raw HTTP response body decoded as UTF-8 text, with undecodable bytes replaced by the Unicode replacement character (U+FFFD), and leading/trailing whitespace stripped - When the decoded, stripped text exceeds limit characters, the returned string is truncated to the first limit characters and suffixed with a single "" (ellipsis) character - Returns an empty string when: read() raises any exception, read() returns a falsy value, or the decoded text after stripping is empty - The function tolerates any exception type from read() callers can invoke it on any exception object without risk of secondary failures
- FMA 推导 actual POST：If calling exc.read() raises an exception or returns a falsy value (e.g., None or empty bytes), the function returns an empty string. Otherwise, let raw_bytes be the returned bytes. The function decodes raw_bytes using UTF-8 with replacement characters for errors, strips surrounding whitespace, yielding text. It then returns text if its length limit; otherwise returns the first limit characters of text followed by ''. Formally: ( result str)(result = '' (RaisedException(exc.read()) bool(raw_bytes := exc.read()))) (result = (t[:limit] + '' if len(t) > limit else t) (RaisedException(exc.read()) bool(raw_bytes := exc.read()) t = raw_bytes.decode('utf-8','replace').strip())).

</details>

#### FMA-MISMATCH-150 — `src--llm_client-py--_retry_create`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/llm_client-py/_retry_create.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/llm_client-py/_retry_create.json) · [具体 bug 报告](../fm_agent/bug_validation/src--llm_client-py--_retry_create.md) · [probe](../fm_agent/bug_validation/probe_src--llm_client-py--_retry_create.py)
- 触发/冲突：URLError from Anthropic native endpoint (e.g. connection reset by rate-limiting proxy) is caught by except Exception and treated as transient, not rate-limit — violating per-category retry budgets.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- client can send conversation messages for the given model and return text responses - model is a non-empty string - messages is a list of message dicts with "role" and "content" keys
- FMA SPEC post-condition：- Returns a tuple of (response_text, usage_metadata_dict) from a successful LLM call - response_text is the text content returned by the LLM - usage_metadata_dict maps token-usage keys to numeric counts from the LLM response, or is an empty dict when no usage data is reported - When the CLI backend is active, the LLM interaction is delegated to an external agent - For direct client calls, Anthropic-family models use a dedicated native Anthropic endpoint; all other models use the standard chat-completions endpoint - Recoverable errors (rate limiting, server unavailability, and other transient HTTP/middleware failures) are retried with increasing delay bounded by a per-category maximum retry count - Non-recoverable errors (provider-rejected malformed…
- FMA 推导 actual POST：After the function _retry_create(client, model, messages) is called, it terminates with one of the following outcomes: 1. If is_cli_backend_enabled() evaluates to True, the function returns run_agent_for_messages(model, messages), which is a tuple (text: str, usage: dict). 2. Otherwise, it enters a retry loop and attempts to call the LLM via client.chat.completions.create (or _anthropic_create for Anthropic models). The loop can terminate in one of the following ways: a. On successful API call, it returns (text, usage) where text is response.choices[0].message.content (a string) and usage is response.usage.model_dump() if response.usage is not None, else {} (a dict). b. If a BadRequestError or an HTTPError with status code 400 is raised, the excepti…

</details>

#### FMA-MISMATCH-151 — `src--llm_client-py--_stable_user_id`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/llm_client-py/_stable_user_id.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/llm_client-py/_stable_user_id.json) · [具体 bug 报告](../fm_agent/bug_validation/src--llm_client-py--_stable_user_id.md) · [probe](../fm_agent/bug_validation/probe_src--llm_client-py--_stable_user_id.py)
- 触发/冲突：When INJECT_ID env var is unset and _DEFAULT_INJECT_USER_ID is empty, _stable_user_id() returns an empty string, violating the spec requirement of always returning a non-empty string.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- None (takes no arguments)
- FMA SPEC post-condition：- Returns the value of the INJECT_ID environment variable when that variable is set and its value is non-empty - Returns a predefined static default value when INJECT_ID is not set or its value is empty - The returned string is non-empty in all cases
- FMA 推导 actual POST：The function returns a string. If the environment variable 'INJECT_ID' is set to a non-empty string, the return value is that string; otherwise, it is the value of `_DEFAULT_INJECT_USER_ID`. Formally: Let `v = os.environ.get('INJECT_ID')`. Then the returned value `r` satisfies `(v is not None and v != '' and r = v) or ((v is None or v == '') and r = _DEFAULT_INJECT_USER_ID)`.

</details>

### `src--opencode_trace-py`

#### FMA-MISMATCH-152 — `src--opencode_trace-py--_copy_opencode_output`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/opencode_trace-py/_copy_opencode_output.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/opencode_trace-py/_copy_opencode_output.json) · [具体 bug 报告](../fm_agent/bug_validation/src--opencode_trace-py--_copy_opencode_output.md) · [probe](../fm_agent/bug_validation/probe_src--opencode_trace-py--_copy_opencode_output.py)
- 触发/冲突：stream.close() is outside the finally block, so exceptions during stream.read() or trace_log.write() propagate past it, leaving the stream open.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- stream is an open, readable stream whose read(n) method returns a string of up to n characters (blocking until data is available) and whose close() method releases the underlying resource - trace_log_path is either None (or a falsy value, meaning no tracing) or a valid writable filesystem path
- FMA SPEC post-condition：- All data from stream has been consumed: read(4096) has been called repeatedly until an empty string signals EOF - stream.close() has been called the stream resource is released - If trace_log_path was truthy, a file at that path exists and contains the complete data read from the stream, encoded in UTF-8 with replacement characters for unencodable data; each chunk is flushed individually - If trace_log_path was falsy, no file is created or written - The trace log file (if opened) is closed before the stream is closed - Regardless of exceptions during reading or writing, both the trace log file (if opened) and the stream are guaranteed to be closed
- FMA 推导 actual POST：After the function _copy_opencode_output runs, the following post-conditions hold given the pre-conditions. Let S be `stream`, P be `trace_log_path` (original argument), and T be the local variable `trace_log`. **Normal termination (no exception):** - The function returns `None`. - All data from S has been read until EOF (the loop terminated on an empty string). - If P was truthy: a file at P was opened for text writing with UTF-8 encoding and `errors='replace'`; every chunk read from S was written to that file and flushed; the file is closed (T.close() called). - S is closed (S.close() called). **Exceptional termination (exception raised during try block or while opening P):** - The exception propagates out of the function. - If T was successfully…

</details>

#### FMA-MISMATCH-153 — `src--opencode_trace-py--_opencode_log_path`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/opencode_trace-py/_opencode_log_path.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/opencode_trace-py/_opencode_log_path.json) · [具体 bug 报告](../fm_agent/bug_validation/src--opencode_trace-py--_opencode_log_path.md) · [probe](../fm_agent/bug_validation/probe_src--opencode_trace-py--_opencode_log_path.py)
- 触发/冲突：When event_id starts with '/' (e.g. '/etc/passwd'), os.path.join discards the directory prefix and returns an absolute path outside work_dir.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- work_dir is a path to an existing directory - event_id is a non-empty string
- FMA SPEC post-condition：- Returns a filesystem path under work_dir that is deterministically derived from work_dir and event_id alone - The returned path identifies the file where the subprocess stdout and stderr log output associated with event_id will be written during execution - For a fixed (work_dir, event_id) pair, every call to this function returns the same path
- FMA 推导 actual POST：The function returns a string that is the result of joining the path of the trace event payload subdirectory (obtained from _payload_dir(_trace_dir(work_dir))) with the filename f"{event_id}_opencode.log". The returned path string may not correspond to an existing file or directory. Formally: return_value = os.path.join(_payload_dir(_trace_dir(work_dir)), event_id + '_opencode.log').

</details>

#### FMA-MISMATCH-154 — `src--opencode_trace-py--_opencode_trace_path`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/opencode_trace-py/_opencode_trace_path.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/opencode_trace-py/_opencode_trace_path.json) · [具体 bug 报告](../fm_agent/bug_validation/src--opencode_trace-py--_opencode_trace_path.md) · [probe](../fm_agent/bug_validation/probe_src--opencode_trace-py--_opencode_trace_path.py)
- 触发/冲突：event_id as an absolute path causes os.path.join to discard the work_dir prefix, returning a path outside work_dir
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- work_dir is a path to an existing directory - event_id is a non-empty string
- FMA SPEC post-condition：- Returns a filesystem path under work_dir that is deterministically derived from work_dir and event_id alone - The returned path identifies the file where the raw LLM request/response trace data associated with event_id will be written during execution - For a fixed (work_dir, event_id) pair, every call to this function returns the same path
- FMA 推导 actual POST：The function returns a string representing a filesystem path constructed by joining the trace directory path (obtained from `_trace_dir(work_dir)`), the segment `'opencode'`, and the filename `f"{event_id}.jsonl"` using the platform's path separator. No side effects occur, and the returned string does not necessarily correspond to an existing file or directory. Formally: `result = os.path.join(_trace_dir(work_dir), 'opencode', event_id + '.jsonl')`

</details>

#### FMA-MISMATCH-155 — `src--opencode_trace-py--_payload_dir`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/opencode_trace-py/_payload_dir.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/opencode_trace-py/_payload_dir.json) · [具体 bug 报告](../fm_agent/bug_validation/src--opencode_trace-py--_payload_dir.md) · [probe](../fm_agent/bug_validation/probe_src--opencode_trace-py--_payload_dir.py)
- 触发/冲突：If a file named 'payloads' already exists at the target path, os.makedirs raises FileExistsError, violating the spec's guarantee that the function returns a path and the directory exists after the call.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- trace_dir is a path to an existing directory
- FMA SPEC post-condition：- Returns a filesystem path identifying a "payloads" subdirectory within trace_dir - After the call returns, the directory at the returned path exists on the filesystem - The directory is the designated storage location for trace event payload files - For a fixed trace_dir, every call to this function returns the same path
- FMA 推导 actual POST：If no exception is raised, the function returns the string obtained by joining trace_dir and 'payloads' (using os.path.join), and the directory at that path exists. The original trace_dir directory is not modified.

</details>

#### FMA-MISMATCH-156 — `src--opencode_trace-py--_payload_ref`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/opencode_trace-py/_payload_ref.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/opencode_trace-py/_payload_ref.json) · [具体 bug 报告](../fm_agent/bug_validation/src--opencode_trace-py--_payload_ref.md) · [probe](../fm_agent/bug_validation/probe_src--opencode_trace-py--_payload_ref.py)
- 触发/冲突：_payload_ref computes relpath from os.path.dirname(trace_dir) instead of trace_dir, so joining the result with trace_dir yields an incorrect double-nested path.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- trace_dir is a valid path to an existing directory - path is a valid filesystem path
- FMA SPEC post-condition：- Returns a relative path string from trace_dir to path, resolving to the file or directory identified by path when combined with trace_dir - The returned path is suitable for use as a content reference in a trace event payload
- FMA 推导 actual POST：After execution of _payload_ref(trace_dir, path): - If the function returns normally, the return value is a string r such that r == os.path.relpath(path, os.path.dirname(trace_dir)). This string is the relative filesystem path from the parent directory of trace_dir to path. - If the function raises an exception, it is a ValueError (or, rarely, an OSError derived from path manipulation) because the relative path cannot be computed (e.g., path and the start directory reside on different Windows drives and no relative path exists). Formal logic: ( returns(r) r = relpath(path, dirname(trace_dir)) ) ( raises(e) (e is ValueError) (e is OSError) )

</details>

#### FMA-MISMATCH-157 — `src--opencode_trace-py--_start_opencode_process`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/opencode_trace-py/_start_opencode_process.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/opencode_trace-py/_start_opencode_process.json) · [具体 bug 报告](../fm_agent/bug_validation/src--opencode_trace-py--_start_opencode_process.md) · [probe](../fm_agent/bug_validation/probe_src--opencode_trace-py--_start_opencode_process.py)
- 触发/冲突：When stdin_text is None, passing stdin=None to subprocess.Popen causes the child to inherit the parent's stdin instead of receiving /dev/null (subprocess.DEVNULL), violating the spec that stdin must not be connected.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a path to an existing directory on the filesystem - work_dir is a path to an existing directory on the filesystem - event_id is a non-empty unique string identifying this trace event - command is an AgentCommand or a non-empty list of strings forming a valid CLI invocation - trace_log_path is a filesystem path under work_dir whose parent directories exist
- FMA SPEC post-condition：- Launches command as a subprocess whose working directory is proj_dir, whose environment variables are derived from work_dir and event_id, and whose stdout and stderr are merged into a single pipeline for capture - The subprocess receives input via a connected stdin pipe if and only if the command carries non-None stdin text; otherwise stdin is not connected to the subprocess - The subprocess text stream encoding is UTF-8 with replacement on decode errors, guaranteeing no UnicodeDecodeError on output read - Starts a background daemon thread that copies the subprocess merged output to trace_log_path as it is produced, ensuring every byte written by the subprocess is recorded - If the command carries non-None stdin text, starts a background daemon th…
- FMA 推导 actual POST：Function _start_opencode_process returns a tuple (proc, log_thread, stdin_thread). proc is a subprocess.Popen instance representing a child process that was launched with the command arguments from command_argv(command), working directory proj_dir, environment variables from _opencode_env(work_dir, event_id) merged with the current environment, and with stdout and stderr both redirected to a subprocess.PIPE that will provide UTF-8 encoded text with replacement errors. If command_stdin(command) returned a nonNone string stdin_text, the childs stdin is connected to a subprocess.PIPE and a newly created daemon thread stdin_thread is running the target _write_command_stdin(proc.stdin, stdin_text), which will write the text, flush, and close the pipe; if…

</details>

#### FMA-MISMATCH-158 — `src--opencode_trace-py--_write_command_stdin`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/opencode_trace-py/_write_command_stdin.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/opencode_trace-py/_write_command_stdin.json) · [具体 bug 报告](../fm_agent/bug_validation/src--opencode_trace-py--_write_command_stdin.md) · [probe](../fm_agent/bug_validation/probe_src--opencode_trace-py--_write_command_stdin.py)
- 触发/冲突：When stream.flush() raises an exception after a successful write(), the exception propagates unhandled, violating the spec postcondition that text is always both written and flushed.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- stream is an open, writable stream whose write(s) method accepts a string and whose close() method releases the underlying resource - text is a string to be written to the stream
- FMA SPEC post-condition：- text has been written to stream via write(text) and the stream internal buffer has been flushed via flush() - stream.close() has been called the stream resource is released - The stream is guaranteed to be closed even if write() or flush() raises an exception
- FMA 推导 actual POST：After the execution of the code block, `text` remains unchanged. The stream object `stream` is closed (i.e., `stream.close()` has been called, the underlying resource is released, and any further operations on `stream` raise `ValueError`). If the block completed without raising an exception (normal return), then the entire `text` has been successfully written to the stream's internal buffer via `stream.write(text)` and flushed to the underlying resource via `stream.flush()`. If an exception was raised during `stream.write(text)` or `stream.flush()`, the exception propagates out of the function; `stream` is still closed, but the amount of `text` written is unspecified. Formally: (invariant: `text` unchanged `stream.closed`) ((normal_return) (written(…

</details>

#### FMA-MISMATCH-159 — `src--opencode_trace-py--finish_opencode_trace`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/opencode_trace-py/finish_opencode_trace.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/opencode_trace-py/finish_opencode_trace.json) · [具体 bug 报告](../fm_agent/bug_validation/src--opencode_trace-py--finish_opencode_trace.md) · [probe](../fm_agent/bug_validation/probe_src--opencode_trace-py--finish_opencode_trace.py)
- 触发/冲突：Call finish_opencode_trace with a TracedOpenCodeProcess whose work_dir is a non-writable directory; record_opencode_call raises an unhandled exception and the trace event is never recorded, violating the specification.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- record is a fully populated TracedOpenCodeProcess with non-null work_dir, event_id, stage, started, command, and proc fields - record.proc has already terminated (its returncode is set)
- FMA SPEC post-condition：- If record.stdin_thread is not None, that thread has been joined (it is guaranteed completed before this function returns) - If record.log_thread is not None, that thread has been joined (it is guaranteed completed before this function returns) - A trace event of type "opencode_call" has been recorded in the trace database under record.work_dir - The recorded event's status is "success" if and only if record.error is falsy AND record.proc.returncode == 0; otherwise the status is "error" - The recorded event's end_time is the current UTC time at the moment of recording, formatted as ISO 8601 - The recorded event preserves the following fields from record unchanged: event_id, stage, started, command, function_ids, input_files, output_files, summary,…
- FMA 推导 actual POST：After normal execution (no uncaught exception) of finish_opencode_trace(record), the following hold: 1. Thread joining: (record.stdin_thread != None) record.stdin_thread.join() has completed, guaranteeing the thread has terminated. (record.log_thread != None) record.log_thread.join() has completed, guaranteeing that thread has terminated. 2. Trace recording: A trace event has been appended to the trace events JSONL file under record.work_dir, with the exact fields: - work_dir = record.work_dir - event_id = record.event_id - stage = record.stage - status = "error" if (record.error or record.proc.returncode != 0) else "success" - started = record.started - ended = utc_now_iso() (current UTC timestamp in ISO8601) - command = record.command - function_i…

</details>

#### FMA-MISMATCH-160 — `src--opencode_trace-py--function_id_from_extracted_path`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/opencode_trace-py/function_id_from_extracted_path.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/opencode_trace-py/function_id_from_extracted_path.json) · [具体 bug 报告](../fm_agent/bug_validation/src--opencode_trace-py--function_id_from_extracted_path.md) · [probe](../fm_agent/bug_validation/probe_src--opencode_trace-py--function_id_from_extracted_path.py)
- 触发/冲突：When a basename starts with a leading dot (e.g. '.hidden'), os.path.splitext treats it as part of the filename instead of an extension, violating the spec that defines the extension as the shortest suffix from the final '.' in the filename.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- path is a string containing a file path that may use either "/" or "\\" as path separators
- FMA SPEC post-condition：- Returns the fully-qualified function name (FQN) derived from path - If path begins with the prefix "fm_agent/extracted_functions/" or "extracted_functions/" (after normalizing backslashes to "/"), that prefix is removed before deriving the FQN; otherwise the prefix portion of the path is retained as-is - The FQN is formed by: stripping the last file extension (the shortest suffix beginning with the final "." in the filename) from the path, then replacing every remaining "/" separator with "::" - The returned string contains no "/" or "\\" characters and no final file extension
- FMA 推导 actual POST：The function returns a string formed by applying the following transformations in sequence: 1) replace every '\\' with '/' in the input path; 2) if the resulting string starts with 'fm_agent/extracted_functions/', remove that prefix; otherwise, if it starts with 'extracted_functions/', remove that prefix; 3) remove the file extension using os.path.splitext (i.e., remove the substring from the last '.' that follows a non-leading position in the final path component to the end, respecting that a single leading dot in the basename is treated as part of the name and not as an extension separator); 4) replace every remaining '/' with '::'. Formally: let s0 = path.replace('\\', '/'); let prefix1 = 'fm_agent/extracted_functions/', prefix2 = 'extracted_func…

</details>

#### FMA-MISMATCH-161 — `src--opencode_trace-py--function_id_from_result_path`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/opencode_trace-py/function_id_from_result_path.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/opencode_trace-py/function_id_from_result_path.json) · [具体 bug 报告](../fm_agent/bug_validation/src--opencode_trace-py--function_id_from_result_path.md) · [probe](../fm_agent/bug_validation/probe_src--opencode_trace-py--function_id_from_result_path.py)
- 触发/冲突：A dot-file path segment (e.g., '.hidden') is not stripped by os.path.splitext, which treats the leading dot as part of the basename instead of an extension separator.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- path is a non-empty string representing a file path
- FMA SPEC post-condition：- Returns a fully-qualified function name (FQN) string with path segments joined by "::" - The returned FQN contains no file extension: the substring from the last "." (inclusive) onward is removed from the final path segment - If the normalized path (backslashes converted to forward slashes) starts with the literal prefix "fm_agent/logic_verification_results/", that prefix is stripped before deriving the FQN - All remaining path separators ("/") in the stripped, extension-removed path are replaced with "::" to form the FQN - Backslash characters ("\") in the input are treated as equivalent to forward slash ("/") for all path manipulation
- FMA 推导 actual POST：The return value is the string obtained from `path` by applying the following transformations sequentially: (1) replace all occurrences of "\\" by "/"; (2) if the resulting string starts with "fm_agent/logic_verification_results/", remove that prefix; (3) remove the file extension (i.e., all characters from the last "." to the end, inclusive; if no ".", keep the whole string); (4) replace all occurrences of "/" by "::". Formally, let s1 = path.replace('\\', '/'), s2 = s1[len('fm_agent/logic_verification_results/'):] if s1.startswith('fm_agent/logic_verification_results/') else s1, s3 = os.path.splitext(s2)[0], then the return value is s3.replace('/', '::').

</details>

#### FMA-MISMATCH-162 — `src--opencode_trace-py--record_opencode_call`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/opencode_trace-py/record_opencode_call.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/opencode_trace-py/record_opencode_call.json) · [具体 bug 报告](../fm_agent/bug_validation/src--opencode_trace-py--record_opencode_call.md) · [probe](../fm_agent/bug_validation/probe_src--opencode_trace-py--record_opencode_call.py)
- 触发/冲突：Pass an empty string as summary (non-None but falsy); code substitutes default instead of using the provided value.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- work_dir is a valid writable directory path - event_id is a unique, non-empty string - stage is a non-empty string identifying the pipeline stage - status is one of "success", "error", "mismatch", or "format_error" - started and ended are ISO 8601 UTC timestamp strings with started <= ended - command is a list of strings forming a valid CLI invocation - function_ids, when not None, is a list of fully-qualified fun…
- FMA SPEC post-condition：- Appends exactly one trace event of type "opencode_call" as a single JSON line to the trace events file under work_dir (specifically trace/events.jsonl within work_dir) - The recorded event's event_id, stage, status, start_time, end_time reflect the corresponding parameter values unchanged - The recorded event's function_ids is the provided list when non-None, or an empty list when None - The recorded event's summary is the provided value when non-None, or a default string of the form "OpenCode <stage>" when None - When opencode_log_path is provided and the file it refers to actually exists on disk, the event includes a child payload entry of type "tool_output" labeled "opencode-stdout", referencing the file via a path relative to the trace directo…
- FMA 推导 actual POST：The function returns None. It writes a trace event to the file <code>events.jsonl</code> inside the trace directory derived from <code>work_dir</code> (i.e., <code>_trace_dir(work_dir)</code>), creating parent directories and the file if they do not exist. The event is a JSON object <code>e</code> with the following properties: <code>e.event_id = event_id</code>; <code>e.type = 'opencode_call'</code>; <code>e.stage = stage</code>; <code>e.status = status</code>; <code>e.start_time = started</code>; <code>e.end_time = ended</code>; <code>e.summary = summary if summary is not None else 'OpenCode ' + stage</code>; <code>e.function_ids = function_ids if function_ids is not None else []</code>; <code>e.children</code> is a list built by including a child…

</details>

#### FMA-MISMATCH-163 — `src--opencode_trace-py--run_opencode_traced`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/opencode_trace-py/run_opencode_traced.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/opencode_trace-py/run_opencode_traced.json) · [具体 bug 报告](../fm_agent/bug_validation/src--opencode_trace-py--run_opencode_traced.md) · [probe](../fm_agent/bug_validation/probe_src--opencode_trace-py--run_opencode_traced.py)
- 触发/冲突：When _wait_opencode_process returns (0, error_string), the trace status is incorrectly 'success' because the code only checks exit_code==0 without considering the error variable.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a path to an existing project directory - work_dir is a path to an existing, writable fm_agent workspace directory - command is a non-empty list of strings forming a valid CLI invocation - stage is a non-empty string identifying the pipeline stage - function_ids, when provided, is a list of fully-qualified function name strings - input_files, when provided, is a list of fm_agent-relative input file pat…
- FMA SPEC post-condition：- Launches command as a subprocess with work_dir as the working directory and waits for it to complete, subject to a configured timeout - If the subprocess exits with code 0: returns a CompletedProcess containing the command argv and exit code - If the subprocess exits with a non-zero code, or if the configured timeout expires: raises subprocess.CalledProcessError whose returncode reflects the actual exit code (non-zero exit) or a synthetic non-zero code (timeout) - In every exit path success, non-zero exit, or timeout writes exactly one structured trace event as a JSON line appended to fm_agent/trace/events.jsonl - The trace event includes the event ID, stage name, start and end timestamps in ISO 8601 UTC, status ("success" for exit code 0, "error"…
- FMA 推导 actual POST：After execution of run_opencode_traced, regardless of whether it returns normally, raises subprocess.CalledProcessError, or raises any other exception, the following global conditions hold: 1. A uniquely identified opencode subprocess was launched. Any log-capture thread (log_thread) and stdin-handling thread (stdin_thread) that were started have been joined (blocking until they finish), so no orphaned threads remain. 2. A trace event record is appended to the file at {work_dir}/fm_agent/trace/events.jsonl via record_opencode_call. The recorded fields are: - work_dir: the given work_dir - event_id: a globally unique string returned by new_event_id("opencode") - stage: the given stage - status: "success" if the exit_code variable at the time of recor…

</details>

#### FMA-MISMATCH-164 — `src--opencode_trace-py--wait_opencode_traced`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/opencode_trace-py/wait_opencode_traced.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/opencode_trace-py/wait_opencode_traced.json) · [具体 bug 报告](../fm_agent/bug_validation/src--opencode_trace-py--wait_opencode_traced.md) · [probe](../fm_agent/bug_validation/probe_src--opencode_trace-py--wait_opencode_traced.py)
- 触发/冲突：When _wait_opencode_process returns an empty error string and record.error is None, the condition 'error or record.error is None' evaluates True (empty string is falsy), causing record.error to be set to '' instead of remaining None per spec.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- record is a TracedOpenCodeProcess previously returned by start_opencode_traced. - record.proc refers to a running subprocess that has not yet been waited on. - timeout_seconds is a positive integer; defaults to the configured OPENCODE_TIMEOUT_SECONDS.
- FMA SPEC post-condition：- Blocks until one of: the subprocess exits normally, the subprocess is terminated by a signal, or timeout_seconds elapses since invocation of this function. - If timeout_seconds elapses before the subprocess terminates, the subprocess is killed and the post-condition from the resulting forced termination applies. - Returns the subprocess exit code: zero if the process exited with status 0, a positive integer if the process exited with a non-zero status, or the negative of the signal number if the process was terminated by a signal. - If a non-empty error string is produced during waiting, record.error is overwritten with it. - If an empty or None error string is produced during waiting and record.error is None, record.error remains None. - If an em…
- FMA 推导 actual POST：After execution, the function returns the integer exit_code obtained from `_wait_opencode_process`. The `record.proc` subprocess has been waited on and is no longer running; its `returncode` is set to the same exit_code value (the process's exit code, or the negative of the signal number if killed by a signal). The `record.error` attribute is updated as follows: if the error string from `_wait_opencode_process` is not None, then `record.error` becomes that string; otherwise `record.error` retains its previous value (which may be None or a prior error). The other attributes of `record` (`command`, `stage`) are unchanged. No exceptions are raised. Formal logic: Let old state be unprimed, new state primed. Let (exit_code, error) = _wait_opencode_proces…

</details>

#### FMA-MISMATCH-249 — `src--opencode_trace-py--start_opencode_traced`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/opencode_trace-py/start_opencode_traced.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/opencode_trace-py/start_opencode_traced.json) · [具体 bug 报告](../fm_agent/bug_validation/src--opencode_trace-py--start_opencode_traced.md) · [probe](../fm_agent/bug_validation/probe_src--opencode_trace-py--start_opencode_traced.py)
- 触发/冲突：The specification requires event_id to start with 'opencode_', but new_event_id('opencode') already produces IDs with the 'opencode_' prefix because new_event_id inserts an underscore between the prefix argument and the UUID hex.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is an absolute path to an existing directory on the filesystem. - work_dir is an absolute path to an existing directory. - command is a non-empty list of strings forming a valid CLI invocation. - stage is a non-empty string identifying a pipeline stage. - function_ids, when provided, is a list of fully-qualified function name strings. - input_files, when provided, is a list of fm_agent/-relative file path…
- FMA SPEC post-condition：- Returns a TracedOpenCodeProcess whose fields are populated from the corresponding arguments and generated startup values. - The returned record has a globally unique event_id string generated with prefix "opencode_". - The returned record's started field is a UTC timestamp in ISO 8601 format captured at the moment of invocation. - The returned record's proc field refers to a running subprocess whose stdout and stderr streams are being read asynchronously by one or more background threads. - The returned record's opencode_log_path is a filesystem path under work_dir determined solely by work_dir and event_id. - The returned record's opencode_trace_path is a filesystem path under work_dir determined solely by work_dir and event_id. - The returned re…
- FMA 推导 actual POST：The function returns a new TracedOpenCodeProcess instance. Upon return, a globally unique event identifier event_id has been generated by new_event_id('opencode') and is stored in the returned object. The started timestamp is the current UTC date-time in ISO 8601 format obtained from utc_now_iso(). The paths opencode_log_path = _opencode_log_path(work_dir, event_id) and opencode_trace_path = _opencode_trace_path(work_dir, event_id) are computed and stored. A subprocess is launched and the resulting (proc, log_thread, stdin_thread) tuple from _start_opencode_process(proj_dir, work_dir, event_id, command, opencode_log_path) is held in the object; proc is a live subprocess.Popen instance whose stdout and stderr are being asynchronously captured by log_…

</details>

### `src--parser-py`

#### FMA-MISMATCH-165 — `src--parser-py--_extract_function_name`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/parser-py/_extract_function_name.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/parser-py/_extract_function_name.json) · [具体 bug 报告](../fm_agent/bug_validation/src--parser-py--_extract_function_name.md) · [probe](../fm_agent/bug_validation/probe_src--parser-py--_extract_function_name.py)
- 触发/冲突：The regex uses ASCII-only character classes [A-Za-z_] and [A-Za-z0-9_]* which fail to match Unicode letters in Python identifiers (e.g. 'café'), causing the function to return None instead of extracting the identifier.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- signature_line is a string
- FMA SPEC post-condition：- Returns the function name extracted from the signature line; returns None if no recognizable function name is found - A function name is recognizable when signature_line contains an identifier (starting with an alphabetic character or underscore, followed by zero or more alphanumeric characters or underscores) immediately followed by optional whitespace and an opening parenthesis `(` - When multiple such patterns exist in signature_line, the first (leftmost) match determines the returned function name
- FMA 推导 actual POST：The function returns the first identifier-like substring immediately followed by an opening parenthesis in `signature_line`, or `None` if no such pattern exists. The input string `signature_line` remains unchanged. Formally: let `m = re.search(r'([A-Za-z_][A-Za-z0-9_]*)\s*\(', signature_line)`. Then: if `m` is not `None`, the return value is `m.group(1)` (a string); if `m` is `None`, the return value is `None`. That is, `( m MatchObject {None} : m = re.search(r'([A-Za-z_][A-Za-z0-9_]*)\s*\(', signature_line) ( (m None return_value = m.group(1) isinstance(return_value, str)) (m = None return_value = None) ))`.

</details>

#### FMA-MISMATCH-166 — `src--parser-py--_parse_info_section`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/parser-py/_parse_info_section.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/parser-py/_parse_info_section.json) · [具体 bug 报告](../fm_agent/bug_validation/src--parser-py--_parse_info_section.md) · [probe](../fm_agent/bug_validation/probe_src--parser-py--_parse_info_section.py)
- 触发/冲突：Calling .strip() on the joined body lines removes leading whitespace from the first body line, violating the spec's requirement to preserve original spec body text.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- section_text is a string; it may be empty, contain only whitespace, be exactly "(no callees)", or contain callee entries separated by [SPLIT] delimiters
- FMA SPEC post-condition：- Returns a FunctionSpecMap object - When section_text is empty, whitespace-only, or equals "(no callees)" after stripping, returns an empty FunctionSpecMap containing zero entries and zero signatures - Otherwise, section_text is partitioned into entries at each [SPLIT] delimiter; leading and trailing whitespace is stripped from each entry - For each non-empty entry: the first non-blank line is interpreted as a callee function signature; all subsequent non-blank lines collectively form the spec body for that callee - An entry whose first non-blank line does not contain a recognizable function name is silently discarded it produces no entry in the returned map - Each retained entry is stored in the returned map under its extracted function name, with…
- FMA 推导 actual POST：If `section_text.strip()` is the empty string or exactly "(no callees)", the function returns an empty `FunctionSpecMap`. Otherwise, let `entries` be the list obtained by splitting `section_text` using the regular expression `_SPLIT_MARKER_RE`. The function returns a `FunctionSpecMap` containing one entry for every string `e` in `entries` that satisfies: after stripping whitespace, `e` is non-empty; after splitting `e` into lines and removing any line that consists only of whitespace, the resulting list `entry_lines` is non-empty; and `_extract_function_name(entry_lines[0])` returns a non`None` value `name`. For each such qualifying `e`, the map stores an entry whose key is `name`, with the signature set to `entry_lines[0]` and the spec body set to…

</details>

#### FMA-MISMATCH-167 — `src--parser-py--_strip_section_comment_prefix`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/parser-py/_strip_section_comment_prefix.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/parser-py/_strip_section_comment_prefix.json) · [具体 bug 报告](../fm_agent/bug_validation/src--parser-py--_strip_section_comment_prefix.md) · [probe](../fm_agent/bug_validation/probe_src--parser-py--_strip_section_comment_prefix.py)
- 触发/冲突：The regex requires at least two '/' or '-' characters for comment prefixes, but the spec allows a single character; single-char prefixes are not stripped.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- line is a string
- FMA SPEC post-condition：- Returns a string where any leading comment prefix at the start of the line (after optional leading whitespace) has been removed - A recognized comment prefix consists of one or more consecutive characters from the set {`/`, `#`, `-`, `%`}, all of the same character, optionally followed by a single whitespace character - Leading whitespace characters that precede the comment prefix are preserved unchanged in the returned string - When the line does not begin with (optional leading whitespace followed by) a recognized comment prefix, the line is returned unchanged
- FMA 推导 actual POST：Returns a string equal to `re.sub(r'^(\s*)(?://+|#+|--+|%+)\s?', r'\1', line)`. Specifically, if `line` starts with any amount of whitespace followed by one or more comment characters from the set `//`, `#`, `--`, `%` and optionally a single whitespace character, then the matched comment prefix and optional whitespace are removed, leaving only the leading whitespace; otherwise the original `line` is returned unchanged.

</details>

#### FMA-MISMATCH-168 — `src--parser-py--add_entry`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/parser-py/add_entry.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/parser-py/add_entry.json) · [具体 bug 报告](../fm_agent/bug_validation/src--parser-py--add_entry.md) · [probe](../fm_agent/bug_validation/probe_src--parser-py--add_entry.py)
- 触发/冲突：When self.signatures is aliased to self, add_entry stores signature in place of spec due to the second assignment overwriting the first.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- function_name is a non-empty string - signature is a string - spec is a string (may be empty)
- FMA SPEC post-condition：- The value stored for key function_name in the map equals the spec argument - The value stored for key function_name in self.signatures equals the signature argument
- FMA 推导 actual POST：self[function_name] == spec self.signatures[function_name] == signature (k keys(self) \ {function_name} : self[k] == old(self)[k]) (k keys(self.signatures) \ {function_name} : self.signatures[k] == old(self.signatures)[k])

</details>

#### FMA-MISMATCH-169 — `src--parser-py--parse_input_function`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/parser-py/parse_input_function.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/parser-py/parse_input_function.json) · [具体 bug 报告](../fm_agent/bug_validation/src--parser-py--parse_input_function.md) · [probe](../fm_agent/bug_validation/probe_src--parser-py--parse_input_function.py)
- 触发/冲突：Bug 1 (nl_spec is None when no [SPEC] section) NOT confirmed — code correctly returns empty string. Bug 2 (inline # comments stripped by _remove_func_comments) CONFIRMED — inline comments are removed contrary to the spec which only requires removal of comment-only lines.
- 成因复核：函数目的就是给 reasoner 提供去注释代码；SPEC 只允许删整行注释、禁止删行尾注释，没有调用方或文档依据。验证报告自身也承认其中一个子 claim 未复现。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- file_path points to a file that exists and is readable as UTF-8 text - The file MAY contain a [SPEC] section: two lines whose stripped text is "# [SPEC]", with arbitrary content between them - The file MAY contain an [INFO] section: two lines whose stripped text is "# [INFO]", with callee specification entries between them separated by "# [SPLIT]" markers - The remainder of the file after the closing [INFO] or [SP…
- FMA SPEC post-condition：- Returns a 3-tuple (func, nl_spec, knowledge) - func: a string of the source code body all comment lines (lines where the first non-whitespace character is '#') are removed, and each remaining line is prefixed with "Line {N}: " where N is the 1-based line number in the comment-stripped text - nl_spec: the text between the opening and closing [SPEC] markers (empty string "" when no [SPEC] section is present) - knowledge: a FunctionSpecMap built from the [INFO] section's callee entries, where each callee name maps to its spec text and the .signatures dict maps callee names to their signature lines; empty FunctionSpecMap when no [INFO] section exists - The source code body is taken from the portion of the file after the closing [INFO] marker when an […
- FMA 推导 actual POST：The function returns a tuple (func, nl_spec, knowledge). Let lines = file_content.splitlines(). (spec_text, _, spec_close_idx) = _extract_marked_section(lines, 'SPEC'), and (info_text, _, info_close_idx) = _extract_marked_section(lines, 'INFO'). Then: - nl_spec is spec_text, which is the string containing the lines between the first '# [SPEC]' marker line and the next '# [SPEC]' marker line, exclusive of the markers; or None if fewer than two '# [SPEC]' marker lines exist. - knowledge = _parse_info_section(info_text), a FunctionSpecMap where each callee function name maps to its full spec text and its signature line; empty if info_text is None. - Let raw_func be: if info_close_idx is not None, the concatenation of lines from index info_close_idx+1 t…

</details>

### `src--pipeline_setup-py`

#### FMA-MISMATCH-170 — `src--pipeline_setup-py--_build_module_description_prompt`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_build_module_description_prompt.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_build_module_description_prompt.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_build_module_description_prompt.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_build_module_description_prompt.py)
- 触发/冲突：When source_files is a string (not an array), list() converts it to a non-empty character list, causing the truthiness check to incorrectly include the module in the prompt.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- modified_modules is an iterable of dicts, each containing at minimum "phase" (int) and "module" (str) keys. - phases_json is a string path to a JSON file. If the file exists, its content conforms to the phases.json schema: a JSON object with a "phases" array where each phase has "phase" (int) and "modules" (array of objects with "name" (str) and "source_files" (array of str)).
- FMA SPEC post-condition：- If phases_json cannot be opened or its content is not valid JSON, behaves as if phases were an empty list. - Returns None when none of the modules named in modified_modules has a non-empty source_files array in phases_json. - Otherwise, returns a string containing an agent prompt. The prompt enumerates every module in modified_modules that still owns at least one source file according to phases_json, each formatted as a bulleted line identifying the module by its current phase number and module name. The prompt includes explicit constraints that the agent must: edit only the "description" field of the listed modules in fm_agent/phases.json; not modify "source_files", "phase", "name", "depends_on_phases", or the phase structure; not touch any unlis…
- FMA 推导 actual POST：The function returns either None or a string. It attempts to open and parse the JSON file at `phases_json`; if an OSError or ValueError occurs (e.g., file missing, invalid JSON), the file is treated as containing no phases. A mapping from (phase, module name) to list of source files is built from the file's 'phases' array. For each module in `modified_modules`, if the corresponding source file list is non-empty, the module is included in a list of changes. If this list is empty, the function returns None. Otherwise, it returns a prompt string beginning with 'Here is a list of modules in fm_agent/phases.json:\n\n', followed by lines of the form ' - phase {phase} module "{name}"' for each included module, followed by a fixed instruction text. The func…

</details>

#### FMA-MISMATCH-171 — `src--pipeline_setup-py--_clean_empty_phase_module`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_clean_empty_phase_module.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_clean_empty_phase_module.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_clean_empty_phase_module.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_clean_empty_phase_module.py)
- 触发/冲突：When phases are removed from phases.json, the renumbered dict only contains surviving phases (e.g. {2: 1}) instead of all original phases as the spec requires.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- work_dir is a string path to a writable directory containing phases.json that conforms to the phases.json schema (a JSON object with a "phases" array; each phase has "phase" (int), "modules" (array), and optionally "depends_on_phases" (array of int)). - If work_dir contains spec_prompts/domain_context/, it may contain phase_NN_types.txt files keyed by phase number.
- FMA SPEC post-condition：- phases.json is modified in-place (file overwritten): * Every module whose source_files array is absent, null, or empty is removed from its phase. * Every phase left with no modules (empty modules array after pruning) is removed from the phases array. * Surviving phases are renumbered to a contiguous 1..N range in ascending order of their original phase numbers (no gaps). * For each surviving phase, every element in depends_on_phases is remapped to the new phase number; references to removed phases are dropped. The resulting depends_on_phases array is sorted in ascending order and contains no duplicates. - Domain context files are synced: * For every removed phase number, the corresponding phase_NN_types.txt file is deleted. * For every phase that…
- FMA 推导 actual POST：On successful execution: The file 'phases.json' in `work_dir` is updated so that its 'phases' array contains exactly the phases from the original array that, after filtering each phase's modules to those with a truthy 'source_files' field, still have at least one module. The surviving phases are renumbered consecutively from 1 upwards, preserving the original ordering (by original 'phase' number). For each surviving phase, its 'depends_on_phases' list is replaced by a sorted list of the new numbers of its original dependencies that are still present; references to removed phases are dropped. If a phase originally had no 'depends_on_phases' field or it was null/falsy, it is left as is. The function also synchronises domain context files: for each rem…

</details>

#### FMA-MISMATCH-172 — `src--pipeline_setup-py--_collapse_phases_to_one`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_collapse_phases_to_one.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_collapse_phases_to_one.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_collapse_phases_to_one.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_collapse_phases_to_one.py)
- 触发/冲突：When the first original phase number is not 1, the code preserves that original phase number instead of resetting it to 1 as the specification requires.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- work_dir is a string path to a writable directory containing phases.json that conforms to the phases.json schema (a JSON object with a "phases" array; each phase has "phase" (int), "name" (string), "description" (string or null), "modules" (array), and optionally "depends_on_phases" (array of int)). - If work_dir contains spec_prompts/domain_context/, it may contain phase_NN_types.txt files keyed by phase number.
- FMA SPEC post-condition：- When phases.json contains no phases (empty "phases" array), the function returns immediately; no files are modified or created. - Otherwise, phases.json is replaced: the "phases" array contains exactly one element a phase with: * "phase" set to the integer 1. * "name" set to the string "Unified Analysis Phase". * "modules" being the concatenation of every module from every original phase, preserving the ascending phase-number order of original phases and the original module order within each phase. * "description" being the concatenation of every non-empty (after stripping whitespace) description from every original phase, each prefixed by "Phase {N} ({name}): " and joined by "\n\n". If no original phase had a non-empty description, "description"…
- FMA 推导 actual POST：Upon successful execution: (1) if the initial 'phases' array in 'phases.json' was empty, the file system is unchanged and the function returns; (2) otherwise, 'phases.json' is overwritten with a single phase whose 'phase' equals that of the original first phase, 'name' = "Unified Analysis Phase", 'description' = the concatenation (separated by "\n\n") of non-empty original descriptions each prefixed with "Phase {phase} ({name}): ", 'modules' = the concatenation of all original phase modules, and 'depends_on_phases' = []. In the subdirectory 'spec_prompts/domain_context/', if any 'phase_NN_types.txt' files exist for the original phases, their (stripped) contents are concatenated (separator "\n\n") and written to 'phase_01_types.txt', and all other fi…

</details>

#### FMA-MISMATCH-173 — `src--pipeline_setup-py--_collect_changed_phases`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_collect_changed_phases.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_collect_changed_phases.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_collect_changed_phases.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_collect_changed_phases.py)
- 触发/冲突：Non-integer values (strings, floats) passed as phase numbers are included in the result because the code only checks for None, not isinstance(phase_num, int).
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- ensure_changes is a mapping optionally containing an "augmented" key whose value, if present, is a mapping. - Each element of change_sets is a mapping optionally containing a "modified_modules" key whose value, if present, is an iterable of mappings, each optionally containing a "phase" key. - Phase number values (keys of ensure_changes["augmented"] and values of m["phase"]) are expected to be integers or None.
- FMA SPEC post-condition：- Returns a set containing every non-None integer that is either: a) a key of ensure_changes["augmented"], or b) the value of the "phase" key from any entry in "modified_modules" across all change_sets. - Each phase number appears at most once in the result (duplicates are collapsed). - Returns an empty set if no non-None phase numbers are found across all sources.
- FMA 推导 actual POST：The function returns a set of distinct non-None phase numbers (integers, as per the precondition) collected from two sources. 1) Every key k in ensure_changes["augmented"] (if the key exists and the value is a mapping) for which k is not None is included. 2) For every change set c in *change_sets, and for every module m in c.get("modified_modules", []), the value m.get("phase") is included if it is not None. Formally, if we denote A = ensure_changes.get("augmented", {}) and for each c change_sets, M(c) = c.get("modified_modules", []), then the returned set is: {k | k A.keys() k None} {m.get("phase") | c change_sets, m M(c) m.get("phase") None}.

</details>

#### FMA-MISMATCH-174 — `src--pipeline_setup-py--_deduplicate_phases`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_deduplicate_phases.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_deduplicate_phases.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_deduplicate_phases.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_deduplicate_phases.py)
- 触发/冲突：When a source file appears twice within the same module's source_files list, the function incorrectly removes the second occurrence because the global seen set does not distinguish intra-module duplicates from cross-module duplicates.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- phases_dir is a string path to a directory containing a valid phases.json file. - phases.json conforms to the pipeline schema: a JSON object with a "phases" array; each phase has "phase" (int) and "modules" (array); each module has "name" (string) and "source_files" (array of strings). - Each source_files element is a relative file path string from the project root. - The phases.json file is readable and writable…
- FMA SPEC post-condition：- phases.json is overwritten with every source file path appearing in at most one module across all phases. - For any source file path appearing in multiple modules (across the same or different phases), only the first occurrence in ascending phase number order, then module order within each phase is preserved; all subsequent occurrences are removed from their respective module's source_files list. - The set of phases and modules is unchanged: no phase or module is removed, even when a module's source_files becomes empty. - Phase numbers, module names, and the ordering of phases/modules within phases.json are preserved. - Returns a dict with the key "modified_modules" mapping to a list of dicts, one per module from which at least one source file was…
- FMA 推导 actual POST：After successful execution (no exceptions), the following holds: Natural language: The file at `phases_path = os.path.join(phases_dir, "phases.json")` is overwritten with a JSON object `new_data` that preserves the original phases and modules structure (same order, same counts, same names) but with each module's `source_files` list deduplicated so that every source file appears at most once overall. For each source file that appeared in the original `old_data`, it is kept only in the module that first claims it according to ascending phase number (ties broken by original stable order among phases with equal numbers) and then by original module order within that phase; later occurrences are removed. Modules that lose all files are retained without dr…

</details>

#### FMA-MISMATCH-175 — `src--pipeline_setup-py--_domain_context_complete`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_domain_context_complete.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_domain_context_complete.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_domain_context_complete.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_domain_context_complete.py)
- 触发/冲突：When a phase object in phases.json has a non-numeric string value for the 'phase' key (which is not None), f'{phase_num:02d}' raises ValueError instead of returning False as the spec requires.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- work_dir is a valid directory path
- FMA SPEC post-condition：- Returns True if and only if all of the following hold simultaneously: (a) phases.json exists under work_dir and is a well-formed JSON file containing a "phases" array (b) spec_prompts/domain_context/engine_overview.txt exists as a regular file under work_dir (c) For every phase object in phases.json whose "phase" key is a numeric value, the file spec_prompts/domain_context/phase_NN_types.txt (where NN is the phase number zero-padded to 2 digits) exists as a regular file under work_dir (d) No phase object in phases.json has a missing or non-numeric "phase" key - Returns False when any of conditions (a)-(d) is not satisfied - Does not modify any filesystem state: the function performs only existence checks and reads, never creates, updates, or delet…
- FMA 推导 actual POST：After execution, the function returns a boolean value. Natural language: The function returns True if and only if: 1. The file `phases.json` inside `work_dir` is a valid JSON file (i.e., it exists as a regular file and its content is successfully parseable as JSON). 2. The file `spec_prompts/domain_context/engine_overview.txt` relative to `work_dir` exists as a regular file. 3. The parsed JSON object from `phases.json` contains a key `'phases'` whose value is a list. For every element `phase_entry` in that list, `phase_entry` contains a key `'phase'` with a nonnull numeric value, and the file `spec_prompts/domain_context/phase_{phase_num:02d}_types.txt` (where `phase_num` is that numeric value formatted to two digits) exists as a regular file. If an…

</details>

#### FMA-MISMATCH-176 — `src--pipeline_setup-py--_ensure_source_files_in_phases`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_ensure_source_files_in_phases.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_ensure_source_files_in_phases.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_ensure_source_files_in_phases.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_ensure_source_files_in_phases.py)
- 触发/冲突：Duplicate-normalized paths in required_source_files (e.g. 'path/to/dup.py' and 'path\\to\\dup.py') are both appended to source_files without deduplication.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- phases_json is a string path to a writable JSON file conforming to the phases.json schema (an object with a "phases" array where each phase has a numeric "phase" key and a "modules" array, and each module has a "source_files" array of relative paths) - required_source_files is None or an iterable of strings
- FMA SPEC post-condition：- If required_source_files is None or empty, returns {"forced": [], "augmented": {}, "augmented_modules": []} without modifying the file at phases_json - If required_source_files is non-empty: (a) Every path in required_source_files not already present in any source_files list in phases_json (after normalizing "\" to "/" in both the existing entries and the required files) is appended, in its original form, to the source_files list of the first module of the phase with the smallest "phase" number (b) If no phase exists in phases_json, a single phase numbered 1 containing one module named "entry_points" is created to receive all missing source files; the phase has an empty depends_on_phases list (c) If the earliest phase exists but has no modules, a…
- FMA 推导 actual POST：If `required_source_files` is None or empty, the file `phases_json` is unchanged and the function returns `{"forced": [], "augmented": {}, "augmented_modules": []}`. Otherwise, let `norm_paths_required` = { normalize_path(p) for p in required_source_files } where normalize_path replaces backslashes with forward slashes. Let `existing_norm_paths` = set of all normalized source file paths across all modules in all phases in the original file. If norm_paths_required existing_norm_paths, the file is unchanged and the function returns the empty result. Otherwise, let `missing` = [p for p in required_source_files if normalize_path(p) existing_norm_paths] (preserving order). Then the function modifies the file as follows: (1) If the original file had no `p…

</details>

#### FMA-MISMATCH-177 — `src--pipeline_setup-py--_filter_phases_to_submodules`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_filter_phases_to_submodules.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_filter_phases_to_submodules.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_filter_phases_to_submodules.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_filter_phases_to_submodules.py)
- 触发/冲突：When a phase object in phases.json lacks a 'phase' key, phase.get('phase') returns None instead of an integer, violating the post-condition that each modified module record must contain the phase number.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- phases_json is a string path to an existing phases.json file whose parent directory is writable and whose content conforms to the phases.json schema (a JSON object with a "phases" array; each phase has "phase" (int) and "modules" (array); each module has "source_files" (array of strings)). - submodules is None or a non-empty iterable of subdirectory name strings relative to the project root.
- FMA SPEC post-condition：- When submodules is None or empty, phases.json is unchanged on disk and the function returns {"removed": 0, "modified_modules": []}. - When submodules is non-empty, every source_file path in every module of every phase is classified: paths that begin with any of the submodule directory names are retained; all other paths are removed from their module. - Returns a dict with two keys: "removed" maps to the total count (int) of removed source_file entries; "modified_modules" maps to a list of objects, one per module from which at least one file was removed, each containing the phase number, module name, the list of removed file paths, and the list of retained file paths. - When at least one source_file is removed, the file at phases_json is overwritte…
- FMA 推导 actual POST：After successful execution (i.e., no unhandled I/O or JSON parse error), the function returns a dictionary with keys 'removed' (integer) and 'modified_modules' (list). If submodules is falsy (None or empty), the function returns {'removed': 0, 'modified_modules': []} without reading or modifying the file at phases_json. Otherwise: the file at phases_json is read into memory (old_data). The function iterates over the phases array sorted by the 'phase' key, and for each module it partitions its source_files list into kept (files whose path starts with any string in submodules) and removed (all others). If removed is empty, the module is unchanged. If removed is non-empty, the module's 'source_files' field is replaced with kept, the count is added to r…

</details>

#### FMA-MISMATCH-178 — `src--pipeline_setup-py--_merge_descriptions`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_merge_descriptions.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_merge_descriptions.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_merge_descriptions.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_merge_descriptions.py)
- 触发/冲突：The specification requires joining with a single space when neither description is empty and source_desc is not a substring of target_desc, but the code uses two newline characters.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- target_desc is a string - source_desc is a string
- FMA SPEC post-condition：- Returns target_desc unchanged when source_desc, after stripping leading and trailing whitespace, is empty - Returns target_desc unchanged when the stripped source_desc is a substring of target_desc - Returns source_desc unchanged when target_desc is empty and stripped source_desc is non-empty and is not a substring of target_desc - Otherwise, returns target_desc joined with source_desc using a single space separator
- FMA 推导 actual POST：The function returns a string. Let s = source_desc.strip() (after applying the emptystring fallback, which is a noop since both inputs are strings). - If s is empty or s is a substring of target_desc, the result equals the original target_desc. - Else if target_desc is empty (and s is nonempty and not a substring), the result equals s. - Otherwise, the result is the concatenation of the original target_desc, the literal string '\n\n', and s. No side effects; the input strings remain unchanged. Formally, with inputs T (target_desc) and S (source_desc) and output R: R String ( S.strip() = "" S.strip() T R = T ) ( S.strip() "" S.strip() T T = "" R = S.strip() ) ( S.strip() "" S.strip() T T "" R = T + "\n\n" + S.strip() )

</details>

#### FMA-MISMATCH-179 — `src--pipeline_setup-py--_phase_source_files`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_phase_source_files.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_phase_source_files.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_phase_source_files.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_phase_source_files.py)
- 触发/冲突：A valid JSON array (e.g. []) parsed by json.load() as a list causes AttributeError on data.get() because lists lack .get(), instead of returning {} as the spec requires.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- phases_json is a string path to a phases.json file whose schema conforms to the phases.json specification: a JSON object with a "phases" key containing an array of phase objects, each with a "phase" key (integer) and a "modules" key (array of module objects, each with a "source_files" key containing an array of string paths).
- FMA SPEC post-condition：- When phases_json cannot be read (file missing, unreadable) or contains invalid JSON, returns an empty dict. - Otherwise returns a dict[int, list[str]] mapping each phase number present in the file to the concatenation of all source_files arrays from ALL modules within that phase. Phases whose "phase" key is absent or null are silently skipped. - The returned dict may contain entries whose value is an empty list if the corresponding phase has modules but no source files. - Each source file path in the returned lists is a string exactly as it appears in phases.json (no normalization, no resolution).
- FMA 推导 actual POST：The function returns a dictionary mapping each phase number (integer) to the combined list of source file paths (strings) from all modules of that phase, in the order they appear in the phases.json file. Formally, if the file is successfully opened and parsed as a valid JSON object with a 'phases' array conforming to the given schema, then result = {phase['phase']: [file for module in phase['modules'] for file in module['source_files']] for phase in D['phases']}. If the file cannot be opened or contains invalid JSON (contradicting the precondition), an empty dictionary is returned.

</details>

#### FMA-MISMATCH-180 — `src--pipeline_setup-py--_phases_cover_current_sources`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_phases_cover_current_sources.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_phases_cover_current_sources.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_phases_cover_current_sources.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_phases_cover_current_sources.py)
- 触发/冲突：Pass submodules=[] (empty list, not None); 'if submodules' treats [] as falsy and skips the submodule check, returning True when spec condition (d) requires False.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- phases_json is a string path - proj_dir is an existing directory - submodules is None or an iterable of subdirectory name strings
- FMA SPEC post-condition：- Returns True when all of the following hold: (a) phases_json is a readable file whose content parses as valid JSON, (b) the JSON contains at least one source file entry across all phases and modules, (c) every source file path listed in the JSON resolves to an existing file under proj_dir, (d) when submodules is not None, every listed source file path falls under at least one of the specified submodule directories, and (e) every source file under the project directories scoped by submodules (or under all of proj_dir when submodules is None) appears in the JSON - Returns False when any of (a)-(e) fails - Backslash separators in source file paths within the JSON are treated as forward slashes for path comparison and file existence resolution - The f…
- FMA 推导 actual POST：The function returns True if and only if all of the following hold: (1) opening and JSON-parsing the file at `phases_json` succeeds without raising `OSError` or `ValueError`; (2) the parsed JSON yields a non-empty set of source-file paths (after normalizing backslashes to '/') from the 'phases'[].'modules'[].'source_files'[] structure; (3) when `submodules` is truthy (non-None, non-empty), every such path contains at least one string from `submodules` as a path component (as defined by `_is_under_submodules`); (4) for every such path, `os.path.exists(os.path.join(proj_dir, sf))` evaluates to `True`; (5) the set of all discoverable source files under `proj_dir` (restricted to `submodules` when provided, otherwise the whole directory) is a subset of t…

</details>

#### FMA-MISMATCH-181 — `src--pipeline_setup-py--_post_process_phases`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_post_process_phases.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_post_process_phases.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_post_process_phases.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_post_process_phases.py)
- 触发/冲突：one_phase=True with already-single-phase phases.json returns True despite no structural modifications, because or one_phase is unconditionally included in the phases_modified check at line 994.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string path to an existing project root directory. - work_dir is a string path to a writable fm_agent workspace directory. - phases.json exists under work_dir and conforms to the phases.json schema (a JSON object with a "phases" array; each phase has "phase" (int) and "modules" (array), each module has "source_files" (array)). - required_source_files is None or an iterable of file path strings relati…
- FMA SPEC post-condition：- phases.json is updated in-place (file overwritten) through a sequence of transformations applied in order: ensure required source files filter submodules deduplicate update module descriptions clean empty phases optionally collapse to single phase. - When required_source_files is non-None, any listed file not already present in phases.json is inserted; the function prints a message to stdout reporting the count and names of forced files. - When submodules is non-None, any source file whose path does not begin with one of the submodule directory names is removed from phases.json; the function prints a message to stdout reporting the count of removed files. - After deduplication, each source file path appears in exactly one phase. phases.json reflec…
- FMA 推导 actual POST：If the function completes without raising an exception, then (1) the file at `os.path.join(work_dir, 'phases.json')` has been updated by applying, in order, the transformations specified by `_ensure_source_files_in_phases`, `_filter_phases_to_submodules`, `_deduplicate_phases`, `_update_module_description`, `_clean_empty_phase_module`, and (if `one_phase` is truthy) `_collapse_phases_to_one`. As a result: all file paths in `required_source_files` (if nonNone) that were not initially present have been added; if `submodules` is nonNone, any source file whose path does not start with one of the submodule directory names has been removed; each source file appears in exactly one phase (duplicates eliminated); empty phases have been deleted and remaining…

</details>

#### FMA-MISMATCH-182 — `src--pipeline_setup-py--_prepare_workflow_file`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_prepare_workflow_file.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_prepare_workflow_file.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_prepare_workflow_file.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_prepare_workflow_file.py)
- 触发/冲突：The source_files instruction rewrite uses a hard-coded em-dash (—) that fails to match source files using a regular hyphen (-), silently leaving the instruction unchanged.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir, work_dir, and script_dir are existing directory paths - workflow_filename is a string such that the file script_dir/md/workflow_filename exists and is readable
- FMA SPEC post-condition：- A copy of the file script_dir/md/workflow_filename exists at work_dir/workflow_filename with file metadata preserved from the source - The source_files instruction in the copied file is rewritten to reference the absolute path of proj_dir as the project root and to include an example clarifying that paths must be relative to that root (not prefixed with the project directory name) - When one or more domain knowledge files are staged under work_dir, the copied file includes an appended section listing each staged file as a user-provided domain knowledge reference formatted as Markdown bullets - When no domain knowledge files are staged, the copied file contains only the rewritten source_files instruction and is otherwise identical to the source - T…
- FMA 推导 actual POST：If the function returns normally, the file at `os.path.join(work_dir, workflow_filename)` exists and its content is equivalent to the following sequence of transformations applied to the original content of `os.path.join(script_dir, 'md', workflow_filename)`: (1) The first occurrence of the exact string `"- `phases[*].modules[*].source_files` relative paths from repo root of all source files that belong to this module."` is replaced by `f"- `phases[*].modules[*].source_files` relative paths from the project root `{os.path.abspath(proj_dir)}` of all source files that belong to this module. For example, a file at `{os.path.abspath(proj_dir)}/path/to/file.ext` must be recorded as `path/to/file.ext`, NOT as `{os.path.basename(os.path.abspath(proj_dir))}…

</details>

#### FMA-MISMATCH-183 — `src--pipeline_setup-py--_run_generate_domain_context`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_run_generate_domain_context.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_run_generate_domain_context.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_run_generate_domain_context.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_run_generate_domain_context.py)
- 触发/冲突：_prepare_workflow_file is called unconditionally on line 1007 before the _resume_skip early-return, causing workflow_generate_domain_context.md to be created even when resume=True and domain context is already complete.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir, work_dir, and script_dir refer to existing directory paths - phases.json exists under work_dir - resume is a boolean
- FMA SPEC post-condition：- On normal return: the directory spec_prompts/domain_context/ within work_dir contains engine_overview.txt and exactly one file matching the pattern phase_NN_types.txt for each phase defined in phases.json - When resume is truthy and the domain context files under spec_prompts/domain_context/ already satisfy the pipeline's completeness criteria, the function returns without producing or modifying any files - If complete domain context is not produced after a configurable maximum number of retry attempts, the function prints a diagnostic message to stdout identifying the failed stage and the trace directory, then calls sys.exit(1) - When a non-final attempt fails to produce complete domain context, the function does not call sys.exit(1) it waits a f…
- FMA 推导 actual POST：Natural Language Post-condition: After execution, if the function returns normally (no exception and no call to sys.exit), then the workflow file 'workflow_generate_domain_context.md' exists under fm_agent/ in the project directory, and the domain context completeness condition holds (i.e., _domain_context_complete(work_dir) returns True). If the function raises an unhandled exception (e.g., from file operations), the state is partially updated (with the workflow file possibly created) and no guarantees about completeness are made. If the function calls sys.exit(1) after exhausting all retries, the process terminates with exit code 1 and the domain context remains incomplete. Formal Logic: Let proj_dir, work_dir, script_dir be given. After the funct…

</details>

#### FMA-MISMATCH-184 — `src--pipeline_setup-py--_run_generate_phases`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_run_generate_phases.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_run_generate_phases.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_run_generate_phases.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_run_generate_phases.py)
- 触发/冲突：_run_generate_phases uses _json_file_is_valid() to validate phases.json — it only checks JSON validity, not schema conformance, so any valid JSON (e.g. {}) passes even though it lacks required phases fields.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir, work_dir, and script_dir refer to existing directory paths - is_incremental is a boolean; when truthy, a pre-existing phases.json under work_dir is updated in place rather than regenerated from scratch - resume is a boolean - submodules is None or a non-empty iterable of subdirectory name strings relative to proj_dir
- FMA SPEC post-condition：- On normal return: phases.json exists under work_dir and conforms to the phases.json schema - When resume is truthy and phases.json already satisfies the pipeline's completeness criteria, the function returns without producing or modifying any file - When submodules is provided: phases.json covers all source files under the specified subdirectories of proj_dir; source files outside those subdirectories are neither added nor required to be present - When is_incremental is truthy: a valid phases.json already present under work_dir may be accepted without modification if it covers all current source files, even when its modification timestamp has not changed - If valid phases.json is not produced or confirmed after a configurable maximum number of ret…
- FMA 推导 actual POST：After the code block finishes, the original input parameters (`proj_dir`, `work_dir`, `script_dir`, `is_incremental`, `resume`, `submodules`) remain unchanged. The file `workflow_generate_phases.md` and any staged domain knowledge files are unmodified. One of the following mutually exclusive outcomes holds: 1. **Phase plan ready (break):** A `break` statement has been executed, exiting the enclosing retry loop. The variable `phase_plan_ready` is `True`, and the file `phases.json` exists under `work_dir/fm_agent/`. Depending on the configuration: - If `submodules` is not `None`, every source file under the specified subdirectories is referenced in `phases.json`. - If `is_incremental` is `True` and `submodules` is `None`, either the modification time…

</details>

#### FMA-MISMATCH-185 — `src--pipeline_setup-py--_update_module_description`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_update_module_description.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_update_module_description.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_update_module_description.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_update_module_description.py)
- 触发/冲突：The retry delay between failed agent attempts is hard-coded as time.sleep(10) with no configurable mechanism; spec requires a configurable fixed interval.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string path to the project root directory. - work_dir is a string path to a writable fm_agent workspace directory. - modified_modules is an iterable of module name strings (may be empty).
- FMA SPEC post-condition：- When modified_modules is empty: returns immediately with no side effects. - When phases.json does not exist under work_dir: logs an informational message and returns with no side effects. - When, after checking phases.json, none of the modules named in modified_modules still owns any source file: logs an informational message and returns with no side effects. - Otherwise: delegates to an agent to rewrite the description field of every module in modified_modules whose source file list in phases.json differs from its pre-deduplication state. Each rewritten description accurately reflects the module's current set of owned source files. - The delegation is retried up to a configurable maximum number of attempts. Between consecutive failed attempts, th…
- FMA 推导 actual POST：After execution, if modified_modules is empty, the function returns immediately leaving the filesystem unchanged and no trace events written. Otherwise, if phases.json does not exist in work_dir, an info log is emitted and the function returns with no modifications. Otherwise, a prompt is built from the modified_modules and phases.json path; if that prompt is falsy, an info log is emitted and the function returns without invoking the agent. Otherwise (non-empty modified_modules, phases.json exists, valid prompt), the function retries running an external agent up to OPENCODE_MAX_RETRIES times. On each attempt, run_opencode_traced is called; if it succeeds (exit 0), a success trace event is written under fm_agent/trace/, phases.json may be updated by…

</details>

#### FMA-MISMATCH-186 — `src--pipeline_setup-py--types_path`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/types_path.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/types_path.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--types_path.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--types_path.py)
- 触发/冲突：types_path uses os.path.join without os.path.abspath, so when domain_dir is relative the returned path is relative, violating the absolute-path specification.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- num is an integer representing a phase number - domain_dir is defined in the enclosing scope as a valid directory path string pointing to the domain context directory within the fm_agent workspace
- FMA SPEC post-condition：- Returns the absolute file path to the domain context types file for phase num, constructed as <domain_dir>/phase_<num:02d>_types.txt where num is zero-padded to at least 2 digits - The returned path uses the operating system's native path separator - The return value is purely a path string no filesystem side effects occur
- FMA 推导 actual POST：After executing the function definition, the name 'types_path' is bound to a function object in the current scope. The function captures the enclosing scope's variable 'domain_dir' at its current value. For any integer argument x, a call to types_path(x) returns the string obtained by os.path.join(domain_dir, f'phase_{x:02d}_types.txt'), where domain_dir is the captured directory path string. No other program state (other variables, global state) is changed by the definition. The definition itself raises no exceptions. Formal logic: types_path = ( x. os.path.join(domain_dir_pre, f'phase_{x:02d}_types.txt')), where domain_dir_pre is the value of domain_dir before the block execution, and the binding of domain_dir is unaltered.

</details>

#### FMA-MISMATCH-250 — `src--pipeline_setup-py--_sync_domain_context`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/pipeline_setup-py/_sync_domain_context.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/pipeline_setup-py/_sync_domain_context.json) · [具体 bug 报告](../fm_agent/bug_validation/src--pipeline_setup-py--_sync_domain_context.md) · [probe](../fm_agent/bug_validation/probe_src--pipeline_setup-py--_sync_domain_context.py)
- 触发/冲突：Agent invocation fails; spec requires retry up to OPENCODE_MAX_RETRIES with delay, then warn and return without raising. Code already implements this.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a path to an existing project directory. - work_dir is a path to an existing fm_agent workspace directory. - changed_phases is a collection of integer phase numbers, possibly empty. - phase_cleanup, when provided, is a dict optionally containing key "removed_phases" (list of integer phase numbers) and key "renumbered" (dict mapping old phase number to new phase number, where both are non-None integers)…
- FMA SPEC post-condition：- Returns without effect when changed_phases is empty and no phase removal or renumbering has occurred. - Returns without invoking the LLM agent when the domain_context subdirectory (spec_prompts/domain_context/) is absent under work_dir. - Returns without invoking the LLM agent when every changed phase owns zero source files per phases.json and no cleanup renumbering/removal is pending. - When invoked, the LLM agent receives phases.json and all staged domain-knowledge Markdown files as input and is instructed to regenerate phase_NN_types.txt files only for phases whose source-file composition changed. - The agent invocation is retried up to a configured maximum (OPENCODE_MAX_RETRIES), with a delay between attempts. On success the function returns;…
- FMA 推导 actual POST：After execution, one of the following holds: 1. The function raises `subprocess.CalledProcessError`. This occurs when the LLM agent subprocess is invoked but fails (non-zero exit). An error trace event is recorded in `<work_dir>/trace/events.jsonl`. The state of domain context files in `<work_dir>/spec_prompts/domain_context/` may be partially updated. 2. The function returns normally without invoking the agent (early return). This happens if (a) `changed_phases` is empty and `cleanup_changed` is false, or (b) `<work_dir>/spec_prompts/domain_context/` does not exist, or (c) after loading source files from `phases.json`, the set `regenerate` (phases in `changed_phases` that still have files) is empty and `cleanup_changed` is false. In all these cases…

</details>

### `src--prompts-py`

#### FMA-MISMATCH-187 — `src--prompts-py--_check_post_implies_spec`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/prompts-py/_check_post_implies_spec.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/prompts-py/_check_post_implies_spec.json) · [具体 bug 报告](../fm_agent/bug_validation/src--prompts-py--_check_post_implies_spec.md) · [probe](../fm_agent/bug_validation/probe_src--prompts-py--_check_post_implies_spec.py)
- 触发/冲突：When _retry_create raises a non-ValueError exception, the bare raise on line 88 re-raises it as-is instead of ValueError as required by the spec.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- block is a non-empty string containing code statements, possibly with "Line N:" prefixes - post_condition is a non-empty string describing the state guaranteed after executing block under some prior pre-condition - spec_post_condition is a non-empty string describing the post-condition required by the specification - knowledge is a mapping from callee function names to their behavioral specifications; may be empty…
- FMA SPEC post-condition：- Returns a tuple (passed: bool, offending_stmts: str|None, computed_post_cond: str|None, violation_reason: str|None) - When the set of program states described by post_condition is a subset of the set described by spec_post_condition (i.e., post_condition logically implies spec_post_condition for all valid inputs), returns (True, None, None, None) - When there exists a concrete valid input for which post_condition does not guarantee spec_post_condition, returns (False, offending_stmts, post_condition, violation_reason) where offending_stmts and violation_reason are non-empty strings - offending_stmts preserves "Line N:" prefixes from block when present, identifying the specific statements responsible for the violation - When no definitive MATCH or…
- FMA 推导 actual POST：If _retry_create raises an exception E, then response remains None, usage remains {}, an event with status 'error' is recorded, and the exception E is reraised. If _retry_create succeeds, returning (resp, usg), then response = resp and usage = usg. In that case, if _parse_spec_check_json(resp) raises a ValueError exc_parse, then has_violation = None, stmts = None, reason = None, parse_error = str(exc_parse), status = 'format_error', messages is extended with an assistant message containing resp and a user message requesting valid JSON, and a new ValueError with message 'Could not parse a valid structured JSON verdict from spec-check response.' is raised. If _parse_spec_check_json(resp) succeeds, returning (hv, stm, rsn, prs), then parsed_result = pr…

</details>

#### FMA-MISMATCH-188 — `src--prompts-py--_generate_block_post_condition`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/prompts-py/_generate_block_post_condition.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/prompts-py/_generate_block_post_condition.json) · [具体 bug 报告](../fm_agent/bug_validation/src--prompts-py--_generate_block_post_condition.md) · [probe](../fm_agent/bug_validation/probe_src--prompts-py--_generate_block_post_condition.py)
- 触发/冲突：_generate_block_post_condition propagates exceptions from _llm_json_call instead of returning None when post-condition cannot be determined
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- block is a non-empty string containing code statements, possibly with "Line N:" prefixes - pre_condition is a non-empty string describing the logical state assumed to hold before block begins execution - knowledge is a mapping from callee function names to their behavioral specifications; may be empty or falsy - language is a non-empty string identifying the source programming language of the code in block - trace…
- FMA SPEC post-condition：- Returns a string describing the strongest post-condition that must hold after executing block from the given pre-condition, covering all execution paths through the block including normal flow-through, early returns, and exceptional exits - Returns None when the post-condition could not be determined from the given inputs - The returned post-condition is expressed in natural language suitable for subsequent logical implication checks against specification post-conditions
- FMA 推导 actual POST：Normal execution: The function constructs `info_str` (either an empty string or a formatted string containing `knowledge`), `messages` (list of two dicts with system and user prompts built from the given `language`, `pre_condition`, `block`, and `info_str`), and `meta` (a dict with fixed keys `purpose` and `summary`, merged with `trace_meta` if provided). It then returns the result of `_llm_json_call(_llm_provider_client, REASONER_POST_CONDITION_MODEL, messages, _parse_post_condition_json, '{"post_condition": "non-empty string"}', trace_dir=trace_dir, trace_meta=meta)`. Exceptional execution: If `_llm_provider_client`, `REASONER_POST_CONDITION_MODEL`, or `_parse_post_condition_json` are undefined, a `NameError` propagates. Any exception raised by `_…

</details>

#### FMA-MISMATCH-189 — `src--prompts-py--_parse_spec_check_json`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/prompts-py/_parse_spec_check_json.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/prompts-py/_parse_spec_check_json.json) · [具体 bug 报告](../fm_agent/bug_validation/src--prompts-py--_parse_spec_check_json.md) · [probe](../fm_agent/bug_validation/probe_src--prompts-py--_parse_spec_check_json.py)
- 触发/冲突：WHITESPACE ONLY: MATCH verdict with counterexample=' ' (whitespace-only string) should raise ValueError per spec but code's _nonempty_string() strips first and treats it as empty, returning a tuple instead.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- response is a non-empty string
- FMA SPEC post-condition：- Raises ValueError if response is not valid JSON text - Raises ValueError if the parsed JSON value is not a mapping (dict) - Raises ValueError if the parsed mapping does not contain all of the required keys: "verdict", "counterexample", "offending_statements", "reason" - Raises ValueError if the "verdict" value, after conversion to uppercase, is neither "MATCH" nor "MISMATCH" - Raises ValueError if "counterexample" is present and not null-valued but is not a string - Raises ValueError if "offending_statements" is present and not null-valued but is not a string - Raises ValueError if "reason" is not a string value - For "MISMATCH" verdict: raises ValueError if any of counterexample, offending_statements, or reason is empty or consists only of whites…
- FMA 推导 actual POST：The function either raises a ValueError or returns a tuple. In case of a ValueError, one of the following conditions holds: (1) response is not valid JSON (ValueError with message starting 'spec-check response is not valid JSON:'); (2) the parsed JSON is not a dict (ValueError: 'spec-check JSON must be an object'); (3) the dict lacks any of the required fields 'verdict', 'counterexample', 'offending_statements', 'reason' (ValueError: 'spec-check JSON missing required field(s): ...'); (4) the 'verdict' field, after uppercasing if string, is not 'MATCH' or 'MISMATCH' (ValueError: 'spec-check JSON verdict must be MATCH or MISMATCH'); (5) 'counterexample' is neither None nor a string ('spec-check JSON field counterexample must be a string or null'); (6)…

</details>

#### FMA-MISMATCH-251 — `src--prompts-py--_load_spec_check_json`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/prompts-py/_load_spec_check_json.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/prompts-py/_load_spec_check_json.json) · [具体 bug 报告](../fm_agent/bug_validation/src--prompts-py--_load_spec_check_json.md) · [probe](../fm_agent/bug_validation/probe_src--prompts-py--_load_spec_check_json.py)
- 触发/冲突：When response is 42 (an integer), _parse_json_response raises ValueError (not TypeError), which IS caught by except ValueError and correctly converted to json.JSONDecodeError — the code already satisfies the spec.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- response is a non-empty string
- FMA SPEC post-condition：- Returns a dict, which is the Python object produced by deserializing the JSON content extracted from response - Raises json.JSONDecodeError if response does not contain extractable JSON - Raises json.JSONDecodeError if the extracted JSON content is not a dict (i.e., is a list, string, number, boolean, or null)
- FMA 推导 actual POST：If the input string `response` contains a JSON object that can be extracted by `_parse_json_response`, the function returns the corresponding dictionary. Otherwise, it raises `json.JSONDecodeError`. Formally: Let `parse(s)` be the result of `_parse_json_response(s)`. For any non-empty string `response`, ( d dict: `parse(response)` terminates successfully and returns d) the function returns d ( `parse(response)` raises `ValueError` `parse(response)` returns a value that is not a `dict` ) the function raises `json.JSONDecodeError`.

</details>

### `src--reasoner-py`

#### FMA-MISMATCH-190 — `src--reasoner-py--_compute_brace_depth_per_line`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/reasoner-py/_compute_brace_depth_per_line.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/reasoner-py/_compute_brace_depth_per_line.json) · [具体 bug 报告](../fm_agent/bug_validation/src--reasoner-py--_compute_brace_depth_per_line.md) · [probe](../fm_agent/bug_validation/probe_src--reasoner-py--_compute_brace_depth_per_line.py)
- 触发/冲突：Multi-line block comment /* ... */ is not tracked across lines; braces on lines after an unclosed /* are incorrectly counted, producing negative depth.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- lines is a non-empty list of strings, each containing one line of function body text without "Line N:" prefixes
- FMA SPEC post-condition：- Returns a list of non-negative integers whose length equals the number of elements in lines - For each position i (0-indexed), the integer at that position is the cumulative net count of opening brace characters '{' minus closing brace characters '}' encountered across lines[0] through lines[i], inclusive - Brace characters that occur inside a double-quoted string literal do not contribute to the count: upon encountering an unescaped '"' character, counting of braces is suspended until the next unescaped '"', where a backslash preceding the quote is considered an escape - Brace characters that occur inside a single-quoted character literal do not contribute to the count: upon encountering an unescaped "'" character, counting of braces is suspended…
- FMA 推导 actual POST：The function returns a list `depths` of integers such that `len(depths) == len(lines)`. For all indices `k` with 0 k < len(lines), `depths[k]` is the cumulative brace depth after processing the first `k+1` lines, computed as follows: let `d_0 = 0`; for each `j` from 0 to `k`, define `d_{j+1} = process(lines[j], d_j)`, where `process(line, d)` scans the line left to right, maintaining a depth counter starting at `d`. While scanning, the following syntactic regions are skipped (their characters are ignored for brace counting, exactly as implemented): (i) a double-quoted string literal starting with `"` and ending with the matching unescaped `"`, where a backslash `\` escapes the next character (the scanner advances two characters for an escape), (ii)…

</details>

#### FMA-MISMATCH-191 — `src--reasoner-py--_has_terminating_statement`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/reasoner-py/_has_terminating_statement.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/reasoner-py/_has_terminating_statement.json) · [具体 bug 报告](../fm_agent/bug_validation/src--reasoner-py--_has_terminating_statement.md) · [probe](../fm_agent/bug_validation/probe_src--reasoner-py--_has_terminating_statement.py)
- 触发/冲突：An if/else Python block where the if-branch contains 'return' but the else-branch falls through without terminating triggers the bug: the regex finds 'return' and returns True, but the spec requires False because not every path terminates.
- 成因复核：调用方需要知道 block 是否“含有”提前终止路径以触发检查；SPEC 将函数提升为“所有路径都终止”的控制流证明器，与正则实现和调用方式都不符。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- block is a non-empty string containing one or more code statements - language is a string identifying a valid programming language
- FMA SPEC post-condition：- Returns True when every syntactically reachable execution path through `block` ends in an unconditional termination statement (return, raise, system exit, or an equivalent language-specific construct) before reaching the end of the block - Returns False when there exists at least one syntactically reachable execution path through `block` that can fall through to subsequent code without terminating
- FMA 推导 actual POST：The function returns a boolean value indicating whether the input `block` string contains a terminating statement pattern. Formally: let `default_regex = r'\b(return\b|exit\s*\(|raise\s|throw\s|abort\s*\()'`. Let `pattern` be the value of `_TERMINATING_PATTERNS.get(language.lower())` if that value is truthy (i.e., not None and not empty); otherwise, `pattern = default_regex`. The return value is `True` if and only if `re.search(pattern, block)` returns a non-`None` match object, and `False` otherwise. No side effects occur; the program state is identical except that the function returns this value. This post-condition holds for all execution paths, as there are no early returns or exceptions.

</details>

#### FMA-MISMATCH-192 — `src--reasoner-py--_parse_spec_conditions`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/reasoner-py/_parse_spec_conditions.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/reasoner-py/_parse_spec_conditions.json) · [具体 bug 报告](../fm_agent/bug_validation/src--reasoner-py--_parse_spec_conditions.md) · [probe](../fm_agent/bug_validation/probe_src--reasoner-py--_parse_spec_conditions.py)
- 触发/冲突：A spec with an intermediate section header (e.g. 'Note:') between 'Pre-condition:' and 'Post-condition:' causes the regex to include the intermediate section in pre_condition.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- spec is a string that may contain specification text with Pre-condition and/or Post-condition sections
- FMA SPEC post-condition：- Returns a 2-tuple (pre_condition, post_condition) - pre_condition is the text content between the "Pre-condition:" header line and the next section boundary, with leading and trailing whitespace stripped; it is None when no "Pre-condition:" section is found in the spec string - post_condition is the text content between the "Post-condition:" header line and the end of the string, with leading and trailing whitespace stripped; it is None when no "Post-condition:" section is found in the spec string
- FMA 推导 actual POST：The function returns a tuple (pre, post). Define pre_match = re.search(r'Pre-condition:\s*\n(.*?)(?=\nPost-condition:|\Z)', spec, re.DOTALL); pre = pre_match.group(1).strip() if pre_match else None. Define post_match = re.search(r'Post-condition:\s*\n(.*)', spec, re.DOTALL); post = post_match.group(1).strip() if post_match else None. Therefore, pre is the stripped content of the 'Pre-condition:' section if it exists (i.e., the substring after the newline following 'Pre-condition:', up to the next 'Post-condition:' line or end of spec), else None; post is the stripped content of the 'Post-condition:' section if it exists (i.e., the substring after the newline following 'Post-condition:' to the end of spec), else None.

</details>

#### FMA-MISMATCH-193 — `src--reasoner-py--_split_into_blocks_braced`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/reasoner-py/_split_into_blocks_braced.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/reasoner-py/_split_into_blocks_braced.json) · [具体 bug 报告](../fm_agent/bug_validation/src--reasoner-py--_split_into_blocks_braced.md) · [probe](../fm_agent/bug_validation/probe_src--reasoner-py--_split_into_blocks_braced.py)
- 触发/冲突：For brace-delimited languages, the final block never returns to entry depth; with func='{...}' and GRANULARITY=1, block '}' ends at depth 0 instead of entry depth 1.
- 成因复核：最终右花括号把深度从 entry depth 降到 0 是函数正常结束；SPEC 要求每个块都停在 entry depth，错误排除了合法的最后一块。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- func is a non-empty string containing the body of a function, each line optionally prefixed with "Line N: " followed by the source text - language is a string identifying the source programming language
- FMA SPEC post-condition：- Returns a non-empty list of strings, each being a contiguous, non-overlapping segment of the function body, appearing in the same order as in the original body - For brace-delimited languages: every boundary between consecutive returned segments occurs at a line whose brace-nesting depth equals the brace-nesting depth at the first meaningful brace level of the function body. Each segment is therefore syntactically self-contained with respect to brace structure it begins and ends at the same nesting depth as the function's entry depth - For languages that use indentation for syntactic structure (classified as Python-like by the function): segments are split at boundaries that respect indentation-level changes, with each segment being a syntacticall…
- FMA 推导 actual POST：**Natural Language:** The function `_split_into_blocks_braced` returns a nonempty list of strings, each representing a contiguous block of lines from the input function body. The blocks are constructed so that their ordered concatenation with newline characters exactly reproduces the whole function body after stripping leading and trailing whitespace (i.e., `func.strip()`). If `language.lower()` belongs to the set `{"python"}`, or if the computed bracedepth entry point is zero after the algorithms fallback, the returned value is the result of calling `_split_into_blocks(func)`, which splits on indentation boundaries (that function preserves the stripped reconstruction property). Otherwise, the function removes any Line N: prefixes from the lines, co…

</details>

### `src--scope-py`

#### FMA-MISMATCH-194 — `src--scope-py--_base_score`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/_base_score.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/_base_score.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--_base_score.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--_base_score.py)
- 触发/冲突：Body identifiers (idents) intersecting with backtick identifiers (backtick_idents) contribute W_BACKTICK_BODY to the score, which is not a permitted category in the specification.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- name is a non-empty string; the function name being scored - idents is a set of identifier strings extracted from the function body - body_words is a set of distinct word tokens from the function body - exc_types is a set of exception type names referenced in the function body - body_lines is a positive integer representing the number of lines in the function body - signals is a dict containing exactly the followi…
- FMA SPEC post-condition：- Returns a non-negative float representing the heuristic relevance of the function to the developer intent described by signals - The score is the sum of weighted contributions from multiple signal categories: (a) a contribution when name matches a traceback function name (case-insensitive) or when a component of name matches one (b) contributions proportional to the size of the set intersection between name components and backtick identifiers, dotted-reference method names, and plain prose identifiers, each category carrying a distinct pre-defined weight (c) a contribution proportional to the intersection between name components of length 5 characters and alphabetic prose words from the intent (d) a typo-tolerant contribution that applies only whe…
- FMA 推导 actual POST：The function returns a float value computed as follows. Let parts = _name_parts(name) (the set of lowercased name components). Let specific_name_words = {p in parts | len(p) >= 5}. The returned score is the sum of: (i) W_TRACEBACK * |{tf in signals['traceback_funcs'] | tf.lower() == name.lower() or tf.lower() in parts}|; (ii) W_BACKTICK_NAME * |parts signals['backtick_idents']|; (iii) W_BACKTICK_BODY * |idents signals['backtick_idents']|; (iv) W_DOTTED_REF * |parts signals['dotted_refs']|; (v) W_PLAIN_NAME * |parts signals['plain_idents']|; (vi) W_NAME_ALL_WORDS * |specific_name_words signals['all_words']|; (vii) _fuzzy_name_score(parts, signals); (viii) if signals['exception_types'] and exc_types then W_EXCEPTION_MATCH * |signals['exception_types']…

</details>

#### FMA-MISMATCH-195 — `src--scope-py--_collect_func_idents`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/_collect_func_idents.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/_collect_func_idents.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--_collect_func_idents.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--_collect_func_idents.py)
- 触发/冲突：body_words regex uses {4,} minimum characters but spec requires ≥3 characters; 3-letter words like 'bar' and 'baz' are silently excluded.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- node is an AST node rooted at a FunctionDef or AsyncFunctionDef with lineno and end_lineno attributes set. - source_lines is a list[str] containing every line of the source file that produced node, in original order, with trailing newlines removed.
- FMA SPEC post-condition：- Returns a 3tuple (idents, body_words, exc_types) where each element is a set[str] whose members are lowercased. No returned set contains the empty string. - idents contains every identifier whose value is read at least once within the function body. An identifier whose value is read includes: any name resolved as a value (Load context), the attribute name in any attributeaccess expression, and any functionparameter name that appears in the body in a value position. Identifiers that only appear in write (Store) or deletion (Del) contexts are excluded. - body_words contains every distinct alphabetic word of at least 3 characters that appears in the source text spanning from the function's first line through its last line (inclusive), after excluding…
- FMA 推导 actual POST：After execution, the function returns a tuple (idents, body_words, exc_types) such that: - idents = {s.lower() | n ast.walk(node), (s = n.id if isinstance(n, ast.Name)) or (s = n.attr if isinstance(n, ast.Attribute)) or (s = n.arg if isinstance(n, ast.arg)) or (isinstance(n, ast.Constant) and isinstance(n.value, str) and s re.findall(r'[a-zA-Z_][a-zA-Z0-9_]{2,}', n.value))} - exc_types = {e.lower() | n ast.walk(node), ((isinstance(n, ast.Raise) and n.exc != None and (let exc_ref = n.exc.func if isinstance(n.exc, ast.Call) else n.exc in (e = exc_ref.id if isinstance(exc_ref, ast.Name)) or (e = exc_ref.attr if isinstance(exc_ref, ast.Attribute)))) or (isinstance(n, ast.ExceptHandler) and n.type != None and ((e = n.type.id if isinstance(n.type, ast.Nam…

</details>

#### FMA-MISMATCH-196 — `src--scope-py--_extract_backtick_idents`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/_extract_backtick_idents.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/_extract_backtick_idents.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--_extract_backtick_idents.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--_extract_backtick_idents.py)
- 触发/冲突：Input '`__init__`' causes .strip('_') to drop underscores, returning {'init'} instead of spec-expected {'__init__'}
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- issue_text is a string
- FMA SPEC post-condition：- Returns a set of lowercased identifier strings extracted from issue_text - Every returned string has length 2 and consists of ASCII letters, digits, and underscores - An identifier is included if and only if it appears within a backtick-quoted span (`` `...` ``) or a triple-backtick-fenced code block (`` ```...``` ``) in issue_text - Identifiers that match Python language keywords or a fixed set of common built-in / stop-word names are excluded from the returned set - For backtick-quoted spans, leading RST/Sphinx role prefixes of the form `<word>:<word>` are stripped before identifier extraction; the prefix portion contributes no identifiers to the result - Within code blocks, only identifiers of length 3 characters are extracted
- FMA 推导 actual POST：The function returns a set `result` of strings. Each string `t` in `result` satisfies: - `t` is a valid identifier-like token extracted from `issue_text`, - `t` has length at least 2, is not in `_PY_KEYWORDS` and not in `_STOP`, - `t` is obtained by lowercasing and stripping leading/trailing underscores from a match. Formally: result = { t | ( raw re.findall(r'`([^`]+)`', issue_text) : cleaned = re.sub(r'^[a-z]+:[a-z]+\s*', '', raw.strip()) part re.findall(r'[a-zA-Z_][a-zA-Z0-9_]{1,}', cleaned) t = part.lower().strip('_') len(t) 2 t _PY_KEYWORDS t _STOP ) ( block re.findall(r'```.*?```', issue_text, re.DOTALL) : ident re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b', block) t = ident.lower().strip('_') len(t) 2 t _PY_KEYWORDS t _STOP ) }

</details>

#### FMA-MISMATCH-197 — `src--scope-py--_extract_classes`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/_extract_classes.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/_extract_classes.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--_extract_classes.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--_extract_classes.py)
- 触发/冲突：ast.walk visits nested classes (Inner included, should be module-scope only); per-method detail sub-dicts entirely missing from class output
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- tree is a valid AST for a Python module, produced by ast.parse without raising an exception. - source_lines is a list[str] containing every line of the source file that produced tree, in original order, with trailing newlines removed.
- FMA SPEC post-condition：- Returns a list of dicts, one per class defined at module scope in tree. - The list is ordered by ascending class start line (1based lineno). - Each dict contains at minimum these keys: * 'name' (str): the class name as written in the source code. * 'lineno' (int): the 1based line number of the class definition header. * 'end_lineno' (int): the 1based line number of the last line of the class body. * 'docstring' (str): the docstring text of the class, or the empty string when no docstring is present. * 'method_linenos' (list[int]): the 1based line numbers of every method (FunctionDef or AsyncFunctionDef) defined directly within the class body, sorted in ascending order. - Each dict also contains permethod detail entries following the same field sch…
- FMA 推导 actual POST：The function returns a list `C` of dictionaries such that: - Natural language: The list contains one entry for every class definition in the AST, visited in depth-first preorder (the order produced by `ast.walk`). Each entry is a dict with keys `name`, `lineno`, `end_lineno`, `docstring`, `method_linenos`. The value for `name` is the class name (string). The values for `lineno` and `end_lineno` are the starting and ending line numbers of the class definition (integers from the AST node). The value for `docstring` is the class's docstring as extracted by `ast.get_docstring`, or an empty string if none is present. The value for `method_linenos` is a list of integers containing the line numbers of every `ast.FunctionDef` and `ast.AsyncFunctionDef` node…

</details>

#### FMA-MISMATCH-198 — `src--scope-py--_fuzzy_name_score`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/_fuzzy_name_score.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/_fuzzy_name_score.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--_fuzzy_name_score.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--_fuzzy_name_score.py)
- 触发/冲突：Case-sensitive set membership check fails to skip intent tokens with different casing than name parts; spec requires case-insensitive matching.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- parts is a non-empty set of lowercased strings; the component tokens of a function name - signals is a dict containing at minimum the keys 'backtick_idents', 'plain_idents', 'dotted_refs', and 'all_words', each with a set[str] value drawn from developer intent text
- FMA SPEC post-condition：- Returns a non-negative float quantifying fuzzy (typo-tolerant) string similarity between function name parts and developer intent tokens - The score considers all tokens from the union of the four signal sets - Only tokens of length FUZZY_NAME_MIN_LEN that are not common stop words or Python language keywords can contribute - An intent token that has an exact case-insensitive match among the qualified name parts does NOT contribute to this score (exact matches are scored elsewhere by the caller) - For each remaining qualified intent token, if the best string-similarity ratio against any qualified name part is at least FUZZY_NAME_THRESHOLD, the product W_FUZZY_NAME (that best ratio) is added to the result - Returns 0.0 when no qualified intent toke…
- FMA 推导 actual POST：Returns a float score computed as W_FUZZY_NAME multiplied by the sum over every intent token t (where t is in the union of signals['backtick_idents'] | signals['plain_idents'] | signals['dotted_refs'] | signals['all_words'], len(t) >= FUZZY_NAME_MIN_LEN, t _STOP, t _PY_KEYWORDS, and t name_tokens) of the maximum SequenceMatcher ratio between t and any name token n (where n parts, len(n) >= FUZZY_NAME_MIN_LEN, n _STOP, n _PY_KEYWORDS, and n intent_tokens), provided that maximum ratio is >= FUZZY_NAME_THRESHOLD; otherwise the contribution for that t is 0.0. No input data structures are modified.

</details>

#### FMA-MISMATCH-199 — `src--scope-py--_generic_func_info`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/_generic_func_info.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/_generic_func_info.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--_generic_func_info.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--_generic_func_info.py)
- 触发/冲突：The body_words regex [a-zA-Z]{4,} only matches ASCII letters, so non-ASCII alphabetic words like 'café' are silently dropped.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- name is a non-empty string; the function name - start0 and end0 are 0-based line indices with start0 ≤ end0 - source_lines is a list[str] of the source file text, with len(source_lines) > end0 - lang_cfg is a dict containing a 'keywords' key whose value is a set[str] of language reserved words
- FMA SPEC post-condition：- Returns a dict containing the canonical metadata and signal fields for one function extracted from a generic (non-Python) source file - The returned dict has exactly the following keys, all present: * 'name': str equal to the input name parameter * 'start': int equals start0 + 1 (1-based inclusive start line) * 'end': int equals end0 + 1 (1-based inclusive end line) * 'calls': set[str] names of functions called within the body, case-preserved, excluding names present in lang_cfg['keywords'] * 'idents': set[str] lowercased identifier-like tokens extracted from the body * 'body_words': set[str] lowercased alphabetic words of length 4 from the body, excluding common stop words * 'exc_types': set[str] lowercased exception-type names extracted from the…
- FMA 推导 actual POST：The function returns a dictionary D with keys 'name', 'start', 'end', 'calls', 'idents', 'body_words', 'exc_types', 'docstring'. Let body_text = ' '.join(source_lines[start0:end0+1]). Then: - D['name'] = name - D['start'] = start0 + 1 - D['end'] = end0 + 1 - D['docstring'] = '' - D['calls'] = {m | m findall(_CALL_RE, body_text) m keywords} - D['idents'] = {s.lower() | s findall(_IDENT_RE, body_text)} - D['body_words'] = {w | w findall(r'\b([a-zA-Z]{4,})\b', body_text.lower()) w _STOP} - D['exc_types'] = {e.lower() | e findall(_EXC_TOKEN_RE, body_text)} where keywords = lang_cfg['keywords'] (guaranteed key) and _CALL_RE, _IDENT_RE, _EXC_TOKEN_RE, _STOP are external constants. All sets are finite and contain only strings. The start and end indices are…

</details>

#### FMA-MISMATCH-200 — `src--scope-py--_llm_rerank`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/_llm_rerank.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/_llm_rerank.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--_llm_rerank.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--_llm_rerank.py)
- 触发/冲突：Mock LLM returns a function name not present in funcs_info; _llm_rerank accepts it without validating membership against funcs_info names.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- funcs_info is a non-empty list of dicts, each with a unique 'name' (str) key, plus 'start' and 'end' keys (int, 1‑based line numbers) identifying the function's source span within source_lines. - source_lines is a list[str] representing the full source text, with at least max(func['end'] for func in funcs_info) elements. - filepath is a non-empty string identifying the source file. - issue is a string describing d…
- FMA SPEC post-condition：- If the LLM produces a valid response, returns a list of function names (nonempty strings), each drawn exclusively from the set of names in funcs_info, in descending order of relevance to the issue as judged by the LLM, with no duplicate names and length at most top_k. - If the LLM does not produce a valid response after the allowed number of attempts, returns None. - The function is idempotent with respect to funcs_info, source_lines, filepath, and issue: repeated calls with the same arguments may produce different rankings (LLM nondeterminism) but each valid ranking obeys the same contract.
- FMA 推导 actual POST：The function terminates normally (does not raise an exception under the given pre-conditions). Let R be the returned value. Then (R is None) XOR (R is a list of strings such that s R, s.strip() != ''). R is None if and only if all three retry attempts failed: each attempt's try block raised an exception (caught, logged with a warning, and, for the first two, followed by an extended messages list and a sleep). R is a non-empty list if and only if some attempt succeeded: the LLM returned a valid JSON array, every element was a string that after stripping was non-empty, and R is exactly [s.strip() for s in that parsed list]. No further validation against funcs_info names is performed. Formally, let S = {x str : x.strip() ''}; then post-condition |= (R…

</details>

#### FMA-MISMATCH-201 — `src--scope-py--_name_parts`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/_name_parts.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/_name_parts.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--_name_parts.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--_name_parts.py)
- 触发/冲突：Input 'a_b_c' produces only {'a_b_c'} instead of {'a_b_c', 'a_b', 'b_c'} because underscore-split tokens of length 1 are filtered out before consecutive pair generation.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- name is a non-empty string
- FMA SPEC post-condition：- Returns a set of lowercased string components derived from name - The full lowercased name is always included as one component - The name is split on underscore characters ("_"); each resulting token whose length is at least 2 is included as a component - Every consecutive pair of underscore-separated tokens is joined by "_" and included as a component (in addition to the individual tokens) - The name is split at each uppercase-to-lowercase transition boundary and at each leading underscore, lowercased, and each resulting token whose length is at least 2 is included as a component - A token that appears in both the underscore split and the case-transition split is included only once (set semantics) - All components are in lowercase - The returned…
- FMA 推导 actual POST：The function returns a set of strings containing: (1) the lowercased input name; (2) all tokens from splitting the lowercased name by underscores that have length greater than 1; (3) all consecutive pairs of those tokens joined by an underscore; (4) all tokens of length greater than 1 obtained by inserting underscores before each uppercase letter in the original name, lowercasing, stripping leading/trailing underscores, and splitting by underscores. Formally: let L = name.lower(); let T = [t for t in L.split('_') if len(t) > 1]; let P = {f'{T[i]}_{T[i+1]}' for i in range(len(T) - 1)}; let C = {p for p in re.sub(r'([A-Z])', r'_\1', name).lower().strip('_').split('_') if len(p) > 1}; then the result = {L} set(T) P C.

</details>

#### FMA-MISMATCH-202 — `src--scope-py--_parse_generic_file`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/_parse_generic_file.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/_parse_generic_file.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--_parse_generic_file.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--_parse_generic_file.py)
- 触发/冲突：Passing a lang_key not in LANG_CONFIG after _function_spans succeeds raises an unhandled KeyError instead of returning (None, None, None) as the spec requires.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- src_path is a Path identifying an existing source file on disk. - lang_key is a non‑empty string identifying a language registered in the parser configuration. - proj_dir, if provided, is a string path to a project root directory used for codegraph‑backed function boundary detection.
- FMA SPEC post-condition：- If the file can be read and function boundaries can be determined, returns (funcs_info, source_lines, []) where: * funcs_info is a list of dicts, each representing one toplevel function defined in the file, with at minimum 'name' (str), 'start' (int, 1based start line), and 'end' (int, 1based end line) keys. * source_lines is a list[str] containing one element per line of the file, in order, with trailing '\n' and '\r' removed from each element. * The third element is always an empty list (classscope narrowing is Pythononly). - If the file cannot be read or function boundaries cannot be determined, returns (None, None, None). - The function does not modify the source file.
- FMA 推导 actual POST：If the call to _function_spans(str(src_path), lang_key, proj_dir) raises an exception, the function returns (None, None, None). Otherwise, let (spans, raw_lines) be the result of that call (which does not raise). Then the function returns (funcs, source_lines, []) where source_lines = [l.rstrip('\n').rstrip('\r') for l in raw_lines] and funcs = [_generic_func_info(name, start0, end0, source_lines, LANG_CONFIG[lang_key]) for (name, start0, end0) in spans]. Every dictionary in funcs contains at least the keys 'name' (str), 'start' (int, 1based start line), and 'end' (int, 1based end line). The third element of the returned tuple is an empty list, indicating no classscope signals. Formally: (ret = (None, None, None)) (ret = (funcs, source_lines, []) (s…

</details>

#### FMA-MISMATCH-203 — `src--scope-py--_parse_issue_signals`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/_parse_issue_signals.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/_parse_issue_signals.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--_parse_issue_signals.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--_parse_issue_signals.py)
- 触发/冲突：traceback_funcs not lowercased; input ' in Foo\n' yields 'Foo' instead of required 'foo'
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- issue_text is a string containing developer-intent prose, which may include Python traceback lines, backtick-quoted identifiers, Class.method references, CamelCase and snake_case names, exception type names, and free-form text.
- FMA SPEC post-condition：- Returns a dict with exactly seven keys, each mapping to a set of lowercased strings: 'traceback_funcs', 'backtick_idents', 'dotted_refs', 'dotted_classes', 'plain_idents', 'exception_types', 'all_words'. - Every element of every set originates from a substring of issue_text and is lowercased. - 'traceback_funcs': the set of function names appearing immediately after an " in " prefix at the end of a line, as found in Python traceback entries. - 'backtick_idents': the set of identifiers extracted from backtick-quoted spans and triple-backtick-fenced code blocks anywhere in issue_text. - 'dotted_refs': the set of method-name words from Class.method patterns, plus every underscore-delimited subpart of each such method name whose length exceeds 1 chara…
- FMA 推导 actual POST：Returns a dictionary `signals` with exactly seven keys: 'traceback_funcs', 'backtick_idents', 'dotted_refs', 'dotted_classes', 'plain_idents', 'exception_types', 'all_words'. Each value is a set of strings. The contents are defined as follows: 1. 'traceback_funcs': set of function names captured by the regex `\\bin (\\w+)\\s*\n` on the original `issue_text`. These strings are not lowercased. 2. 'backtick_idents': result of `_extract_backtick_idents(issue_text)`, a set of lowercased identifiers from backtick-quoted and triple-backtick-fenced code blocks. 3. 'dotted_refs': set of lowercased method names and their underscore-split parts (length > 1) from `Class.method` references where the class part starts with uppercase and the method part starts wit…

</details>

#### FMA-MISMATCH-204 — `src--scope-py--_parse_python_file`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/_parse_python_file.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/_parse_python_file.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--_parse_python_file.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--_parse_python_file.py)
- 触发/冲突：A Python file with only a class containing a method (no module-level functions) causes class methods to leak into funcs_info because ast.walk() traverses nested FunctionDef nodes inside ClassDef bodies.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- src_path is a Path to a Python source file that exists on disk and is readable.
- FMA SPEC post-condition：- If the source text is syntactically valid Python and can be parsed into an AST without raising an exception, returns a 3tuple (funcs_info, source_lines, classes) where: * funcs_info is a list of dicts, one per function defined at module scope. Each dict contains at minimum the following keys: - 'name' (str): the function name as written in the source - 'start' (int): 1based line number of the `def` or `async def` header - 'end' (int): 1based line number of the last line of the function body - 'calls' (collection of str): every name that is the direct target of a functioncall expression within the function body - 'idents' (collection of str): every identifier whose value is read within the function body - 'body_words' (collection of str): every dis…
- FMA 推导 actual POST：After execution, the function returns a tuple. If an exception was raised during the reading, parsing, or splitting of the file (i.e., any Exception caught in the try block), the return value is (None, None, None). Otherwise, the return value is a 3tuple (funcs, source_lines, classes) where: (1) funcs is a list of dicts, one for each toplevel ast.FunctionDef or ast.AsyncFunctionDef node walked in the tree, each dict containing keys 'name', 'start', 'end', 'calls' (result of _collect_calls on that node), 'idents', 'body_words', 'exc_types' (results of _collect_func_idents on that node), 'docstring' (the function's docstring or ''); (2) source_lines is a list of strings, the lines obtained by splitting the file content; and (3) classes is the result o…

</details>

#### FMA-MISMATCH-205 — `src--scope-py--_rank_functions`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/_rank_functions.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/_rank_functions.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--_rank_functions.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--_rank_functions.py)
- 触发/冲突：CALLEE_INHERIT (0.30) and CALLER_INHERIT (0.20) are unequal, violating the spec's requirement of a single fixed fraction for both callee and caller call-graph propagation.
- 成因复核：CALLER_INHERIT 与 CALLEE_INHERIT 是两个显式独立的排序权重；SPEC 无依据要求二者相等。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- funcs_info is a non-empty list of dicts. Each dict contains at minimum: 'name' (str, function name), 'start' (int, 1-based start line), 'end' (int, 1-based end line), 'idents' (collection of str, identifiers used within the function body), 'body_words' (collection of str, distinct words from the function body), 'exc_types' (collection of str, exception type names referenced in the body), and 'calls' (collection of…
- FMA SPEC post-condition：- Returns a list of dicts with the same cardinality as funcs_info, containing exactly one entry per element of funcs_info. Each entry contains at minimum 'name' (str), 'start' (int, 1-based), 'end' (int, 1-based), and 'score' (float, non-negative). - The list is sorted in descending order by 'score'. - Every 'start' value in the result matches exactly one 'start' from funcs_info; no entries are added, removed, or duplicated. - Each function's score is the sum of: (a) a base relevance score proportional to weighted matches between the function's name and body tokens against the signal token sets, normalized by the function's line count; (b) a call-graph propagation bonus: for every function whose base relevance score is positive, a fixed fraction of…
- FMA 推导 actual POST：The function returns a list `result` such that: - `result` contains exactly the same dictionary objects as the input list `funcs_info`, in descending order of their `'score'` values (i.e., sorted using the key `lambda x: -x['score']` with stable sorting). - Every dictionary `f` in `funcs_info` has been mutated in place to contain a key `'score'` whose value is the final computed score, a nonnegative float. - The final score for a function `f` is defined as: final_score(f) = base(f) + B(f) + C(f) where: * base(f) = _base_score(f['name'], f['idents'], f['body_words'], f['exc_types'], f['end'] - f['start'] + 1, signals). * B(f) is the callgraph propagation bonus summed over all direct callee and caller relations: - For every function `g` in `funcs_info…

</details>

#### FMA-MISMATCH-206 — `src--scope-py--_score_class`

- 结论：**契约待确认**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/_score_class.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/_score_class.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--_score_class.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--_score_class.py)
- 触发/冲突：ASCII-only regex r'\b([a-zA-Z]{4,})\b' fails to match non-ASCII alphabetic docstring tokens like 'naïve', so they contribute 0 even when present in all_words.
- 成因复核：实现与生成 SPEC 确有差异，但仓库现有文档/调用方不足以决定哪一侧代表产品意图。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- cls is a dict containing at minimum a 'name' key whose value is a non‑empty string (the class name) and a 'docstring' key whose value is a string (which may be empty). - signals is a dict with the fixed set of category keys extracted from developer‑ intent text; each key maps to a set[str] of tokens. At minimum the following keys are read: 'backtick_idents', 'plain_idents', 'dotted_classes', 'all_words'.
- FMA SPEC post-condition：- Returns a nonnegative float representing the heuristic relevance of the class to the developer intent. - The return value is zero when no namepart of the class matches any token in 'backtick_idents', 'plain_idents', 'dotted_classes', or 'all_words', and no alphabetic token of at least 4 characters from the class docstring (excluding stop words) matches any token in 'all_words'. - Each matching namepart adds an additive weight determined by the signal category it matches: tokens matching 'backtick_idents' are weighted higher than tokens matching 'dotted_classes', which in turn are weighted higher than tokens matching 'plain_idents' or 'all_words'. - Each matching docstring token (alphabetic, at least 4 characters, not a stop word) that intersects '…
- FMA 推导 actual POST：The function returns a nonnegative float score computed as the sum of five weighted term contributions from class name and docstring matches against developerintent signals. Let name_parts = _name_parts(cls['name']). Then the returned value equals: score = len(name_parts signals['backtick_idents']) * W_BACKTICK_NAME + len(name_parts signals['plain_idents']) * W_CLASS_NAME_MATCH + len(name_parts signals['all_words']) * W_CLASS_NAME_MATCH + len(name_parts signals['dotted_classes']) * W_DOTTED_REF + ( 0 if cls['docstring'] == '' else len( { w for w in re.findall(r'\b([a-zA-Z]{4,})\b', cls['docstring'].lower()) if w not in _STOP } signals['all_words'] ) * W_CLASS_DOC_MATCH ). No side effects occur. The constants W_BACKTICK_NAME, W_CLASS_NAME_MATCH, W_DO…

</details>

#### FMA-MISMATCH-252 — `src--scope-py--_parse_file`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/_parse_file.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/_parse_file.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--_parse_file.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--_parse_file.py)
- 触发/冲突：Non-existent .py file passed to _parse_file; FileNotFoundError is caught by _parse_python_file's except Exception handler, returning None and falling through to _parse_generic_file, not propagating.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- src_path is a Path to a source file that exists on disk. - proj_dir, if provided, is a string path to a project root directory; it is used when the parser requires project‑level indexing.
- FMA SPEC post-condition：- If the file extension is registered as a supported language, returns a tuple (funcs_info, source_lines, classes) where: * funcs_info is a list of dicts, each describing a toplevel function defined in the file, with at minimum 'name' (str), 'start' (int, 1based start line), and 'end' (int, 1based end line) keys. * source_lines is a list[str] containing the source text of the file, one element per line, preserving the original line order. * classes is a list of dicts, each describing a class defined in the file. - If the file extension is not registered as a supported language, or if languagespecific parsing fails for every available parser for that language, returns (None, None, None). - For Python files, parsing is attempted via AST first; if the…
- FMA 推导 actual POST：After execution, the function has returned. If the file extension is not recognized (i.e., not in EXT_TO_LANG), the returned value is (None, None, None) and a warning has been logged. If the extension is 'python' and the Python AST parser succeeds, the returned value is a tuple (funcs_info, source_lines, classes) from _parse_python_file, where each element is nonNone (funcs_info: list of dicts with keys 'name','start','end'; source_lines: list of strings; classes: list of dicts). If the extension is 'python' but the AST parser fails, the returned value equals the result of _parse_generic_file(src_path, 'python', proj_dir), which is either a tuple of three nonNone lists (if parsing succeeds) or (None, None, None). For any other recognized extension,…

</details>

#### FMA-MISMATCH-253 — `src--scope-py--rank_functions_in_file`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/scope-py/rank_functions_in_file.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/scope-py/rank_functions_in_file.json) · [具体 bug 报告](../fm_agent/bug_validation/src--scope-py--rank_functions_in_file.md) · [probe](../fm_agent/bug_validation/probe_src--scope-py--rank_functions_in_file.py)
- 触发/冲突：The function does have `return result` at line 172/798; it correctly returns a list of dicts, not None. Bug claim is false.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- src_path is a Path to an existing source file. - filepath is a human-readable label identifying the file. - issue is a string describing developer intent. - signals is a dict[str, set[str]] with the same keys produced by _parse_issue_signals: 'traceback_funcs', 'backtick_idents', 'dotted_refs', 'dotted_classes', 'plain_idents', 'exception_types', 'all_words'. - top_k is a positive integer. - llm_trigger, llm_top_k…
- FMA SPEC post-condition：- If the file contains zero parseable functions, returns an empty list. - Otherwise, returns a list of dicts sorted in descending order by 'score'. - Each returned dict contains the keys: 'file' (str, equal to filepath), 'name' (str), 'lineno' (int, 1based start line), 'end_lineno' (int, 1based end line), 'score' (float, rounded to 3 decimal places), and 'reason' (str, one of "heuristic", "llm", "heuristic_pad"). - The returned list length is at most top_k. - Every 'name' in the result is unique; if a name appeared in multiple positions within the file, only the occurrence with the highest score is kept. - Every 'name' in the result corresponds to a function actually defined in the source file. - Scores reflect relevance to the issue as judged again…
- FMA 推导 actual POST：If _parse_file returns funcs_info that is None or empty, the function prints the message and returns the empty list []. Otherwise, funcs_info is non-empty, _rank_functions computes a scored list, deduplication by name produces deduped_ranked, and the function prints a formatted table header; after printing it reaches the end of the block and returns None (implicit return). The arguments filepath, src_path, issue, signals, top_k, llm_client, llm_model, llm_trigger, llm_top_k, llm_confidence_threshold, proj_dir are unchanged. No exceptions are raised under the given pre-conditions. Stdout receives the relevant output lines.

</details>

### `src--trace_writer-py`

#### FMA-MISMATCH-207 — `src--trace_writer-py--append_event`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/trace_writer-py/append_event.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/trace_writer-py/append_event.json) · [具体 bug 报告](../fm_agent/bug_validation/src--trace_writer-py--append_event.md) · [probe](../fm_agent/bug_validation/probe_src--trace_writer-py--append_event.py)
- 触发/冲突：When events.jsonl contains content that does not end with a newline, append_event concatenates the new event to the last incomplete line instead of writing it on a new line.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- trace_dir is a string specifying a writable filesystem path - event is a dict whose top-level values are JSON-serializable
- FMA SPEC post-condition：- The directory trace_dir exists, with any missing parent directories created - The file events.jsonl inside trace_dir has one additional line appended - That line is the JSON serialization of event with non-ASCII characters preserved in their original form (Unicode, not \u-escaped) - The write is safe under concurrency: each event occupies exactly one complete line and bytes from different events are never interleaved within the same line - Returns None
- FMA 推导 actual POST：After execution, the lock _LOCK is released. If the block completes without raising an exception, then: (1) the directory trace_dir exists (and all missing parent directories exist); (2) the file events_path = os.path.join(trace_dir, 'events.jsonl') exists and its content is the previous content (if any) appended with the line json.dumps(event, ensure_ascii=False) + '\n'; (3) the function returns None. If an exception is raised, the directory may or may not exist depending on whether _ensure_trace_dirs succeeded, the file may be untouched, created but empty, or contain a partial write; the lock is released in all cases. Formally, let S be the initial state and S' the final state, let exists(p) denote path p exists, content(p) the file contents, and…

</details>

#### FMA-MISMATCH-208 — `src--trace_writer-py--new_event_id`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/trace_writer-py/new_event_id.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/trace_writer-py/new_event_id.json) · [具体 bug 报告](../fm_agent/bug_validation/src--trace_writer-py--new_event_id.md) · [probe](../fm_agent/bug_validation/probe_src--trace_writer-py--new_event_id.py)
- 触发/冲突：Monkey-patching uuid.uuid4() to a deterministic value causes new_event_id() to return duplicate IDs, confirming no collision-prevention mechanism exists beyond probabilistic UUID4 randomness.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- prefix is a non-empty string
- FMA SPEC post-condition：- Returns a string composed of prefix, a single underscore, and a 32-character lowercase hexadecimal string - The returned identifier is globally unique: it differs from every identifier previously returned by any invocation of new_event_id
- FMA 推导 actual POST：The function returns a string formed by concatenating the prefix (the provided non-empty string argument or the default 'evt'), an underscore, and the 32-character hexadecimal digest of a randomly generated UUID4. Formally, if s is the return value, p is the prefix (p ''), then s = p + '_' + h where h = uuid.uuid4().hex and h is a string of 32 lowercase hexadecimal digits ([0-9a-f]{32}).

</details>

#### FMA-MISMATCH-209 — `src--trace_writer-py--record_llm_exchange`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/trace_writer-py/record_llm_exchange.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/trace_writer-py/record_llm_exchange.json) · [具体 bug 报告](../fm_agent/bug_validation/src--trace_writer-py--record_llm_exchange.md) · [probe](../fm_agent/bug_validation/probe_src--trace_writer-py--record_llm_exchange.py)
- 触发/冲突：When event dict lacks a 'metadata' key, setdefault() on line 51 unconditionally adds one, modifying event beyond what the spec permits.
- 成因复核：该函数职责就是给 event 增补 metadata/children 后写 trace；SPEC 禁止增加 metadata，直接否定了函数的主要用途。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- trace_dir is either a writable directory path or a falsy value (None or empty string). - event_id is a non-empty string that uniquely identifies the exchange. - event is a mutable dict. - messages is a list of dicts, each having at least "role" (string) and "content" (string) keys. - response is a string, None, or omitted.
- FMA SPEC post-condition：- When trace_dir is falsy, returns immediately with no side effects. - When trace_dir is a writable directory: - The content of each message in messages is durably stored as a separate file. Each stored message is classified by role: messages with role "system" are classified as system_prompt, role "user" as user_prompt, role "assistant" as assistant_output, and any other role as message. - If response is not None, its string value is durably stored as an additional file classified as assistant_output. - All stored files are recorded as child entries in the event dict. Each child entry contains a type field matching the classification, and a reference to the stored file content. Message-derived child entries additionally include the message's role.…
- FMA 推导 actual POST：If `trace_dir` is falsy (None or empty string), the function returns immediately; the mutable dict `event` and list `messages` are unchanged, and no side effects occur (no files created, no log appended). If `trace_dir` is a writable directory path, then: The `event` dict is modified as follows: a key `'metadata'` is set to a new dict obtained from the original `event.get('metadata', {})` (or an empty dict if absent) with the key `'parsed'` removed (if present); a key `'children'` is set to a list `children` constructed by iterating over `messages` with index `i` and mapping each message to a dict `{'type': item_type, 'role': role, 'content_ref': ref}` where `role = message.get('role', 'message')`, `item_type` is determined by `role` ('system''syste…

</details>

#### FMA-MISMATCH-210 — `src--trace_writer-py--utc_now_iso`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/trace_writer-py/utc_now_iso.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/trace_writer-py/utc_now_iso.json) · [具体 bug 报告](../fm_agent/bug_validation/src--trace_writer-py--utc_now_iso.md) · [probe](../fm_agent/bug_validation/probe_src--trace_writer-py--utc_now_iso.py)
- 触发/冲突：datetime.isoformat() omits fractional seconds when microseconds are zero, so utc_now_iso() fails to include microsecond precision when the clock lands on an exact second boundary.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- none
- FMA SPEC post-condition：- Returns the current UTC date and time formatted as an ISO 8601 string ending with "Z" as the UTC timezone designator - The returned string includes microsecond precision
- FMA 推导 actual POST：The function returns a string that is the ISO 8601 formatted representation of the current UTC date and time, with the UTC offset suffix '+00:00' replaced by 'Z'. Formally, let t be the instant the function is called, let dt = datetime.now(timezone.utc) at t, then the returned value is dt.isoformat().replace('+00:00', 'Z'). No exceptions are raised, and no side effects occur.

</details>

#### FMA-MISMATCH-211 — `src--trace_writer-py--write_payload`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/trace_writer-py/write_payload.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/trace_writer-py/write_payload.json) · [具体 bug 报告](../fm_agent/bug_validation/src--trace_writer-py--write_payload.md) · [probe](../fm_agent/bug_validation/probe_src--trace_writer-py--write_payload.py)
- 触发/冲突：When trace_dir is '.', os.path.dirname('.') returns '' instead of '..', so the returned path is relative to trace_dir itself instead of one level above it.
- 成因复核：差异可以复现，但被违反的要求是生成 SPEC 新增或过度强化的约束，probe 仅把该 SPEC 当作 oracle。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- trace_dir is a string path to a writable directory. - event_id is a non-empty string uniquely identifying the owning event. - name is a non-empty string used as a filename component. - content is a string value (or a bytes value when binary is truthy). - binary is a truthy/falsy value.
- FMA SPEC post-condition：- The content is atomically written to a file named "{event_id}_{name}" under the payloads subdirectory of trace_dir. The write is atomic: the file either appears at the final path in its entirety or not at all; no partial content is visible at that path. - When binary is falsy, content is written as UTF-8-encoded text. - When binary is truthy, content is written as raw bytes. - Returns a relative path string that identifies the written file for later retrieval. The path is relative to the directory one level above trace_dir and uses the operating-system path separator. - The necessary parent directories for the file are created under trace_dir as a side effect.
- FMA 推导 actual POST：If the function raises an exception (e.g., OSError, IOError), no guarantees are made about the existence or content of the target file. If the function returns normally, the returned value `r` satisfies: `r = os.path.relpath(p, os.path.dirname(trace_dir))` where `p = os.path.join(payload_dir, event_id + '_' + name)` and `payload_dir = _ensure_trace_dirs(trace_dir)`. The file at `p` exists, is a regular file, and its content exactly matches the input `content`. If `binary` is truthy, the file contains the raw bytes of `content`; otherwise, the file contains the string `content` encoded in UTF-8. The write is atomic: the file at `p` is either the newly written content or its prior content (if any) remains unmodified. The temporary file used during the…

</details>

### `src--verification-py`

#### FMA-MISMATCH-212 — `src--verification-py--_generate_validation_summary`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/verification-py/_generate_validation_summary.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/verification-py/_generate_validation_summary.json) · [具体 bug 报告](../fm_agent/bug_validation/src--verification-py--_generate_validation_summary.md) · [probe](../fm_agent/bug_validation/probe_src--verification-py--_generate_validation_summary.py)
- 触发/冲突：Sort key uses b.get('id', '') without converting id to string; mixed int/str ids in same status group cause TypeError during sort.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string path to a directory
- FMA SPEC post-condition：- If proj_dir/bug_validation/ does not exist or is not a directory, the function returns with no file written - Otherwise, every entry in proj_dir/bug_validation/ whose name ends with ".result.json" and whose contents are valid JSON is included in the summary; entries that cannot be read or parsed produce a warning and are excluded from the summary - Writes proj_dir/bug_validation/summary.json via an atomic rename (temp file then os.replace) containing: - total_reported: the number of successfully parsed .result.json records - total_confirmed: count where confirmation_status == "confirmed" - total_not_confirmed: count where confirmation_status == "not_confirmed" - total_error: count where confirmation_status == "error" - bugs: array of all parsed re…
- FMA 推导 actual POST：After execution, one of the following holds: 1. If `os.path.isdir(validation_dir)` returned `False`, the function returns `None` and no files are created or modified. 2. If `os.path.isdir(validation_dir)` returned `True` but `os.listdir(validation_dir)` raises an exception (e.g., `OSError`), that exception propagates and no output file is written. 3. If `os.listdir(validation_dir)` succeeds, then for every entry in the sorted directory listing with name ending in `.result.json`, the function attempts to read and parse it with `json.load`. If that succeeds, the resulting object is appended to a list `bugs`; if it raises `OSError` or `json.JSONDecodeError`, the entry is skipped and a warning is logged. Then counts are computed as: - `confirmed` = numb…

</details>

#### FMA-MISMATCH-213 — `src--verification-py--_spec_task_exit_code`

- 结论：**推理误判**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/verification-py/_spec_task_exit_code.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/verification-py/_spec_task_exit_code.json) · [具体 bug 报告](../fm_agent/bug_validation/src--verification-py--_spec_task_exit_code.md) · [probe](../fm_agent/bug_validation/probe_src--verification-py--_spec_task_exit_code.py)
- 触发/冲突：except Exception on line 59 catches only Exception subclasses; BaseException subclasses like KeyboardInterrupt/SystemExit propagate uncaught instead of returning 1 as the spec requires.
- 成因复核：probe 使用了前置条件、schema、可信全局状态或 callee 合约之外的反例，不能推出实现违约。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- handle is an object whose completion has been confirmed (_spec_task_done(handle) returned True)
- FMA SPEC post-condition：- Returns an integer status code derived from the completed handle's outcome, or None when the handle type exposes no status-reporting mechanism - When the handle carries a direct exit-code attribute: returns its value (an integer or None) unchanged - When the handle resolves to a value: returns that value if it is an integer; returns 0 if the resolved value is of any non-integer type - When handle resolution raises any exception: returns 1
- FMA 推导 actual POST：Given the pre-condition that `handle` refers to a completed task (i.e., `_spec_task_done(handle) == True`), after `_spec_task_exit_code(handle)` finishes execution, it returns an integer exit code or `None` as follows: - If `hasattr(handle, 'returncode')` evaluates to `True`, the return value is `handle.returncode`. - Otherwise, if `hasattr(handle, 'done')` and `handle.done()` both evaluate to `True`: - The function attempts to evaluate `handle.result()`. If that call completes without raising an exception, then: - if `isinstance(result, int)` is `True`, the return value is `result`; - otherwise, the return value is `0`. - If `handle.result()` raises an exception (any `Exception`), the return value is `1`. - Otherwise (neither a `returncode` attribu…

</details>

#### FMA-MISMATCH-214 — `src--verification-py--_validate_single_bug`

- 结论：**实现缺陷候选**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/verification-py/_validate_single_bug.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/verification-py/_validate_single_bug.json) · [具体 bug 报告](../fm_agent/bug_validation/src--verification-py--_validate_single_bug.md) · [probe](../fm_agent/bug_validation/probe_src--verification-py--_validate_single_bug.py)
- 触发/冲突：When resume=True and a valid result.json already exists, the function returns at line 400 before the try/finally cleanup block, leaving the generated prompt file on disk in violation of the spec.
- 成因复核：反例处于声明输入域内，并会影响真实管线、跨平台行为、解析完整性或资源/安全边界。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- result_json_rel is a non-empty string: the path (relative to proj_dir) of a logic_verification_results/…json file whose verdict is "MISMATCH" - proj_dir is an existing directory containing a readable md/bug_validator.md and a writable fm_agent/ subtree - work_dir is either None (defaults to proj_dir) or an existing directory whose fm_agent/bug_validation/ tree is writable - resume is a boolean; when True, a previo…
- FMA SPEC post-condition：- Derives bug_id from result_json_rel deterministically: strips the prefix "fm_agent/logic_verification_results/" (accepting both OS-dependent and "/" separators), removes the file extension, then replaces every path separator ("/" or os.sep) with "--" - Reads md/bug_validator.md and assembles a per-bug prompt consisting of a header identifying the target result file and the derived bug_id, followed by an optional user-provided domain-knowledge section (when staged knowledge files exist under work_dir), followed by the bug_validator base content unmodified - Atomically writes the assembled prompt to fm_agent/bug_validation/bug_validator_{bug_id}.md under proj_dir (writes to a ".tmp" sibling then os.replace, so no reader observes a partial file) - Wh…
- FMA 推导 actual POST：After the code block executes, the following post-condition holds. Let prompt_filename = os.path.join("fm_agent", "bug_validation", f"bug_validator_{bug_id}.md"), prompt_path = os.path.join(proj_dir, prompt_filename), result_relpath = os.path.join("fm_agent", "bug_validation", f"{bug_id}.result.json"), result_path = os.path.join(proj_dir, result_relpath), output_md_path = os.path.join(proj_dir, "fm_agent", "bug_validation", f"{bug_id}.md"), tmp_path = prompt_path + ".tmp". (Invariance) result_json_rel is unchanged; base_md_path unchanged; all staged domain knowledge files listed in user_knowledge_paths are unchanged; tmp_path does not exist in the filesystem. (Early return before outer try) If resume is true, result_path existed and contained valid…

</details>

#### FMA-MISMATCH-215 — `src--verification-py--streaming_reasoner`

- 结论：**SPEC 错误**；内置 validator：`confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/verification-py/streaming_reasoner.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/verification-py/streaming_reasoner.json) · [具体 bug 报告](../fm_agent/bug_validation/src--verification-py--streaming_reasoner.md) · [probe](../fm_agent/bug_validation/probe_src--verification-py--streaming_reasoner.py)
- 触发/冲突：streaming_reasoner delays early-exit when spec_procs complete and files are unready by requiring reasoning_futures and validation_futures to also be empty (line 209), violating spec B.6 which requires immediate exit with a warning.
- 成因复核：等待 reasoning/validation futures 清空可避免遗弃已提交任务；SPEC 要求 spec 进程结束就立即退出，会产生不完整结果。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- input_dir is a directory path containing extracted function files, where each file is expected to eventually have [SPEC]/[INFO] blocks prepended - output_dir is a writable directory path to store verification result JSON files - file_list, if provided, is a collection of relative file paths; each path ends with an extension in EXT_TO_LANG - proj_dir, if provided, is the project root directory path - work_dir defau…
- FMA SPEC post-condition：- Every file in input_dir (scoped to file_list when provided) whose is_file_ready() returns True will be submitted to _verify_single_file exactly once; a readied file that was in already_processed is NOT resubmitted - A verification result JSON is written to output_dir for every submitted file, mirroring the relative path structure of input_dir; the verdict field in each result is one of: "MATCH", "MISMATCH", "ERROR", "SKIPPED" - For every verified file whose verdict is "MISMATCH" and proj_dir is not None, a bug-validation task is submitted via _validate_single_bug; the validation writes a result JSON at proj_dir/bug_validation/<bug_id>.result.json where bug_id is derived from the result JSON path by stripping the fm_agent/logic_verification_results…
- FMA 推导 actual POST：Let state S be the program state after the precondition, with variables as defined there. Define break_condition = (expected_files is not None processed expected_files reasoning_futures = validation_futures = ) (spec_procs is not None ( p spec_procs : _spec_task_done(p)) ((expected_files or set()) \ processed) reasoning_futures = validation_futures = ). After execution of the code block (lines 121171) starting from S, if break_condition holds then: the loop is exited, the function returns processed; reasoning_futures and validation_futures are empty; if proj_dir None then _generate_validation_summary(work_dir) has been called (side effect); all other variables remain unchanged. If break_condition does not hold then: time.sleep(poll_interval) execute…

</details>

### `src--languages--javascript-py`

#### FMA-MISMATCH-245 — `src--languages--javascript-py--batch_extract`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/javascript-py/batch_extract.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/javascript-py/batch_extract.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--javascript-py--batch_extract.md) · [probe](../fm_agent/bug_validation/probe_src--languages--javascript-py--batch_extract.py)
- 触发/冲突：The spec claims .mjs files should be included but codegraph v1.4.1 assigns .mjs files the 'javascript' language tag, so they are already included.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string path to a valid project root directory containing JavaScript source files (.js, .jsx).
- FMA SPEC post-condition：- If the codegraph backend is available, returns a dictionary mapping each absolute file path (string) to a list of (func_name, func_body) tuples, where func_name is a string and func_body is the source text of the function, for every JavaScript function definition found across all project files. - If the codegraph backend is unavailable, returns an empty dictionary. - Each key in the returned dictionary is an absolute filesystem path; each value is a non-empty list of tuples.
- FMA 推导 actual POST：If a CodeGraphExtractor instance cg is successfully created from proj_dir (i.e., cg is not None), the function returns the result of cg.get_functions_by_file("javascript", proj_dir), which is a dictionary mapping each absolute file path (string) of a JavaScript (.js/.jsx) file within proj_dir that contains any function definition to a list of (func_name: str, func_body: str) tuples for all function definitions found in that file. If cg is None (backend initialization fails), the function returns an empty dictionary {}. The returned dictionary maps exactly the JavaScript files that have function definitions; files with no functions are omitted. No other program state is modified.

</details>

#### FMA-MISMATCH-246 — `src--languages--javascript-py--function_spans`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/javascript-py/function_spans.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/javascript-py/function_spans.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--javascript-py--function_spans.md) · [probe](../fm_agent/bug_validation/probe_src--languages--javascript-py--function_spans.py)
- 触发/冲突：function_spans delegates to get_function_spans without explicit sorting, but the backend SQL already uses ORDER BY start_line (INTEGER column), guaranteeing numeric ordering.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a path to an existing project directory. - filepath is a path to a JavaScript source file within the project.
- FMA SPEC post-condition：- Returns None when the codegraph backend is unavailable for the project, or when the backend exists but does not index the given file. - Otherwise returns a list of (name, start_idx, end_idx) tuples, one per function defined in the file. - start_idx and end_idx are 0-indexed inclusive line numbers. - The list is ordered by appearance (ascending start_idx). - The list is empty when no functions are defined in the file.
- FMA 推导 actual POST：Returns a list of tuples (name: str, start_idx: int, end_idx: int) for each function found in the JavaScript source file, where start_idx and end_idx are 0-indexed inclusive line numbers; or None if the codegraph backend is unavailable (CodeGraphExtractor.from_proj_dir returns None) or the backend does not index the given file. No side effects. Formally: let r be the return value. r = None if CodeGraphExtractor.from_proj_dir(proj_dir) is None; otherwise, r = cg.get_function_spans('javascript', filepath) where cg is the returned codegraph instance, so r is either None or a list of tuples (name, s, e) with s e, non-negative integers.

</details>

### `src--languages--python-py`

#### FMA-MISMATCH-247 — `src--languages--python-py--call_edges`

- 结论：**推理误判**；内置 validator：`not_confirmed`。
- 证据：[`[SPEC]` 原文](../fm_agent/extracted_functions/src/languages/python-py/call_edges.py) · [推导 POST / result](../fm_agent/logic_verification_results/src/languages/python-py/call_edges.json) · [具体 bug 报告](../fm_agent/bug_validation/src--languages--python-py--call_edges.md) · [probe](../fm_agent/bug_validation/probe_src--languages--python-py--call_edges.py)
- 触发/冲突：call_edges returns None when cg is truthy but cg.get_call_edges('python') is None — unreachable because get_call_edges always returns a dict for Python.
- 成因复核：validator 的复现阶段已否定该 claim；原始 MISMATCH 是代码/语义读取错误。

<details><summary>SPEC / POST 摘录</summary>

- Pre-condition：- proj_dir is a string path to a project root directory.
- FMA SPEC post-condition：- Returns a dict when the CodeGraph backend can index the project directory; returns None when the backend is unavailable or the project cannot be indexed. - When a dict is returned, each key identifies a caller function (as a tuple of stem and module identifiers) and each value is a set of callee function identifiers (stems) called by that caller. - The returned call edges cover Python source files (.py) under the project directory. - A callee appears in the returned set only when the CodeGraph backend resolves a call site within the caller's body to that callee.
- FMA 推导 actual POST：If the CodeGraphExtractor backend is available and the project can be indexed, the function returns a dictionary mapping each (caller_stem, caller_module) tuple to a set of callee_stem strings for Python; otherwise, it returns None. Formally: let cg = CodeGraphExtractor.from_proj_dir(proj_dir). If cg is falsy, the result is None. If cg is truthy, let edges = cg.get_call_edges('python'). If edges is None, the result is None; else the result is a Dict[Tuple[str, str], Set[str]] containing the call graph edges.

</details>

## 历史完整性问题与 restore 结果

### 原已 ready 但无 result 的 10 个函数（当前已补齐）

| 函数 | 补跑 verdict / validator | 静态复核 | 清单编号 |
|---|---|---|---|
| `_reapply_existing_specs` | MISMATCH / confirmed | 实现缺陷候选 | `FMA-MISMATCH-260` |
| `_llm_check_spec_update` | MISMATCH / not_confirmed | 推理误判 | `FMA-MISMATCH-257` |
| `_plan_spec_update` | MISMATCH / confirmed | 实现缺陷候选 | `FMA-MISMATCH-259` |
| `_verify_incremental_functions` | MISMATCH / confirmed | SPEC 错误 | `FMA-MISMATCH-263` |
| `extract_existing_specs` | MISMATCH / confirmed | 推理误判 | `FMA-MISMATCH-264` |
| `run_incremental_pipeline` | MISMATCH / not_confirmed | 推理误判 | `FMA-MISMATCH-265` |
| `_opencode_generate_spec` | MISMATCH / confirmed | 实现缺陷候选 | `FMA-MISMATCH-258` |
| `_split_spec_and_info` | MISMATCH / confirmed | 推理误判 | `FMA-MISMATCH-261` |
| `_update_specs_for_intent` | MISMATCH / not_confirmed | 推理误判 | `FMA-MISMATCH-262` |
| `_llm_check_caller_info_update` | MISMATCH / confirmed | 实现缺陷候选 | `FMA-MISMATCH-256` |

这 10 项现在都已有逻辑 result、validator report/result 和 probe，因此不再是“skipped/无结果”完整性问题。其中 7 项 confirmed 不等于 7 个真实 bug：对前置条件、上游协议和嵌套函数边界复核后，只有 4 项列为实现缺陷候选。

### 恢复重跑前的 ERROR（当前已清零）

- `src/file_utils-py/_iter_project_source_files.json`：原为 LLM connection error；重跑后为 `MISMATCH`，validator `not_confirmed`，见 `FMA-MISMATCH-254`。
- `src/reasoner-py/_sanitize_strings.json`：原为 LLM connection error；重跑后为 `MATCH`。
- `src/reasoner-py/reasoner.json`：原为 LLM connection error；重跑后为 `MATCH`。

三项均已产生有效逻辑 verdict，当前 `ERROR = 0`。这次恢复只消除了连接故障，不能单独用来证明新 verdict 正确；其中 `_iter_project_source_files` 的新增 MISMATCH 已由 probe 否定。

## 复核边界

本报告没有把生成 SPEC 自动视为 ground truth，也没有在缺乏产品契约时擅自改源码。“实现缺陷候选”应逐项转成维护者认可的测试后再修；“契约待确认”应先决定行为；“SPEC 错误/推理误判”应进入验证器评测集，防止下一轮再次制造同类 mismatch。
