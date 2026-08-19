# DeepSeek MATCH / Qwen MISMATCH 的 19 项差分复核

## 1. 目标与口径

本报告复核同一 baseline `7d490cbe14486dfa741a22086bf1383fbc280ec7` 上，DeepSeek 判为 `MATCH`、Qwen 判为 `MISMATCH` 的全部 19 个函数。重点不是再次确认“代码是否违反 Qwen 生成的 SPEC”，而是判断该差异是否构成真实产品 Bug，并据此比较两种模型在这组差分样本上的判断质量。

逐项检查了以下证据：

1. DeepSeek 与 Qwen 的 canonical verdict、SPEC 和 trigger；
2. Qwen validator 报告及 probe；
3. baseline 源码、函数注释、caller 和相邻 helper 的组合契约；
4. CLI/文件格式等外部接口是否允许反例输入；
5. 反例是否只有在 Mock、非法前置条件或没有产品依据的强化契约下成立。

分类口径：

- **真实 Bug**：反例位于可信输入域，且违反代码、文档、格式标准或真实 caller 所要求的行为；
- **条件性问题**：机制真实，但是否必须修复取决于未明确的跨平台或字节级保真承诺；
- **非 Bug（SPEC 错误）**：差异可复现，但 Qwen 添加了没有依据的产品要求；
- **非 Bug（推理误判）**：Qwen 对代码、caller 或组合行为的描述本身不成立。

需要特别说明：19 项中 Qwen validator 给出 16 个 `confirmed`、3 个 `not_confirmed`。复核后，16 个 `confirmed` 远不等于 16 个真实 Bug；多数只证明代码不满足 Qwen 本轮自行生成的 SPEC。

## 2. 结论先行

| 最终分类          |         数量 | 含义                                         |
| ----------------- | -----------: | -------------------------------------------- |
| 真实 Bug          |  **3** | Qwen 发现了 DeepSeek 漏掉的有效问题          |
| 条件性问题        |  **2** | 行为可复现，但产品契约不足以直接裁定         |
| 非 Bug：SPEC 错误 | **11** | Qwen 自行强化了输入域、格式或容错要求        |
| 非 Bug：推理误判  |  **3** | Qwen 的 claim 被源码/caller/实际运行直接否定 |
| 合计              | **19** |                                              |

三个高置信真实 Bug 是：

1. `src--call_graph_edges-py--_required_string`：required field 清理后可变为空字符串；
2. `src--configure_llm-py--_quote_toml_string`：U+007F 生成非法 TOML；
3. `src--pipeline_setup-py--_merge_descriptions`：合法的 `description: null` 可触发 `TypeError`。

两个条件性问题是：

1. `_trim_source_file` 会把 CRLF 改写为 LF；
2. `_write_file_names` 未显式指定 UTF-8，依赖平台默认编码。

因此，对这 19 个“DS MATCH / Qwen MISMATCH”函数：

- 以高置信真实 Bug 为正例，Qwen 的告警精度为 `3/19 = 15.79%`；
- 即使把两个条件性问题全部按 Bug 计，精度上限也只有 `5/19 = 26.32%`；
- DeepSeek 的 19 个 `MATCH` 中有 3 个明确漏报，严格正确率为 `16/19 = 84.21%`；若两个条件项最终也被维护者定义为 Bug，则为 `14/19 = 73.68%`。

**就这一个差分子集而言，DeepSeek 的判断明显更准确，Qwen 的价值主要体现在补充召回：它用 19 条新增告警找到了 3 个 DeepSeek 漏掉的真实问题。** 这不等于 DeepSeek 在全部 457 个函数上总体更强，因为本报告只审查 Qwen 独有告警，样本选择天然不适合推导全局 precision/recall。

## 3. 逐项复核

|  # | 函数                                                         | Qwen validator    | 最终判断             | 关键理由                                                                                                                                                                                           | 本项更准确者   |
| -: | ------------------------------------------------------------ | ----------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
|  1 | `dashboard-py--build_layout`                               | `not_confirmed` | 推理误判             | `render_tokens` 固定输出 verification、opencode、TOTAL 三行，`tokens_h = 3 + 6` 正确，不存在由 state 动态增加的类别行。                                                                        | DeepSeek       |
|  2 | `dashboard-py--render_recent`                              | `not_confirmed` | 推理误判             | 唯一生产写入方`_push_recent` 使用 `appendleft`，容器已维持最新优先；render 不需要再次反转。                                                                                                    | DeepSeek       |
|  3 | `src--call_graph_edges-py--_required_string`               | `confirmed`     | **真实 Bug**   | `callee.fqn="''"` 通过初始非空检查，随后 `_clean_label` 返回 `""`。required field 最终为空却未拒绝，真实入口是用户提供的 extra-edge JSON。                                                   | **Qwen** |
|  4 | `src--cli_backend-py--messages_to_prompt`                  | `confirmed`     | SPEC 错误            | 多 text block 之间用换行保留边界是合理序列化；“concatenation”没有证据要求零分隔符。                                                                                                              | DeepSeek       |
|  5 | `src--configure_llm-py--_quote_toml_string`                | `confirmed`     | **真实 Bug**   | `json.dumps(..., ensure_ascii=False)` 不转义 U+007F，但 TOML basic string 禁止裸 DEL；最小检查确认 `tomllib` 拒绝生成文本。                                                                    | **Qwen** |
|  6 | `src--entry_reasoning_pipeline-py--_trim_source_file`      | `confirmed`     | **条件性问题** | universal newline 读取后以默认 newline 写回，CRLF 可变成 LF；但操作发生在隔离 run-directory 副本，当前文档未承诺字节级保真。                                                                       | 未定           |
|  7 | `src--file_utils-py--_write_file_names`                    | `confirmed`     | **条件性问题** | 未指定`encoding="utf-8"`，非 UTF-8 locale 下可能写出非 UTF-8 或抛错；但项目支持环境主要是现代 Ubuntu/macOS，是否承诺任意 locale 未明确。                                                         | 未定           |
|  8 | `src--generate_batch_prompts-py--_info_line_mentions_name` | `confirmed`     | SPEC 错误            | Qwen 使用`foo-` 作为 callee name；真实抽取标识会 canonicalize 不安全字符，未发现生产 caller 传入以非 word 字符结尾的裸名称。                                                                     | DeepSeek       |
|  9 | `src--generate_batch_prompts-py--extract_info_block`       | `confirmed`     | SPEC 错误            | helper 文档只承诺读取“usable object”，实际调用方随后通过`.get("callees", [])` 安全降级；Qwen 无依据要求此层执行完整 schema gate。                                                              | DeepSeek       |
| 10 | `src--generate_batch_prompts-py--parse_layers_spec`        | `confirmed`     | SPEC 错误            | CLI 文档虽只展示`0`/`0-5`，但 `0--0` 被 `int("-0")` 接受后仍等价于合法范围 `(0,0)`；没有产品影响或安全边界要求拒绝“额外分隔符”。                                                       | DeepSeek       |
| 11 | `src--languages--c-py--batch_extract`                      | `confirmed`     | SPEC 错误            | baseline registry 文档明确规定`batch_extract` 在 backend 不可用时返回 `{}`；当 registry 无数据时，`run_extraction` 会对每个文件走 regex fallback。Qwen 虚构了 `None` 三态契约。            | DeepSeek       |
| 12 | `CodeGraphExtractor::get_function_spans`                   | `confirmed`     | SPEC 错误            | 该函数注释明确返回未去重 identifier；唯一生产 caller`_function_spans` 随后统一按起始行添加 `_1/_2`，端到端名称与 extraction 保持一致。                                                         | DeepSeek       |
| 13 | `src--languages--codegraph-py--_node_fqn_map`              | `not_confirmed` | 推理误判             | Qwen 认为 SQLite 的`IN ()` 会报语法错，实际 SQLite 接受该语法并返回零行，函数得到 `{}`。                                                                                                       | DeepSeek       |
| 14 | `src--languages--erlang-py--_analysis_or_empty`            | `confirmed`     | SPEC 错误            | `SystemExit`、`KeyboardInterrupt`、`GeneratorExit` 不应被降级 helper 吞掉；要求 catch `BaseException` 会破坏进程退出和用户中断语义。                                                       | DeepSeek       |
| 15 | `src--languages--erlang-py--_analyze_project`              | `confirmed`     | SPEC 错误            | `abspath` 不合并 symlink 路径会造成重复缓存/重复分析，但没有证据要求所有 alias 共享缓存；改用 `realpath` 还会改变项目身份与持久化位置语义。                                                    | DeepSeek       |
| 16 | `src--languages--erlang-py--_module_from_uri`              | `confirmed`     | SPEC 错误            | precondition 已规定 URI 指向具体 Erlang 文档；Qwen probe 使用空 URI，违反真实 ELP symbol/document 输入域，再要求额外`ValueError`。                                                               | DeepSeek       |
| 17 | `src--pipeline_setup-py--_merge_descriptions`              | `confirmed`     | **真实 Bug**   | phase schema 不校验`description` 类型，LLM 可以生成 JSON `null`；caller 传 `module.get("description", "")` 时显式 null 仍为 `None`，随后 `source_desc in target_desc` 抛 `TypeError`。 | **Qwen** |
| 18 | `src--pipeline_setup-py--_post_process_phases`             | `confirmed`     | SPEC 错误            | 返回值的文档语义是“是否需要重生成 domain context”，不是“文件任意字节是否变化”。删除同 phase 内空 module 不改变 source-file 集和 phase 编号，无需将 resume 失效。                               | DeepSeek       |
| 19 | `src--reasoner-py--_sanitize_strings`                      | `confirmed`     | SPEC 错误            | docstring 明确只清理 string values；该函数处理框架自己构造的固定 ASCII keys。Qwen 将契约扩展到任意 dict key，并且其 SPEC 同时要求“same keys”和“key 被改写”，内部也不一致。                     | DeepSeek       |

## 4. 代表性案例

### 4.1 Qwen 正确发现：`_quote_toml_string` 违反真实格式标准

baseline 实现直接复用 JSON 字符串编码：

```python
def _quote_toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)
```

JSON 和 TOML basic string 的转义集合大体相似，但并不完全相同。Python 的 `json.dumps(..., ensure_ascii=False)` 会保留 U+007F（DEL）原字符，而 TOML 1.0 要求该控制字符必须转义。实测把结果放入：

```toml
[llm]
name = "<裸 U+007F>"
```

`tomllib.loads` 会抛出 `TOMLDecodeError`。该 helper 的调用方正是配置向导，输入来自 CLI、`.env` 迁移或用户配置；输出的核心职责就是生成可再次解析的 TOML。因此，这不是 Qwen 自造的健壮性偏好，而是明确的格式正确性问题。

DeepSeek 在此处给出 `MATCH`，说明它没有检查 JSON/TOML 转义集合的细微差异；Qwen 更准确。

### 4.2 Qwen 正确发现：`_required_string` 只在清理前检查非空

实现先检查 `value.strip()`，再调用更强的 `_clean_label`：

```python
if not isinstance(value, str) or not value.strip():
    raise ValueError(...)
return _clean_label(value)
```

对于 `"''"`，清理前非空，去掉成对引号后却变成空字符串。该函数名、错误信息和 caller `_parse_callee` 都明确表明 `callee.fqn` 是 required non-empty field。返回空 FQN 会让无效 extra-edge 继续流入后续去重/调用图过程，而不是在配置边界给出定位明确的错误。

这里 Qwen 的 SPEC 有独立语义来源：required 字段在**规范化后**仍应非空。DeepSeek 漏掉了“校验顺序与规范化顺序不一致”的经典输入验证问题。

### 4.3 Qwen 正确发现：`_merge_descriptions` 的反例可由真实上游产生

Qwen 使用 `target_desc=None`。如果孤立看 helper，这可能像输入域外反例；但 phase plan 是由 LLM 写出的 JSON，schema gate 只校验 `modules` 与 `source_files`，没有要求 `description` 必须是字符串。JSON 中显式的：

```json
{"description": null}
```

会通过该部分 schema。caller 使用 `module.get("description", "")`，默认值只处理 key 缺失，不处理显式 `null`，于是 `None` 进入 `_merge_descriptions`，在空值保护之前执行：

```python
if source_desc in target_desc:
```

并触发 `TypeError`。这是可信上游、真实 caller 和确定崩溃三项同时成立的实现缺陷。修复可以在 schema gate 拒绝非字符串 description，也可以先规范化 `target_desc = target_desc or ""`。

### 4.4 DeepSeek 正确：`get_function_spans` 的去重职责在 caller

Qwen 的 probe 构造两个同名重载节点，证明 `get_function_spans` 会直接返回重复 identifier。这个局部观察是对的，但 Bug 结论忽略了组合契约。

函数注释明确写着返回 class-qualified identifier，让“caller's dedup + name matching”保持一致。唯一生产 caller `_function_spans` 随后统一执行：

```python
count = name_counts.get(cname, 0)
deduped = cname if count == 0 else f"{cname}_{count}"
```

这样 codegraph 和 regex 两种 backend 都使用同一层的确定性去重。若在 `get_function_spans` 内再加 suffix，反而可能形成重复去重或破坏统一边界。Qwen 将最终系统不变量错误地下推到一个明确返回 raw identifier 的 helper，Validator 又只测试 helper 的直接返回值，所以得到了可复现但不代表端到端缺陷的 `confirmed`。

### 4.5 DeepSeek 正确：C `batch_extract` 的 `None` 契约来自错误版本/错误类比

Qwen 认为 codegraph 不可用时 C handler 必须返回 `None`，否则 regex fallback 不会启动。但 baseline 的 registry 文档明确写着：

- `batch_extract` 不可用时返回空 dict；
- `function_spans` 才用 `None` 表示逐文件 fallback。

实际 `run_extraction` 先合并 registry 返回的数据；某个 C 文件不在 `registry_funcs` 中时，会直接调用 `extract_functions_from_file`。因此 C handler 返回 `{}` 恰好会让所有 C 文件进入 regex fallback。Qwen 的 probe 只验证了 `{}` 不等于它生成的 `None` SPEC，没有验证 caller 真的停止 fallback。

这项还揭示了一个额外风险：当前工作树较新的 registry 已引入 unavailable-backend 三态说明，而实验 baseline 尚未采用同一契约。分析历史产物时若混用当前源码语义，容易把后来的设计投射回旧 baseline。

### 4.6 DeepSeek 正确：`_analysis_or_empty` 不应捕获 `BaseException`

Qwen 把“任何异常都不得逃逸”写入 SPEC，并使用 `SystemExit` 作为 probe。Python 将 `KeyboardInterrupt`、`SystemExit`、`GeneratorExit` 放在 `BaseException` 下，正是为了避免普通容错层误吞用户中断、进程退出和生成器关闭信号。

`_analysis_or_empty` 捕获 `Exception`，已经覆盖文件、子进程、协议解析等常规失败。把它改成捕获 `BaseException` 并返回空分析，会把 Ctrl-C 伪装成“ELP 没有结果”，继续执行流水线。这不是更健壮，而是改变控制流语义。Qwen 在这里把 never-raise 偏好提升成了错误契约。

## 5. 两种模型在这 19 项上的行为差异

### 5.1 Qwen 更善于提出具体边界，但容易把“可构造”当成“应承诺”

Qwen 找到的三个真实 Bug 都有相似特征：规范化后为空、两个格式标准的边缘差异、LLM 生成 JSON 中的显式 `null`。这些问题需要构造精确输入并跨 helper/caller 推理，DeepSeek 的 `MATCH` 没有覆盖到。

但 Qwen 同样为 `BaseException`、symlink cache key、零分隔符拼接、额外 CLI 分隔符、任意非 ASCII dict key等行为生成了强契约。probe 能证明实现没有满足这些要求，却不能证明要求属于产品设计。这使 Qwen 在本差分集中呈现“少量高价值新发现 + 大量局部鲁棒性主张”的模式。

### 5.2 DeepSeek 的 MATCH 多数更尊重现有实现边界，但并不是代码正确性的证明

DeepSeek 在 16 项上没有产生新增误报，特别是在 Dashboard 固定布局、caller 负责去重、C fallback 和 Python 控制流异常等问题上，与真实组合行为更一致。不过 `_required_string`、TOML DEL 和 nullable description 说明 `MATCH` 也可能只是没有探索到相应边界，而不是完成了正确性证明。

因此更准确的模型分工不是“DeepSeek 正确、Qwen 错误”，而是：

- DeepSeek 在这组样本上 precision 更高；
- Qwen 提供了额外 recall，但新增告警必须经过独立 oracle 审查；
- 两边的 verdict 都不能取代固定测试和产品级 expected。

## 6. 建议的后续动作

1. 为三个真实 Bug 建立独立回归测试，不再引用任何一轮生成 SPEC 作为 expected 来源；
2. 由维护者决定是否承诺临时源码副本保留换行风格，以及 `fm_agent_file_list.json` 在任意 locale 下必须为 UTF-8，再裁定两个条件项；
3. 把其余 14 项加入误报负例集，重点训练/评测模型是否会：
   - 忽略 caller 已维护的不变量；
   - 把最终系统不变量错误地下推给 helper；
   - 捕获 `BaseException` 等不合理健壮性要求；
   - 仅凭局部返回值而忽略端到端 fallback；
4. 后续跨模型比较应以独立 claim ID 和固定 probe 为单位，而不是以函数 ID 或各自生成的 `MISMATCH` 为单位。

## 7. 最终判断

在 DeepSeek `MATCH`、Qwen `MISMATCH` 的 19 个函数中，Qwen 明确纠正了 DeepSeek 的 3 个漏报，但另外 14 个告警属于 SPEC 错误或推理误判，2 个仍取决于产品契约。**所以在该差分集上，DeepSeek 的判断更准确，Qwen 的新增结果更适合充当高召回候选，而不适合直接作为 Bug 清单。**

更重要的结论是：Qwen 的 16 个 validator `confirmed` 最终只有 3 个能在当前证据下升级为真实 Bug。这说明 Validator 仍主要回答“能否复现实现与本轮 SPEC 的差异”，而不是“这条 SPEC 是否为产品真实契约”。这也是后续改进 FM-Agent 时最应优先拆分的两类判断。
