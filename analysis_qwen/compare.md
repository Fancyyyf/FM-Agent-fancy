# DeepSeek 与 Qwen 自验证结果对比分析

> 对比对象：同一 baseline `7d490cbe14486dfa741a22086bf1383fbc280ec7` 上的 FM-Agent 自验证结果。DeepSeek 产物位于 `fm_agent_ds/`，Qwen 产物位于 `fm_agent/`；两边均覆盖完全相同的 457 个 canonical function ID，均为 0 ERROR。本文只分析已有产物，没有重新调用模型或 validator。

## 结论先行

Qwen 的 MISMATCH 率从 DeepSeek 的 **68.27%（312/457）** 降到 **27.79%（127/457）**，下降 **40.48 个百分点**，相对下降 **59.29%**。但这不能简单解释成“Qwen 少报了 185 个误报，因此准确率更高”。逐函数转移显示：

- DeepSeek 的 312 条 MISMATCH 中，**204 条在 Qwen 中变成 MATCH**；
- Qwen 又在 DeepSeek 判 MATCH 的函数中产生 **19 条新 MISMATCH**；
- 所以净减少量是 `204 - 19 = 185`，而不是两次运行对同一批问题稳定地做了强弱不同的筛选；
- 两边仅有 **108 个共同 MISMATCH 函数**，Jaccard 为 **32.63%**；而且同函数经常报告不同 trigger，因此“具体 bug”的真实重叠明显低于 32.63%；
- DeepSeek 消失的 204 条中，原审计已判为 **SPEC 错误 63 条、推理误判 47 条**，合计 **110 条（53.92%）**。这一部分是最有证据支持的“减少的误报”；另有 64 条契约不确定和 30 条实现缺陷候选消失，不能自动算作纠正误报，也可能是 Qwen 漏检或换了关注点；
- 两边审计后的“实现缺陷候选”分别为 51 和 48 条，但只在 **16 个函数**上相交：DeepSeek 候选召回率 31.37%，Qwen 候选覆盖率 33.33%，Jaccard 仅 **19.28%**。其中又有不少是同函数不同边界条件，所以真实 bug-claim 重叠还要更低。

因此，MISMATCH 大幅下降的最可靠解释是：**模型更换同时改变了 SPEC oracle 和 Reasoner 的搜索方向**。Qwen 消除了大量 DeepSeek 的过度契约和错误推断，但也没有稳定复现 DeepSeek 的大多数实现缺陷候选；它还产生了自己的过度 SPEC 和新边界主张。Qwen 的结果更适合作为“较小的二次候选集”，不能仅凭较低 MISMATCH 率认定其 bug 检测准确率更高。

## 1. 可比口径与边界

### 1.1 可以直接比较的部分

两次运行具备严格的函数级可比性：

| 项目                    |           DeepSeek |               Qwen |
| ----------------------- | -----------------: | -----------------: |
| baseline                | `7d490cbe...ec7` | `7d490cbe...ec7` |
| canonical function ID   |                457 |                457 |
| MATCH                   |                145 |                330 |
| MISMATCH                |                312 |                127 |
| ERROR                   |                  0 |                  0 |
| Validator confirmed     |                262 |                113 |
| Validator not_confirmed |                 50 |                 14 |

逐个比对 `logic_verification_results/**/*.json` 后，两边 457 个相对路径集合完全一致。因此本报告不存在早期 380 函数运行、额外脚本函数或不同 base commit 混入的问题。

### 1.2 不能把 MISMATCH 当 ground truth

FM-Agent 的链条是“模型生成 SPEC → 模型推导实际 POST → 比较二者 → validator 依照该 SPEC 构造 probe”。模型不只扮演检测器，也参与生成 oracle。于是一次 MISMATCH 可能来自：

1. 实现确实违反产品契约；
2. SPEC 无依据地强化了产品契约；
3. Reasoner 错读代码、控制流或可达性；
4. 实现与 SPEC 有真实差异，但仓库证据不足以决定谁对；
5. 同一函数里有多个可报告边界，模型随机选中了其中一个。

同理，validator 的 `confirmed` 只说明 probe 复现了“实现与本轮生成 SPEC 不同”，不等价于产品 bug。DeepSeek 的 262 confirmed 中有 170 条在 Qwen 中变成 MATCH，正好说明 validator 不能作为跨模型 ground truth。

### 1.3 DeepSeek 报告文件的使用方式

DeepSeek 的完整同 baseline 审计是 [bug_list_v7_28.md](../buglists/bug_list_v7_28.md)、[SPEC 错误子清单](../buglists/bug_list_v7_28_spec_errors.md) 和[推理误判子清单](../buglists/bug_list_v7_28_reasoning_misjudgments.md)，总计恰好 312 条。Qwen 使用本目录的 [bug_list_qwen.md](bug_list_qwen.md)。

## 2. Verdict 转移：净下降是怎样形成的

| DeepSeek \ Qwen   |    Qwen MATCH | Qwen MISMATCH | DeepSeek 合计 |
| ----------------- | ------------: | ------------: | ------------: |
| DeepSeek MATCH    |           126 |  **19** |           145 |
| DeepSeek MISMATCH | **204** |           108 |           312 |
| Qwen 合计         |           330 |           127 |           457 |

由此可以得到三组不同性质的函数：

- **共同 MISMATCH：108 条。** 两个模型都认为存在某种 SPEC/实现冲突，但未必是同一冲突。
- **DeepSeek MISMATCH → Qwen MATCH：204 条。** 这是 MISMATCH 下降的主体，包含已知误报、契约不确定项，也包含可能被 Qwen 漏掉的候选 bug。
- **DeepSeek MATCH → Qwen MISMATCH：19 条。** 说明 Qwen 并非只是在 DeepSeek 清单上做保守删减，它也生成了新的 SPEC/trigger。

两边逐函数 verdict 的总体一致率只有 `(126 + 108) / 457 = 51.20%`。考虑两边 MISMATCH 基准率本来就差异很大，Cohen's κ 约为 **0.16**，仅属较弱一致。这是理解后续所有重叠率的关键：**更换模型实质上更换了 oracle，而不是只更换了同一 oracle 下的分类器。**

## 3. 三种“重叠率”必须分开看

### 3.1 Canonical MISMATCH 函数重叠

| 指标                                 |   数值 |
| ------------------------------------ | -----: |
| 共同 MISMATCH 函数                   |    108 |
| 以 DeepSeek 312 条为分母             | 34.62% |
| 以 Qwen 127 条为分母                 | 85.04% |
| Jaccard：`108 / (312 + 127 - 108)` | 32.63% |

85.04% 看起来很高，是因为 Qwen 集合小：Qwen 的大多数 MISMATCH 确实落在 DeepSeek 的大集合内。但反过来，Qwen 只保留了 DeepSeek MISMATCH 的 34.62%。因此不能只报告“Qwen bug 与 DeepSeek 重叠 85%”。

### 3.2 Validator confirmed 函数重叠

DeepSeek 有 262 个 confirmed 函数，Qwen 有 113 个；交集为 **87**：

| 指标                           |   数值 |
| ------------------------------ | -----: |
| confirmed 交集                 |     87 |
| 对 DeepSeek confirmed 的保留率 | 33.21% |
| 对 Qwen confirmed 的覆盖率     | 76.99% |
| Jaccard                        | 30.21% |

这个重叠并不比原始 MISMATCH 更稳定。尤其是 DeepSeek 消失的 204 条里仍有 **170 confirmed**，所以“probe 跑通并观察到差异”没有让该问题在另一个模型的 SPEC 下保持为 MISMATCH。

### 3.3 审计后实现缺陷候选重叠

将 DeepSeek“可能有 Bug”与 Qwen“实现缺陷候选”视为同一层级：

| 指标                   |             数值 |
| ---------------------- | ---------------: |
| DeepSeek 候选          |               51 |
| Qwen 候选              |               48 |
| 同函数交集             |               16 |
| 对 DeepSeek 候选的召回 |           31.37% |
| 对 Qwen 候选的覆盖     |           33.33% |
| Jaccard                | **19.28%** |

若放宽到“实现缺陷候选 + 契约待确认”，DeepSeek 为 142 条、Qwen 为 61 条，交集 32 条，Jaccard仍只有 **18.71%**。DeepSeek 的筛后 62 条队列中，只有 23 个函数仍是 Qwen MISMATCH；其中 Qwen 判为实现缺陷候选 18、SPEC 错误 4、契约待确认 1。

这说明两个模型对“值得人工修实现”的排序并不一致。总 MISMATCH 数下降并没有带来一个稳定、高重叠的小型 bug 集合。

## 4. 同函数不等于同一个 bug

对 108 个共同 MISMATCH 的两份 `trigger_condition` 做词项 Jaccard 检查，平均只有 **17.50%**：

- 仅 10/108 的词项相似度达到 30%；
- 53/108 低于 15%；
- 没有一项达到 50%。

英文长句的词项相似度不是语义 ground truth，但它足以揭示一个重要现象：很多共同 ID 只是两个模型在同一个复杂函数里各找了一个不同边界。

### 4.1 高度一致或同一根因的代表

- `_extract_functions_indent`：两边都指出多行 Python 函数头中，同缩进参数行使扫描提前停止；这是接近同一输入、同一控制流根因的重现。
- `_json_file_is_valid`：两边都使用不可解码字节触发未捕获的 `UnicodeDecodeError`，属于同一具体 claim。
- `_compute_brace_depth_per_line`：两边都指出跨行块注释状态没有延续，导致注释内花括号被计数。
- `_domain_context_complete`：两边都覆盖“合法 JSON 但顶层非 dict 后 `.get` 崩溃”，Qwen 还扩展了 phase 元素/编号类型。
- `_normalize_endpoint_label`：两边都定位到 `lstrip('./')` 的字符集合语义；DeepSeek 用 `../foo`，Qwen 用 `./.hidden.py`，输入不同但根因相同。

这些交集是真正适合合并为统一回归测试的部分。

### 4.2 同函数、相关主题、不同边界

- `run_opencode_traced`：DeepSeek 关注“exit code 为 0 但已有 error 字符串仍记录 success”；Qwen 关注启动时 `FileNotFoundError` 未更新局部状态，`finally` 误记 success。都属于失败状态记录，但不是同一异常路径。
- `_count_mismatches`：DeepSeek 关注目录遍历 OSError，Qwen 关注 JSON 顶层非对象造成 `AttributeError`。都是 robustness，却需要不同测试。
- `_extract_func_name_brace`：DeepSeek 报模板参数里的 `operator+` 假命中，Qwen 报 `operator,` 因正则漏逗号而漏检；方向甚至是一假阳性、一假阴性。

### 4.3 仅函数 ID 重叠、实际 claim 不同

- `State::_ingest_event`：DeepSeek 报非 verification 事件错误增加 verification counter；Qwen 报 cache miss 显式为 `null` 时加法触发 `TypeError`。
- `State::scan_bugs`：DeepSeek 报目录不存在时计数未归零；Qwen 报 result JSON 顶层为数组时 `.get` 崩溃。
- `update_llm_settings_toml_text`：DeepSeek 报 quoted key 未被正则识别而生成重复键；Qwen 报顶层 `llm` 已是标量时追加 `[llm]` 生成非法 TOML。
- `_function_spans`：DeepSeek 关注 universal newline 改写，Qwen 关注 `foo`/`foo_1` 的去重名称碰撞。
- `_deduplicate_phases`：DeepSeek 关注字符串 phase 未按数值排序，Qwen 关注同模块内部重复文件没有进入 `removed_files`。

因此，**32.63% 是“共同函数告警”的上界，不是具体 bug 重叠率**；19.28% 也只是“候选类别 + 函数 ID”的上界。保守地看，人工抽查的 16 个候选交集里，只有约 5 个可以直接视为同一根因，其他多为相关或不同边界。这里不强行给出精确语义百分比，因为一个函数可以同时包含多个真实 bug，而目前没有独立、去重后的 bug-claim ground truth。

## 5. 为什么两个模型识别出的 bug 大量不同

这不是因为两边看到了不同源码：baseline 和 457 个函数完全相同。根本原因是当前流程并非“把固定规范交给两个模型寻找违反项”，而是让模型同时参与**生成规范、解释实现和选择反例**。因此模型变化会同时改变裁判规则与搜索路径。具体可拆成以下八层。

### 5.1 两个模型使用的不是同一个 oracle

源码相同，不代表待验证命题相同。每轮 SPEC 都由当前模型根据源码、注释和 INFO 生成。例如同一个函数，DeepSeek 可能写出“目录不存在时返回空结果”，Qwen 可能写出“任何畸形 JSON 都不得抛异常”。之后 Reasoner 只检查实现是否满足**本轮自己的 SPEC**。

这相当于：

```text
DeepSeek：源码 → DS-SPEC → DS 选择的冲突
Qwen：   源码 → QW-SPEC → Qwen 选择的冲突
```

而不是：

```text
同一份人工规范 → DeepSeek / Qwen 分别找反例
```

所以同 baseline 只能保证“被观察对象相同”，不能保证“验证问题相同”。这是两边 bug 清单差异最大的结构性原因。

### 5.2 一条 MISMATCH 是两个生成阶段的组合，而非一次判断

最终 verdict 依赖至少两个模型产物：生成的 SPEC 和推导的 actual POST。两阶段任意一边发生轻微措辞变化，都可能翻转 verdict：

- SPEC 较强、POST 较窄，容易得到 MISMATCH；
- SPEC 与 POST 使用相同抽象层级，容易得到 MATCH；
- SPEC 强调异常类型而 POST 强调正常返回，即使实现没变也会冲突；
- 两者都遗漏同一个实现风险时，反而会稳定得到 MATCH。

因此 Qwen 的低 MISMATCH 可能来自更准确，也可能来自 SPEC 与自身 POST 更自洽，或者两阶段共同遗漏了某个边界。它不能仅凭总量与 DeepSeek 做“发现 bug 能力”的直接排序。

### 5.3 复杂函数通常不止一个可报告缺陷，模型只选中了其中一个

Reasoner 的输出结构通常只突出一个主要 `trigger_condition`，但一个函数可以同时包含多个独立边界。模型会受代码局部显著性和自身偏好影响，走向不同分支。例如：

- `State::_ingest_event`：DeepSeek 关注 verification counter 的错误归类；Qwen 关注 cache miss 为 `null` 时的 `TypeError`；
- `update_llm_settings_toml_text`：DeepSeek 关注 quoted key 导致重复键；Qwen 关注顶层 `llm` 已为标量时追加 `[llm]`；
- `_extract_func_name_brace`：DeepSeek 发现模板里的 `operator+` 假命中，Qwen 发现 `operator,` 漏匹配；
- `_function_spans`：DeepSeek 关注换行保持，Qwen 关注去重后名称碰撞。

这些结果并不必然互相否定。有时两个模型都找到了真实问题，只是找到了同一函数里的不同问题。以函数 ID 作为 bug ID 会把这种情况错误地显示成“重叠”，也会使跨模型差异看起来难以解释。

### 5.4 两个模型有不同的归纳偏好和风险先验

从实际清单可以看到不同的关注倾向：

- 有的模型更敏感于异常包装、never-raise、返回类型和精确格式；
- 有的模型更容易追踪数据结构不变量、schema、路径规范化和状态破坏；
- 有的模型倾向构造极端输入，例如非 dict JSON、无效 UTF-8、symlink 或 monkeypatch 异常；
- 有的模型更重视真实 caller 是否可能提供该输入。

这种差异与模型训练分布、代码推理风格以及对“不完整规范”的默认补全方式有关。项目中大量 internal helper 没有权威文档，模型必须自行猜测设计意图；两种合理但不同的猜测就会产生两份不同 SPEC。

### 5.5 前置条件的边界不同，会直接决定同一反例是否合法

大量争议都不是“代码会不会这样运行”，而是“这个输入是否属于函数承诺处理的范围”。例如合法 JSON 但顶层是数组、不可解码文件、空路径、`None` 字段、错误类型的 Mapping、缺失外部工具等：

- 如果 SPEC 把它纳入输入域，未捕获异常就是 MISMATCH；
- 如果 SPEC 认为 caller 已完成 schema 校验，它就是前置条件外输入，不应报 bug；
- 如果仓库没有文档和测试，两种判断都缺乏最终依据，只能列为契约待确认。

DeepSeek 与 Qwen 对这些隐式前置条件的补全不同，足以使大批 verdict 翻转。204 条 DS MISMATCH → Qwen MATCH 中有 64 条原本就是契约不确定，正体现了这种 oracle 缺失。

### 5.6 INFO/callee 摘要会产生级联差异

模型判断当前函数时不仅看函数体，也会依赖生成的 INFO、callee SPEC、调用图、抽取名称和中间 schema。若上游摘要对一个 helper 的行为写得更强或写错，调用它的多个函数可能连续出现 MISMATCH；换一个模型生成上游描述后，这一簇问题又会一起消失。

这在本次数据中有明显迹象：204 条消失项中，`languages` 有 43 条、`incremental_reasoner` 22 条、`configure_llm` 19 条，都是依赖链较长、sidecar 较多的区域。尤其 Erlang 后端单独消失 22 条，不太可能代表 22 个相互独立的实现问题恰好都被 Qwen 证明不存在，更可能包含共同的契约/摘要假设迁移。

### 5.7 Validator 会确认本轮 claim，但不会统一两个模型的产品语义

validator 依据本轮 trigger 和 SPEC 构造 probe，因此它有明显的**锚定效应**：DeepSeek 提出问题 A，validator 就尝试复现 A；Qwen 提出问题 B，validator 就尝试复现 B。即使两边都 `confirmed`，也可能只是各自证明了不同输入下“实现不满足各自生成的 SPEC”。

本次 DeepSeek 的 262 个 confirmed 中有 170 个在 Qwen 直接变成 MATCH；两边 confirmed 集合的 Jaccard 也只有 30.21%。这说明 validator 能过滤一部分不可执行的 Reasoner 幻觉，却不能把两个模型拉回同一个产品级 ground truth。

### 5.8 生成过程存在路径依赖和采样不稳定性

即使固定模型、prompt 和温度，长文本生成也可能因服务端实现、并发顺序、上下文组织和早期 token 差异走向不同结论。早期生成的一个 stronger/weaker 词语，会影响后续 POST 比较和 probe 选择。跨模型时，这种差异更大。

但“随机性”只是放大器，不是主要解释。现有数据呈现的是系统性差异：Qwen 127 条中有 108 条仍位于 DeepSeek 的 312 条大集合内，说明两者确实共同感知到一批复杂函数；可它们在这些函数内选择的具体 claim 经常不同。108 个共同函数的 trigger 词项 Jaccard 平均只有 17.50%，正符合“相同风险热点、不同验证路径”的特征。

### 5.9 综合判断：不是谁随机漏了同一份答案，而是问题定义随模型改变

两个模型清单不同，可归纳为下面的因果链：

```text
模型归纳偏好不同
        ↓
隐式产品意图与前置条件补全不同
        ↓
SPEC / INFO / callee 摘要不同
        ↓
Reasoner 选择的代码路径与反例不同
        ↓
Validator 被不同 trigger 锚定
        ↓
最终 MISMATCH 集合与审计分类不同
```

因此不能把两份列表视作针对固定答案的两次投票。更合适的理解是：它们是对同一源码进行的两次、使用不同自动生成规范的探索性审计。二者的交集适合提炼高稳定性问题，差集适合扩展候选覆盖；只有把 claim 转成独立回归测试并由维护者确认 expected 后，才能判断某模型究竟是正确发现、误报还是漏报。

## 6. 消失的 204 条 MISMATCH：哪些是减少的误报

### 6.1 按 DeepSeek 人工审计结论分解

| DeepSeek 原分类 |       DS 总数 | 变为 Qwen MATCH |         消失比例 | 对 204 条的占比 | 解读                               |
| --------------- | ------------: | --------------: | ---------------: | --------------: | ---------------------------------- |
| SPEC 错误       |            94 |    **63** |           67.02% |          30.88% | 最明确的过度/错误契约被消除        |
| 推理误判        |            76 |    **47** |           61.84% |          23.04% | 控制流、可达性、行为描述错误被消除 |
| 契约不确定      |            91 |    **64** |           70.33% |          31.37% | 冲突消失，但不能证明哪一轮契约更对 |
| 可能有 Bug      |            51 |    **30** |           58.82% |          14.71% | 有漏检风险，不能算作已纠正误报     |
| **合计**  | **312** |   **204** | **65.38%** |  **100%** |                                    |

所以，对“减少的误报”最稳妥的定量回答是：**至少 110/204（53.92%）属于 DeepSeek 审计已识别的 SPEC 错误或推理误判**。这 110 条占净减少 185 条的 59.46%。其余 94 条需要分为契约漂移与潜在漏检，不能为了得到漂亮结论而统称误报。

### 6.2 减少的误报主要类型

#### A. SPEC 自造了源码未承诺的输入域或错误策略

这是 63 条消失 SPEC 错误的主体。常见模式包括：

- 把辅助函数写成“对任意畸形 JSON、任意类型、不可解码文本、所有 I/O 问题都 never-raise”；
- 把格式偏好写成精确契约，例如显示小数位、输出路径必须绝对化、排序或字符串拼接必须采用唯一形式；
- 要求捕获 `BaseException`、`SystemExit`，或要求将所有底层异常统一包装，而调用者和文档没有这种承诺；
- 对 internal helper 添加其真实调用链永远不会提供的非法参数，再用该参数制造反例；
- 把“推荐行为”强化为原子性、完整保留、唯一命名或跨平台保证。

消失实例包括 `_parse_args`、`_read_text_if_exists`、`_dedupe_edges`、`command_argv`、`resolve_model_backend`、`_is_test_file`、`run_entry_pipeline` 等。它们并不是统一被 Qwen“证明正确”，而是 Qwen 生成的 SPEC 没再包含 DeepSeek 的那条强断言。

#### B. Reasoner 错读控制流、数据结构或可达性

47 条消失项原本已被归为推理误判。典型模式包括：

- 把抽取后的代码片段误判为语法错误、缺失函数头或不可执行；
- 忽略 caller/callee 提供的前置保证；
- 错解 truthiness、正则、SQLite、路径或语言语法；
- 构造的 probe 没有真正走到声称的分支；
- 将 INFO sidecar 的错误或不完整摘要级联为当前函数的 MISMATCH。

这类错误在 `languages`、`incremental_reasoner`、`dashboard`、调用图与抽取函数中尤其明显。Qwen 判 MATCH 通常表示它没有复述 DeepSeek 的错误推导，但仍不等于对全函数完成了形式证明。

#### C. 对返回格式、排序、默认值和容错偏好的过度精确化

这一类横跨 SPEC 错误和契约不确定，数量无法从四分类中无歧义地单独相加，但在消失清单中反复出现：

- `dashboard` 的 cache rate、价格显示、layout/render 行数与格式；
- CLI 参数和 display string 的唯一构造形式；
- 缺失值究竟返回 `None`、空对象、空字符串还是抛异常；
- 是否保持输入顺序、是否数字排序、是否去重以及如何命名重复项；
- 路径是相对还是绝对、是否解析 symlink、是否保留原始换行。

这些冲突往往确实可被 probe 复现，却缺乏产品层证据。Qwen 少报它们，降低了噪声；但如果项目对输出格式有外部兼容约束，仍应由真实测试/文档确认。

#### D. 非法或极端输入造成的“通用 robustness”告警

DeepSeek 大量 MISMATCH 使用 non-dict JSON、不可读文件、非法 UTF-8、空路径、任意对象、symlink race 或异常 monkeypatch。这里要分两种：

- 若输入来自用户文件、trace、插件或 LLM artifact，robustness 可能是真 bug；
- 若函数只由受控 caller 调用且前置 schema 已验证，则是输入域外误报。

Qwen 并非整体拒绝这种模式。相反，它自己的候选中仍大量使用 non-object JSON、无效 UTF-8 和 `None` 字段。这意味着下降不是一个简单的“Qwen 更尊重前置条件”规则，而更像是两个模型对每个函数选择了不同的边界。

#### E. Callee/INFO 与抽取产物的级联污染

DeepSeek 消失项在模块上最集中于 `languages` 43 条，其中 Erlang 22、codegraph 9；其次是 `incremental_reasoner` 22、`configure_llm` 19、`dashboard` 12、`opencode_trace` 12。语言后端和增量流水线有更长的依赖链，SPEC 会吸收 callee INFO、路径约定和中间 schema。一处 sidecar 假设偏差会让多个 wrapper 同时报 MISMATCH。

这解释了为什么换模型后会成片消失：改变上游 INFO/SPEC 的表述，可以同时取消下游多个冲突。它们不应被当成相互独立的 43 个产品 bug。

### 6.3 不能忽略的 30 条 DeepSeek 实现缺陷候选

DeepSeek 的 51 个实现缺陷候选有 30 个被 Qwen 判为 MATCH，消失率 58.82%。这部分包括配置、抽取、语言后端、trace、pipeline 与验证器中的具体风险。可能的解释有三种：

1. DeepSeek 原审计仍把一个边界高估成真实调用域，Qwen 的 MATCH 更合理；
2. Qwen SPEC 没写到该保证，因而没有机会检测；
3. Qwen Reasoner 没搜索到 DeepSeek 的反例。

现有结果无法区分这三者。若目标是减少 token 成本，正确做法不是重跑 204 条，而是把这 30 条已有 DeepSeek probe 作为固定回归集，直接在 baseline 上独立复验。这样可在不重新生成 SPEC 的情况下判断 Qwen 的 MATCH 究竟是降噪还是漏检。

## 7. Qwen 新增的 19 条 MISMATCH 说明了什么

Qwen 新增项的审计构成为：

| Qwen 分类    | 数量 |
| ------------ | ---: |
| SPEC 错误    |    9 |
| 推理误判     |    3 |
| 契约待确认   |    4 |
| 实现缺陷候选 |    3 |

12/19 已被归为 SPEC 错误或推理误判，说明 Qwen 也会制造自己的误报，并非简单地比 DeepSeek 更保守。三个新实现缺陷候选是：

- `_required_string`：清理成对引号后可能返回空字符串；
- `_quote_toml_string`：U+007F 未转义可能生成非法 TOML；
- `CodeGraphExtractor::get_function_spans`：重载/同名函数可能产生不唯一名称。

另外的新项包括 CRLF 改写、layers spec 的额外连字符、缺少 codegraph index 时 C handler 返回 `{}` 还是 `None` 等契约待确认项；以及对 `BaseException`、默认编码、symlink cache key、非 ASCII dict key 等过强契约。它们证明两个模型不是沿同一阈值移动，而是在不同问题空间采样。

## 8. 为什么 Qwen 的 MISMATCH 率会下降这么多

### 8.1 直接原因：它生成了不同的 SPEC 与不同的 actual POST

同 baseline 只固定源码，不固定自然语言规范。两边每个函数的 SPEC、INFO 和 Reasoner 结果都由模型生成。只要 Qwen 的 SPEC 更接近它自己推导的 POST，MISMATCH 就会下降；这可能源于更准确，也可能源于更自洽或更少覆盖某些行为。

值得注意的是，Qwen SPEC 反而更长、更强断言化：457 份 SPEC 的 pre+post 平均字符数约 **1447**，DeepSeek 约 **783**；Qwen 中含 `exactly` 的 SPEC 约 284 份，DeepSeek 约 56 份，含 raise 相关表述的也更多。因此不能用“Qwen SPEC 更短、更宽松”解释下降。更合理的机制是：

- Qwen 对代码分支的描述与自己生成的 SPEC 更一致；
- Qwen 将更具体的 caller/数据格式信息写入前置条件或同一份行为叙述；
- DeepSeek 更常在 SPEC 与 POST 两阶段产生彼此不一致的假设；
- 两个模型选择不同边界，Qwen 没有触发 DeepSeek 的多数冲突。

换句话说，下降主要是**跨阶段自洽性与关注点迁移**，不是单纯的规范宽松化。

### 8.2 DeepSeek 基准率本身包含大量已知噪声

DeepSeek 的 312 条中，94 条 SPEC 错误、76 条推理误判，已知高置信误报下界为 **170/312 = 54.49%**。Qwen 的 127 条中，对应两类为 66 条，误报下界 **51.97%**。两者在“各自 MISMATCH 内部的误报比例”其实接近；真正不同的是 DeepSeek 产生了更多 MISMATCH 总量。

按全部 457 个函数计算：

- DeepSeek 已知高置信误报告警密度：`170/457 = 37.20%`；
- Qwen 已知高置信误报告警密度：`66/457 = 14.44%`。

因此 Qwen 确实大幅减少了绝对误报负担，但它没有显著改善“一个 MISMATCH 最终能进入实现缺陷候选”的精度：DeepSeek 为 `51/312 = 16.35%`，Qwen 为 `48/127 = 37.80%`，虽提高明显，却伴随对 DeepSeek 候选仅 31.37% 的函数级召回。精度提高与召回下降同时存在。

### 8.3 Qwen 更集中，DeepSeek 更铺开

Qwen 的 127 条中有 108 条位于 DeepSeek 的大集合，说明它大体在 DeepSeek 覆盖过的复杂函数内取了一个更小子集；但 19 条新增又表明它会在局部发现新边界。DeepSeek 更像高召回、低精度的广撒网；Qwen 更像较窄但仍不稳定的二次扫描。

这种“集中”在模块分布上也可见：DeepSeek 消失最多的是语言后端、增量 reasoner、配置和 trace 等长链模块；共同 MISMATCH 则集中在 `configure_llm` 13、`incremental_reasoner` 12、`dashboard` 11、`pipeline_setup` 9、`languages` 8、`scope` 8。共同集更偏向输入 schema、文件格式、抽取边界和状态一致性等容易构造具体 probe 的区域。

### 8.4 Validator 会放大 SPEC 差异，而不会消除它

两边 validator 都以本轮 SPEC 为期望。一个过强 SPEC 往往很容易生成能跑通的 confirmed probe，因此 DeepSeek 的 SPEC 错误里也有大量 confirmed。validator 更像“反例可执行性检查”，而不是“产品契约真实性检查”。这就是为什么 170 个 DeepSeek confirmed 项仍会在 Qwen 变成 MATCH。

## 9. 两边四分类如何迁移

108 个共同 MISMATCH 的审计分类转移如下：

| DeepSeek → Qwen           | 数量 |
| -------------------------- | ---: |
| 契约不确定 → 实现缺陷候选 |   14 |
| 契约不确定 → SPEC 错误    |    9 |
| 契约不确定 → 推理误判     |    3 |
| 契约不确定 → 契约待确认   |    1 |
| 可能有 Bug → 实现缺陷候选 |   16 |
| 可能有 Bug → SPEC 错误    |    4 |
| 可能有 Bug → 契约待确认   |    1 |
| SPEC 错误 → SPEC 错误     |   20 |
| SPEC 错误 → 实现缺陷候选  |    5 |
| SPEC 错误 → 推理误判      |    4 |
| SPEC 错误 → 契约待确认    |    2 |
| 推理误判 → 推理误判       |    8 |
| 推理误判 → 实现缺陷候选   |   10 |
| 推理误判 → SPEC 错误      |    6 |
| 推理误判 → 契约待确认     |    5 |

只有 20 个 SPEC 错误、8 个推理误判、1 个契约项和 16 个实现候选在同层级上保持一致；其余 63/108 即使函数仍为 MISMATCH，审计性质也改变了。尤其是 10 个 DeepSeek 推理误判被 Qwen 归为实现缺陷候选，往往不是 Qwen 推翻了旧审计，而是 Qwen 在同函数选择了另一个、可成立的 trigger。不能把它理解为对 DeepSeek 原 claim 的“升级确认”。

## 10. 与 DeepSeek 最终人工 Review 的对比

前面的 51 个 DeepSeek“可能有 Bug”和过滤后的 40 个候选仍然只是中间分类。项目根目录的 [review_report.md](../review_report.md) 又检查了真实调用链、产品语义、最新源码和最小反例，代表 DeepSeek 结果目前最深入的人工裁决。它最终记录：

- 18 个实现缺陷记录；
- 225 与 239 属于同一数据丢失根因，合并后约为 17 个独立问题；
- 061 是 1 个待真实 CodeGraph 场景确认的问题；
- 076 和 188 明确排除为非实现 Bug。

因此，判断“去掉契约问题和 SPEC 问题后是否一致”，应以这 18 条而不是 DS 初筛的 40 或原分类的 51 条为基准。

### 10.1 函数级结果明显趋同，但没有完全一致

DS 最终 18 个实现缺陷记录中，有 11 个函数也被 Qwen 归为“实现缺陷候选”：

| DS ID | 函数                              | Qwen 是否保留为实现候选 |
| ----: | --------------------------------- | ----------------------- |
|   031 | `validate_base_url`             | 是                      |
|   030 | `update_llm_settings_toml_text` | 是                      |
|   071 | `_extract_func_name_brace`      | 是                      |
|   073 | `_extract_functions_indent`     | 是                      |
|   198 | `_json_file_is_valid`           | 是                      |
|   301 | `_get_call_regex`               | 是                      |
|   238 | `_plan_spec_update`             | 是                      |
|   239 | `_reconcile_caller`             | 是                      |
|   177 | `run_opencode_traced`           | 是                      |
|   252 | `State::scan_bugs`              | 是                      |
|   272 | `_compute_brace_depth_per_line` | 是                      |

由此得到：

| 指标                            |                     数值 |
| ------------------------------- | -----------------------: |
| DS 最终实现缺陷记录             |                       18 |
| Qwen 实现缺陷候选               |                       48 |
| 同函数交集                      |                       11 |
| Qwen 对 DS 最终记录的函数级覆盖 |         **61.11%** |
| 合并 DS 225/239 后的近似覆盖    | **11/17 = 64.71%** |
| DS 最终报告对 Qwen 候选的覆盖   |                   22.92% |
| 函数级 Jaccard                  |                   20.00% |

这与初筛阶段差异很大：拿 DS 过滤后的 40 个候选比较时，交集只有 14 个，覆盖率 35%；拿完整 51 个“可能有 Bug”比较时交集是 16 个，覆盖率 31.37%。经过最终人工 Review 排除过强 SPEC、输入域外反例和低价值项后，Qwen 对 DS 结果的覆盖上升到约 61%～65%。这说明原始巨大分歧中确实有相当部分是 DeepSeek 的契约、SPEC 和推理噪声。

但反向覆盖仍只有 22.92%：Qwen 的 48 个候选中只有 11 个进入 DS 最终报告。原因既可能是 Qwen 尚有大量误报，也可能是它发现了 DS 未选择的新 claim；在做同等深度人工 Review 前不能二选一。

### 10.2 11 个共同函数中，具体 bug 只部分一致

按 trigger 和根因复核，11 个函数可分为三层。

#### 基本是同一个 bug：4 个

- `_extract_functions_indent`：两边都指出 Python 多行函数签名中的同缩进参数续行使函数范围提前截止。
- `_json_file_is_valid`：两边都用不可解码字节复现未捕获的 `UnicodeDecodeError`。
- `_compute_brace_depth_per_line`：两边都指出跨行块注释状态未保存，注释中的大括号污染深度。
- `run_opencode_traced`：两边最终都指向异常路径仍可能记录为 `success`；DS 最新 Review 与 Qwen 的启动 `FileNotFoundError` 反例已经非常接近。

#### 同一根因，但具体输入不同：1 个

- `validate_base_url`：DS 使用非数字端口，Qwen 使用空 hostname 但 netloc 非空。具体反例不同，根因相同：实现只检查 `scheme/netloc`，没有完整验证 URL authority。

#### 只是同一函数，实际 claim 不同：其余 6 个

- `update_llm_settings_toml_text`：DS 报 quoted key 未被识别而产生重复键；Qwen 报顶层 `llm` 已是标量时追加 `[llm]`。
- `_extract_func_name_brace`：DS 报模板参数里的 `operator` 假命中；Qwen 报 `operator,` 因正则缺逗号而漏检。
- `_get_call_regex`：DS 报嵌套泛型调用漏检；Qwen 报 C 比较表达式被错误接受为泛型调用。
- `_plan_spec_update`：DS 报 LLM 生成失败和正常跳过都折叠为 `None`；Qwen 报合法 JSON 但非 dict 的旧 SPEC 错误进入后续路径。
- `_reconcile_caller`：DS 报 LLM 返回不完整 `new_info` 后覆盖并丢失其他 callee；Qwen 报无效 UTF-8 未捕获。
- `State::scan_bugs`：DS 报目录消失后遗留旧 pending；Qwen 报 result JSON 顶层非对象时 `.get()` 崩溃。

因此，11/18 是函数级一致，不是具体 bug 一致。严格按 claim 看，高度一致约 4 个，同根因约再加 1 个，即 DS 最终独立问题中约 **24%～29%** 形成了强跨模型共识。这个比例不应伪装成精确的模型指标，因为多缺陷函数允许两个 claim 同时成立；它更适合表示“无需重新争论 oracle、可以优先转成回归测试”的稳定核心。

### 10.3 DS 最终确认但 Qwen 未作为实现候选保留的项目

| DS ID | DeepSeek 最终问题                   | Qwen 结果 | 对比判断                                         |
| ----: | ----------------------------------- | --------- | ------------------------------------------------ |
|   014 | 空 TOML 文件被当作不存在            | SPEC 错误 | 对空文件产品语义判断不同，不能仅凭 Qwen 降级排除 |
|   157 | hostname 匹配大小写敏感             | SPEC 错误 | Qwen 不认可该契约，仍有漏报可能                  |
|   038 | 子进程非零退出仍报告成功            | MATCH     | Qwen 没覆盖该失败路径                            |
|   097 | 已含`server` 时重复追加           | MATCH     | Qwen 没选择该配置边界                            |
|   107 | Erlang 分析失败被伪装为空图         | MATCH     | Qwen 没保留失败/空结果语义问题                   |
|   139 | 不完整 phases 因 mtime 变化仍被接受 | SPEC 错误 | Qwen 在同函数报告了另一条 SPEC 问题              |
|   225 | caller-info 校验未保护其他 callee   | MATCH     | 与 239 同根因；Qwen 已在 239 上报另一问题        |

225 不应计作完全漏报，因为 DeepSeek 自己已将 225/239 合并，Qwen 也保留了 239 函数。其余项目已有 DS 人工调用链或反例支持；Qwen 的 MATCH/SPEC 错误只能说明它没有生成相同 claim，不能推翻 DeepSeek 的最终 Review。尤其应保留 `_check_oh_my_openagent`、`_elp_argv`、Erlang `call_edges`、`_run_generate_phases`、`_matches_inject_target` 和空 TOML 处理的回归测试。

### 10.4 Qwen 的 48 个候选尚未达到 DS 最终 Review 的证据等级

Qwen 的 48 个实现缺陷候选在 DeepSeek 原始 312 条审计中的分布为：

| Qwen 实现候选在 DS 中的分类 |         数量 |
| --------------------------- | -----------: |
| DS 可能有 Bug               |           16 |
| DS 契约不确定               |           14 |
| DS 推理误判                 |           10 |
| DS SPEC 错误                |            5 |
| DS MATCH                    |            3 |
| **合计**              | **48** |

这不能解释为“Qwen 有 29 条已被 DS 证明是误报”，因为同函数可能是不同 claim；但它说明 Qwen 的静态四分类不能直接等同于最终真 bug。DS 的 `review_report.md` 对候选继续检查了调用方是否保证输入合法、SPEC 是否有文档/schema 支持、最小 probe 是否证明了真实产品影响，以及最新源码上是否仍可触发。Qwen 48 条尚未全部经过这些步骤。

Qwen 独有候选中，以下模式仍值得进入深审：

- 非对象 JSON 导致 `.get()` 崩溃，且该文件确实可能由外部、LLM 或恢复流程产生；
- sidecar/trace 无效 UTF-8 导致恢复、dashboard 或 pipeline 中断；
- 写文件前先截断旧 sidecar，随后校验失败造成数据破坏；
- 函数名称去重碰撞、plugin manifest 类型校验不足；
- JSON-RPC falsy error 被忽略、失败状态被记录为成功；
- validator summary 遇到非对象 result 崩溃、中断时丢失已完成 verdict；
- TOML 控制字符或结构冲突使生成配置不可解析。

以下模式则很可能在同等级 Review 中被降级：

- 对所有异常都要求统一包装或 never-raise；
- 反例违反真实 caller 已保证的 schema；
- 要求捕获 `BaseException`、`SystemExit` 等控制流异常；
- 没有并发读者证据却要求严格目录原子替换；
- CRLF、默认编码、symlink 等行为只属于跨平台偏好而非产品保证；
- internal helper 被要求处理其设计输入域外的任意对象。

### 10.5 最终回答：去掉契约和 SPEC 噪声后是否一致

结论应分成两句话：

1. **在风险函数层面，结果明显趋同。** Qwen 覆盖了 DS 最终实现缺陷记录的约 61%～65%，远高于初筛阶段约 31%～35%；这说明 Review 确实移除了大量导致两模型分歧的契约和 SPEC 噪声。
2. **在具体 bug claim 层面，仍不一致。** 强同根因交集约 4～5 个，只占 DS 最终独立问题的约四分之一到三分之一；大量共同函数实际报告了不同边界，而 Qwen 还有 37 个不在 DS 最终 18 条中的候选。

因此，DeepSeek 最终 Review 与 Qwen 不是互相否定，而是形成三层集合：

- **强交集 4～5 项**：作为最高优先级固定回归集；
- **DS 最终独有项**：已有较深人工证据，不应因 Qwen MATCH 而删除；
- **Qwen 独有候选**：作为新增覆盖，需要复制 DS `review_report.md` 的审查标准后才能进入最终 Bug 清单。

最准确的判断是：**去掉契约与 SPEC 问题后，两模型在“哪里风险高”上达到中等一致，在“究竟是哪一个具体 bug”上仍只有低到中等一致。当前证据支持多模型互补，不支持用 Qwen 的较低 MISMATCH 直接替换 DeepSeek 的人工 Review。**

## 11. 应如何使用这两次结果

### 11.1 不用总 MISMATCH 率评判模型优劣

27.79% 比 68.27% 更便于人工处理，但不是天然更准确。一个生成空泛 SPEC 的模型可以得到极低 MISMATCH，一个生成极强 SPEC 的模型可以得到极高 MISMATCH。真正应比较的是固定 ground-truth claim 上的 precision、recall 和复现稳定性。

### 11.2 建立去模型化的三层回归集

建议从已有产物构建，不必重新烧大规模 token：

1. **稳定同根因集**：先收录两边明显同一 claim 的 `_json_file_is_valid`、`_extract_functions_indent`、`_compute_brace_depth_per_line`、`_domain_context_complete`、`_normalize_endpoint_label` 等；
2. **单模型候选集**：复用 Qwen 的 3 个新增候选，以及 DeepSeek 消失的 30 个实现候选的现成 probe；
3. **误报回归集**：收录两边 SPEC 错误和推理误判，测试未来模型是否再次生成同类过强契约或错误可达性判断。

每个条目应固定源码输入、明确产品级 expected、保留最小 probe，并给 claim 一个独立 ID，而不是继续用函数 ID 代替 bug ID。

### 11.3 最有性价比的下一步

如果只做一次低成本人工/测试复核，优先级应是：

- 先复跑两个模型都同根因命中的少量 probe，得到高稳定核心集；
- 再复跑 DeepSeek 消失的 30 个实现缺陷候选，判断 Qwen 的 30 个 MATCH 中有多少实际漏报；
- 再复核 Qwen 新增的 3 个实现候选；
- 其余 110 个已知高置信误报无需重新调用大模型，直接转成 evaluator 的负例；
- 64 个契约不确定项只在维护者给出真实契约后处理，否则继续调用模型不会解决 oracle 缺失。

## 12. 最终判断

Qwen 的价值主要是把人工面对的原始 MISMATCH 从 312 压缩到 127，并消除了至少 110 条 DeepSeek 已知的 SPEC/推理噪声。就“告警负担”而言，它明显更好；就“每条告警成为实现缺陷候选的比例”而言，也从 16.35% 提升到 37.80%。

但两个关键事实阻止我们直接宣布 Qwen 更准确：

1. Qwen 只保留 DeepSeek 51 个实现候选中的 16 个函数，可能漏掉大量真实边界；
2. 即使共同 MISMATCH，同一具体 trigger 也经常不同，说明运行结果对模型和生成措辞高度敏感。

最准确的表述是：**Qwen 显著降低了 DeepSeek 式的过度告警，并形成了更小、更高候选密度的清单；但当前证据只能证明降噪，尚不能证明在固定真实 bug 集上的总体准确率或召回率更高。** 两次结果的最大用途不是选出一个“赢家”，而是取交集构造稳定正例、取各自误报构造负例、对不重叠的实现候选做一次低成本独立回归，从而把自指的 LLM oracle 转成可重复的工程测试。

## 数据来源

- Qwen 总结：[conclu.md](conclu.md)
- Qwen 全量审计：[bug_list_qwen.md](bug_list_qwen.md)
- DeepSeek 全量主清单：[bug_list_v7_28.md](../buglists/bug_list_v7_28.md)
- DeepSeek SPEC 错误：[bug_list_v7_28_spec_errors.md](../buglists/bug_list_v7_28_spec_errors.md)
- DeepSeek 推理误判：[bug_list_v7_28_reasoning_misjudgments.md](../buglists/bug_list_v7_28_reasoning_misjudgments.md)
- DeepSeek 筛后队列：[bug_list_v7_28_zh_filter.md](../buglists/bug_list_v7_28_zh_filter.md)
- DeepSeek 最终人工 Review：[review_report.md](../review_report.md)
- Qwen 原始 verdict：[`fm_agent/logic_verification_results`](../fm_agent/logic_verification_results/)
- DeepSeek 原始 verdict：[`fm_agent_ds/logic_verification_results`](../fm_agent_ds/logic_verification_results/)
