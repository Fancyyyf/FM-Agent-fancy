# FM-Agent 自审计 Issue 草稿

## 基线与使用说明

- 复核版本：`self_modify@570edee`，已包含 `upstream/main@b0b41fe`。
- 来源：`review_report.md` 中的 21 条人工复核记录。
- 本文只收录当前版本仍值得修复的问题；076 已判定为非真实 Bug，188 不是被指向函数的实现 Bug，均不单独提出实现 Issue。
- 238、107 只得到部分缓解，下面的 Issue 只要求补齐尚未解决的部分。
- 每个草稿都明确列出“覆盖 mismatch”；一个 Issue 合并多个 mismatch 时，应在 PR 和回归测试中同时引用这些 ID。

## Issue 路由总览

| 草稿 | 优先级 | 覆盖 mismatch | 合并理由 |
|---|---:|---|---|
| Issue 1：配置编辑与 URL 校验 | P2 | 014、030、031 | 都位于 `configure_llm.py`，共同影响配置向导接受和持久化用户配置的可靠性。 |
| Issue 2：增量 metadata 失败状态与数据完整性 | P0 | 238、239、225 | 同一条增量 sidecar 生成、校验、覆盖写入链；会静默漏验或丢失 callee 数据。 |
| Issue 3：增量 phase plan 必须覆盖当前源码 | P1 | 139 | 独立的阶段完整性问题，影响后续所有抽取和验证。 |
| Issue 4：运行状态不得把失败或陈旧数据显示为成功 | P2 | 038、177、252 | 都破坏运行状态的真实性，分别位于 preflight、trace 和 dashboard。 |
| Issue 5：fallback 解析器应处理真实多行与嵌套语法 | P1 | 071、073、301 | 都是语义后端不可用时的源码识别错误，会产生错误函数范围/FQN/调用边。 |
| Issue 6：Reasoner 分块应使用跨行词法状态 | P1 | 272；关联 188 | 272 是当前可复现实现 Bug；188 作为“完整函数仍可能被不完整分析”的回归动机，不声称由本 Issue 完全解决。 |
| Issue 7：Erlang 命令与后端失败语义 | P1 | 097、107 | 都位于 ELP 适配层；一个导致错误启动 argv，一个把调用图失败伪装为空图。 |
| Issue 8：注入目标的 hostname 比较应大小写无关 | P2 | 157 | 独立且修复面很小。 |
| Issue 9：损坏 JSON 应进入恢复路径 | P2 | 198 | 独立的恢复健壮性问题。 |
| 候选 Issue A：跨语言 CodeGraph 边 | 待确认 | 061 | 机制存在，但提交前还缺固定 CodeGraph 版本上的真实 FFI 证据。 |

---

## Issue 1

### Title

`fix(config): make TOML updates and base URL validation reject ambiguous or invalid input`

### Priority / Labels

`P2` · `bug` · `configuration` · `good first issue`

### 覆盖 mismatch

- FMA-MISMATCH-014：空 TOML 文件被误判为不存在。
- FMA-MISMATCH-030：合法 quoted key 未被编辑器识别，更新后形成重复键。
- FMA-MISMATCH-031：非法或越界端口未在 Base URL 校验阶段拒绝。

### Description

配置向导目前混淆“文件不存在”和“文件存在但为空”，文本 TOML 编辑器只识别裸键，并且 URL 校验没有实际解析 hostname/port。这会让合法空配置无法初始化，让合法 quoted key 更新成无效 TOML，也会把错误端口延迟到 HTTP 客户端阶段才暴露。

当前可复现行为：

```text
empty fm-agent.toml + apply_llm_settings_update -> ConfigWizardError
"name" = "old" + update name              -> TOMLDecodeError（重复语义键）
validate_base_url("http://example.com:abc") -> 正常返回
```

### Expected behavior

- 用文件存在性区分 missing 与 empty；空 TOML 应作为合法空文档处理。
- 能识别 TOML bare key、basic quoted key 和 literal quoted key，更新后只保留一个语义键。
- URL 必须是可解释的 HTTP(S) absolute URL；hostname 非空，显式端口必须是整数且在合法范围内。
- 所有用户可修复的输入错误统一转换为 `ConfigWizardError`，并给出具体字段信息。

### Suggested implementation

- `apply_llm_settings_update()` 使用 `toml_path.is_file()` 判断缺失，不使用内容 truthiness。
- 为保格式编辑器增加可靠的 TOML key token 解析；若继续使用正则，至少完整覆盖 TOML quoted-key 语法，并在写入前后都用 `tomllib.loads()` 校验。
- `validate_base_url()` 显式访问 `parsed.hostname` 和 `parsed.port`，捕获 `ValueError` 并转换为 `ConfigWizardError`。

### Acceptance criteria

- 空文件可以生成有效的 `[llm]` 配置。
- 更新 `"name"`、`'name'` 和 `name` 均不会产生重复键，原注释和无关字段保留。
- 非数字端口、负端口、超过 65535 的端口、缺失 hostname 均被拒绝。
- 合法 IPv4、IPv6、带认证信息和无显式端口的 HTTP(S) URL 仍可通过。

---

## Issue 2

### Title

`fix(incremental): make metadata generation failures explicit and preserve unrelated callee entries`

### Priority / Labels

`P0` · `bug` · `incremental` · `data-integrity` · `reliability`

### 覆盖 mismatch

- FMA-MISMATCH-238：LLM 失败和正常跳过共用 `None`，新函数可能静默漏验。
- FMA-MISMATCH-239：不完整 `new_info` 直接覆盖整个 sidecar。
- FMA-MISMATCH-225：校验边界没有保护非目标 callee 条目。

### Description

这三项属于同一条 metadata 更新链。`_plan_spec_update()` 无法区分 unchanged、unsupported 与 generation failure；`_validate_caller_info_update()` 只验证 JSON schema；`_reconcile_caller()` 随后把模型返回对象作为完整文件覆盖。结果可能是：新增函数没有 sidecar 却被当成正常完成，或者一次局部 callee 协调永久删除其他 callee 的契约。

最新本地修改已经在 sidecar 写入后调用 `is_file_ready()` 并在失败时恢复旧文件，这是必要保护，但仍未覆盖以下路径：

- LLM 没有返回可用结果，plan 在写入前就变成 `None`；
- 新函数返回 `spec_updated=false`；
- caller 返回 schema 合法但集合不完整的 `new_info`；
- caller sidecar 直接覆盖过程中断，或者模型修改了非目标条目。

### Expected behavior

- 计划阶段返回结构化 outcome：至少区分 `updated`、`unchanged`、`unsupported`、`missing_source` 和 `generation_failed`。
- 对没有 ready sidecar 的新增/修改函数，`generation_failed` 必须让增量运行失败或明确结束为 incomplete，不能报告完整成功。
- caller reconciliation 只能确定性地修改目标 callee；其他条目由程序保留，而不是依赖提示词。
- 所有 sidecar 使用临时文件、完整性校验和原子替换；失败时保留上一份可用文件。

### Suggested implementation

- 引入带 status/error/fqn 的 dataclass 或 TypedDict，替换无语义的 `None`。
- 对 changed targets 在 spec 阶段结束后执行 readiness 审计，并把缺失函数写入运行摘要、CLI 和 Dashboard。
- 让模型只返回目标 callee entry，代码按稳定 identity 合并；或者对完整返回值比较旧集合，拒绝非目标条目减少或改变。
- 复用现有写后 readiness 回滚，同时把写入改为同目录临时文件 + `os.replace()`。

### Acceptance criteria

- 新函数的 LLM 超时、空响应、非法 JSON、`spec_updated=false` 都产生可观察的 incomplete/error，且不会进入成功摘要。
- 原 `.info.json` 含 A/B，本轮只更新 A 时，即使模型只返回 A，最终 B 仍逐字段保持不变。
- 模型尝试修改非目标 B 时更新被拒绝或 B 被代码恢复。
- 写入中断不会留下半写 JSON，也不会删除上一份 ready sidecar。
- 保留现有 `is_file_ready()` 写后检查及其回滚覆盖。

---

## Issue 3

### Title

`fix(pipeline): require incremental phases.json to cover all current in-scope sources`

### Priority / Labels

`P1` · `bug` · `incremental` · `pipeline-completeness`

### 覆盖 mismatch

- FMA-MISMATCH-139。

### Description

`_run_generate_phases()` 当前用以下条件接受非 submodule 的增量计划：

```python
mtime_changed or _phases_cover_current_sources(...)
```

只要 Agent 重写了文件，即使新计划漏掉当前源码，也会停止重试。遗漏文件随后不会被抽取、生成规约或验证，因此这是结果完整性问题，而不是单纯的计划质量问题。

### Expected behavior

更新动作和内容完整性必须分开判断。增量计划被接受时必须满足 schema 合法且覆盖所有当前 in-scope source；如果产品还要求“本轮确实更新”，则额外要求 mtime/content hash 变化。

### Acceptance criteria

- 项目有 `main.py/a.py/b.py` 而计划只列 `main.py` 时，即使 mtime 已变化也不能通过。
- 新增、删除、重命名文件及 submodule scope 都有回归测试。
- 最终失败消息列出缺失和越界的 source path，而不是只报告“未更新”。
- resume 只能复用同时满足 schema 与覆盖率的计划。

---

## Issue 4

### Title

`fix(observability): never report failed checks or stale dashboard state as success`

### Priority / Labels

`P2` · `bug` · `observability` · `dashboard` · `preflight`

### 覆盖 mismatch

- FMA-MISMATCH-038：preflight 忽略子进程非零退出。
- FMA-MISMATCH-177：OpenCode 启动意外异常仍记录 success/0/null。
- FMA-MISMATCH-252：Bug 目录消失后 pending 使用旧值。

### Description

环境检查、trace 和 Dashboard 都存在“当前状态与展示状态不一致”的路径。工具不可用可能被报告为可用；执行异常可能留下成功 trace；结果目录已删除后 Dashboard 仍显示旧 pending 数。三者共同破坏用户对运行状态的信任。

### Expected behavior

- preflight 只有在命令退出码为 0 时才通过，并保留 stderr 摘要。
- `run_opencode_traced()` 的 success 条件必须是 `exit_code == 0 and error is None`；所有向外传播的异常都先记录失败状态再重新抛出。
- `scan_bugs()` 每次扫描开始时重置 confirmed、not-confirmed 和 pending；目录不存在时三者都为 0。

### Acceptance criteria

- mock `returncode=1` 时 `_check_oh_my_openagent()` 返回失败。
- `_start_opencode_process`、等待线程或日志线程抛异常时 trace 为 error、非零/空退出码，并包含错误文本。
- Bug 目录从存在变为不存在后 pending 归零。
- 正常成功路径的现有 trace 字段和 Dashboard 计数不回归。

---

## Issue 5

### Title

`fix(fallback-parser): preserve function identity and calls across multiline and nested syntax`

### Priority / Labels

`P1` · `bug` · `parser` · `call-graph` · `fallback`

### 覆盖 mismatch

- FMA-MISMATCH-071：模板区域中的 `operator()` 抢占真实函数名。
- FMA-MISMATCH-073：合法 Python 多行签名被截断。
- FMA-MISMATCH-301：嵌套泛型调用漏边。

### Description

语义后端不可用或未索引文件时，fallback 解析器仍会直接影响函数文件、FQN 和调用图。当前实现依赖先后顺序和单层正则，无法可靠处理模板文本、多行 Python header 和嵌套泛型。

### Expected behavior

- C/C++ operator 只有在函数名位置才被识别，模板参数中的文本不能抢占外层声明。
- Python 函数范围使用 `ast`/`tokenize` 或括号状态确定 header 结束，而不是依赖续行缩进。
- C++、Rust、Go 泛型调用使用平衡分隔符扫描，至少稳定提取基础 callee identifier。

### Acceptance criteria

- 使用编译器可接受的 C++ 模板/operator 样本验证普通函数名不会误提取。
- `def foo(a,\nb):` 及带 decorator、return annotation、默认 lambda 的多行签名都提取完整。
- `foo<std::vector<int>>(x)`、`bar::<Vec<u8>>(x)`、`fn[map[string]int](x)` 都产生对应基础调用边。
- 未配对分隔符不会导致崩溃；明确降级并保留后端来源信息。
- CodeGraph/AST 权威结果可用时仍优先使用，不被 fallback 覆盖。

---

## Issue 6

### Title

`fix(reasoner): track multiline lexical state when splitting braced functions`

### Priority / Labels

`P1` · `bug` · `reasoner` · `parser` · `correctness`

### 覆盖 mismatch

- 直接解决 FMA-MISMATCH-272。
- 关联 FMA-MISMATCH-188：增加“Reasoner 必须消费完整函数”的回归与可观测性，但不把 188 误标成 `generate_batch_prompts.main()` 的实现 Bug。

### Description

`_compute_brace_depth_per_line()` 每行重新处理块注释，`/*` 未在当前行闭合时不会把状态带到下一行。注释内的 `{`/`}` 会污染深度和安全切分点，使长函数被截成语法不完整的块。

### Expected behavior

- 单次跨行扫描显式维护 block comment、字符串、字符字面量和 escape 状态。
- 只有真实代码 token 改变 brace depth。
- 分块前后能够证明所有源行按顺序恰好出现一次，并记录函数总行数、块范围和输入 hash，便于发现 188 类“不完整分析”。

### Acceptance criteria

- 跨行注释中的任意括号不改变 depth。
- 跨行字符串/原始字符串按各支持语言的能力边界处理，并有文档说明。
- 每个分块在允许的语法边界结束；重新拼接块可恢复完整输入。
- Reasoner trace 能显示函数总行数和每个 block 的起止行，长函数后半段缺失可被自动检测。

---

## Issue 7

### Title

`fix(erlang): normalize ELP server argv and preserve call-graph backend failures`

### Priority / Labels

`P1` · `bug` · `erlang` · `call-graph` · `backend`

### 覆盖 mismatch

- FMA-MISMATCH-097：`elp server` 被扩展为 `elp server server`。
- FMA-MISMATCH-107：`call_edges()` 把 ELP 异常转换为权威空图。

### Description

最新版本已经让 Erlang batch extraction 返回 `None`、function spans 抛 `BackendUnavailableError`，从而保护增量清理；但 call graph 路径仍通过 `_analysis_or_empty()` 吞掉失败。同时 `_elp_argv()` 无条件追加 `server`，对已经包含子命令的配置产生错误 argv。

### Expected behavior

- 明确定义 `erlang.command` 是 executable/global args 还是完整 server command，并规范化成恰好一个 `server` 子命令。
- `call_edges()` 在 ELP 不可用或分析异常时返回 registry 可识别的 unavailable 信号，或抛出统一后端异常；只有成功分析且确实无边时返回 `{}`。
- 不撤销已经合入的抽取/函数范围失败保护。

### Acceptance criteria

- `elp` 与 `elp server` 都得到恰好一个 `server`；带空格路径和平台 quoting 有测试。
- `_analyze_project` 抛异常时 `call_edges()` 不返回 `{}`。
- registry 能区分 unavailable 与 authoritative empty，并在日志/摘要中报告降级。
- ELP 成功分析无调用项目时仍返回合法空图。

---

## Issue 8

### Title

`fix(llm): compare configured injection hostnames case-insensitively`

### Priority / Labels

`P2` · `bug` · `llm-client` · `configuration`

### 覆盖 mismatch

- FMA-MISMATCH-157。

### Description

无 scheme 的注入 target 走 hostname 地址空间匹配，但当前比较大小写敏感。DNS hostname 大小写无关，因此配置 `EXAMPLE.COM` 时请求 `example.com` 不会注入预期 metadata。

### Expected behavior

- hostname 分支按大小写无关、去除尾随点后的规范形式比较 exact host/subdomain。
- 带 scheme 的完整 URL prefix 分支维持其独立契约，不在本 Issue 中扩大匹配范围。

### Acceptance criteria

- `example.com`、`EXAMPLE.COM` 和相应子域名正确匹配。
- `notexample.com` 不得误匹配 `example.com`。
- IDNA/尾随点行为有明确测试或文档边界。

---

## Issue 9

### Title

`fix(resume): treat non-UTF-8 or corrupted JSON artifacts as invalid instead of crashing`

### Priority / Labels

`P2` · `bug` · `resume` · `recovery`

### 覆盖 mismatch

- FMA-MISMATCH-198。

### Description

`_json_file_is_valid()` 只捕获 `OSError` 和 `JSONDecodeError`。非法 UTF-8 在 JSON 解析前抛出 `UnicodeDecodeError`，会中断 incomplete/resume 扫描，而不是把坏文件交给已有的重新生成路径。

### Expected behavior

- 所有项目 JSON 以显式 UTF-8 读取。
- 编码错误、JSON 语法错误、I/O 错误统一返回 `False`，必要时记录文件路径和错误类别。
- 不吞掉与文件有效性无关的编程错误。

### Acceptance criteria

- 非 UTF-8、截断 UTF-8、多余半个 JSON 和目录路径都返回 `False` 而不抛异常。
- 合法 Unicode JSON 返回 `True`。
- resume/incomplete 扫描能够重新生成损坏 artifact。

---

## 候选 Issue A（提交前必须补证据）

### Proposed title

`fix(codegraph): preserve cross-language callees for callers in the requested language`

### 当前对应 mismatch

- FMA-MISMATCH-061。

### 为什么暂不直接提交

`CodeGraphExtractor.get_call_edges(lang_key)` 确实只用当前语言构建 node→FQN map，因此合成数据库里的跨语言 target 会被过滤。但尚未证明固定版本 `v1.5.0-fmagent.1` 能从真实 FFI 项目生成这种 `calls` edge，也尚未明确产品是否承诺跨语言调用图。

### 提交前验证清单

1. 构建至少一个真实最小项目，例如 Python C extension、JNI 或 Rust/C FFI。
2. 用固定 CodeGraph 版本执行索引，确认数据库存在跨语言 `calls` edge。
3. 调用 `get_call_edges()`，确认当前 FM-Agent 确实丢边。
4. 明确修复后是否要把所有语言节点加入 FQN map，及其对性能和同名解析的影响。
5. 有真实证据后，把 Issue 状态从“待确认”改为 confirmed，并提供 fixture/database 构造测试。

---

# Concise English Issues for GitHub

The following versions are intentionally shorter and can be pasted directly into GitHub.

## Web Issue 2

### Title

`fix(incremental): surface metadata generation failures and preserve unrelated callees`

### Affected mismatches

- FMA-MISMATCH-238
- FMA-MISMATCH-239
- FMA-MISMATCH-225

### Description

The incremental metadata pipeline currently uses `None` for both expected skips and LLM/spec-generation failures. A newly added function can therefore finish an incremental run without valid sidecars or a verification result.

Caller reconciliation also accepts a schema-valid but incomplete `new_info` object and writes it as a complete replacement. Updating one callee can silently delete metadata for other callees.

The existing post-write `is_file_ready()` rollback is useful, but it only protects plans that reach the write stage. It does not detect a missing plan or protect unrelated entries in a valid replacement object.

### Minimal counterexamples

#### Silent missing specification

```text
new function has no sidecars
_opencode_generate_spec() returns None
_update_specs_for_intent() returns []
verification returns SKIPPED
pipeline still finishes without a result for that function
```

#### Callee data loss

```json
// Existing .info.json
{"callees": [{"name": "callee_a"}, {"name": "callee_b"}]}

// LLM replacement while updating only callee_a
{"callees": [{"name": "callee_a"}]}

// Current result: callee_b is lost
```

### Impact

- Added or modified functions may be silently left unverified.
- Incremental completion can report incomplete coverage as success.
- Unrelated callee contracts can be removed from the workspace.
- Later reasoning and dependency propagation may use corrupted metadata.

### Suggested changes

- Replace ambiguous `None` results with explicit outcomes such as `updated`, `unchanged`, `unsupported`, and `generation_failed`.
- Require every added/modified function to have ready sidecars before reporting successful completion.
- Merge only the target callee entry in code; do not trust the LLM to preserve unrelated entries.
- Validate and atomically replace sidecars while keeping the existing readiness rollback.

### Acceptance criteria

- LLM timeout, invalid output, or missing output for a new function produces an explicit incomplete/error result.
- A changed function cannot finish successfully without valid `.spec.json` and `.info.json` files.
- Updating callee A never removes or changes unrelated callee B.
- Interrupted or invalid writes preserve the last ready sidecars.

---

## Web Issue 5

### Title

`fix(fallback-parser): handle valid multiline and nested language syntax`

### Affected mismatches

- FMA-MISMATCH-071
- FMA-MISMATCH-073
- FMA-MISMATCH-301

### Description

When CodeGraph is unavailable, initialization fails, or a file is not indexed, FM-Agent falls back to regex-based extraction and call detection. The fallback currently misidentifies valid C++ declarations, truncates valid Python functions, and misses nested generic calls.

### Minimal counterexamples

Valid C++ accepted by `g++ -std=c++17`:

```cpp
#include <utility>

template<class> struct Template {};
struct X { int operator()(int); };

void bar(Template<decltype(std::declval<X>().operator()(0))> value) {}
```

The outer function must be `bar`; the fallback can incorrectly identify an inner operator expression as the function name.

Valid Python accepted by `ast.parse()`:

```python
def foo(a,
b):
    return a + b
```

The fallback records only the first line instead of the complete function.

Nested generic calls are also missed:

```cpp
foo<std::vector<int>>(items);
```

### Impact

- Incorrect function names and FQNs.
- Truncated source passed to specification generation.
- Missing call edges and caller context.
- Incorrect top-down ordering and incremental propagation.

The problem is conditional on fallback mode, but fallback is an intentional production path when CodeGraph cannot be used.

### Suggested changes

- Use `ast`/`tokenize` for Python function ranges.
- Locate the outer C/C++ declarator before recognizing operator overloads.
- Replace single-level generic regexes with a small balanced-delimiter scanner.
- Record whether spans and edges came from a semantic backend or fallback.

### Acceptance criteria

- Valid C++ template/operator expressions do not replace the outer function name.
- Multiline Python signatures produce complete function ranges.
- Nested C++, Rust, and Go generic calls produce their base callee edges.
- Semantic backend results remain authoritative when available.

---

## Web Issue 1

### Title

`fix(config): handle empty TOML, quoted keys, and invalid URL ports`

### Affected mismatches

- FMA-MISMATCH-014
- FMA-MISMATCH-030
- FMA-MISMATCH-031

### Description

The LLM configuration workflow mishandles three valid or user-reachable inputs:

- an existing empty TOML file is treated as missing;
- valid quoted TOML keys are not recognized by the format-preserving editor;
- invalid URL ports pass validation and can be persisted.

### Minimal counterexamples

```python
# Existing empty TOML: currently reported as missing
toml_path.write_text("")
apply_llm_settings_update({"backend": "opencode"}, toml_path)

# Invalid port: currently accepted
validate_base_url("http://example.com:abc")
```

Quoted keys are valid TOML but cannot currently be updated:

```toml
[llm]
"name" = "old-model"
```

The editor preserves the quoted key and appends a bare `name`, producing a duplicate semantic key. Final validation prevents the invalid document from being written, but the valid original configuration cannot be updated.

### Impact

- Valid empty or quoted-key configurations cannot be updated.
- Invalid endpoints are accepted and fail later during client initialization or requests.
- Configuration errors are reported far from their source.

Existing TOML is normally not corrupted because final validation runs before writing.

### Suggested changes

- Distinguish file existence from empty content.
- Support bare, basic quoted, and literal quoted TOML keys.
- Validate `parsed.hostname` and `parsed.port`, converting URL parsing errors to `ConfigWizardError`.

### Acceptance criteria

- An existing empty TOML file can be initialized.
- Bare and quoted forms of the same key update exactly one semantic key.
- Invalid, negative, or out-of-range ports and missing hostnames are rejected.
- Valid IPv4, IPv6, and portless HTTP(S) URLs remain accepted.
