# Callee expectation

`FMA-MISMATCH-048` 。被检查的函数是 `_dedupe_edges()`：

- 实现会合并重复的调用边，并按照 `(caller.fqn, callee.fqn)` 的字典序输出；
- 自动生成的 SPEC 却要求结果保持首次出现顺序。

它最初由模型写入上层函数 `load_call_edges()` 的 `.info.json`，随后作为 callee expectation 传入下一层 SPEC，最终被 Reasoner 和 Validator 共同放大。

## Workflow

```text
load_call_edges() 源码
  ↓
模型生成 load_call_edges 的 SPEC 与 INFO
  ↓
INFO 首次加入“_dedupe_edges 应保持首次出现顺序”
  ↓
batch prompt 将该要求作为 callee expectation 传给 Layer 1
  ↓
_dedupe_edges 的 SPEC 接受该要求
  ↓
行为分析正确识别实现按字典序输出
  ↓
Reasoner 比较“字典序”与“首次出现顺序”，报告 MISMATCH
  ↓
Validator 围绕同一 SPEC 构造反例，得到 confirmed
  ↓
人工复核发现顺序要求没有独立契约来源，将其归为 SPEC 错误
```

## 1. 源码行为

`load_call_edges()` 遍历目录时先对文件路径排序，再按顺序读取其中的调用边，最后把结果交给 `_dedupe_edges()`：

- [`src/call_graph_edges.py`](src/call_graph_edges.py#L70)：`load_call_edges()` 入口；
- [`src/call_graph_edges.py`](src/call_graph_edges.py#L78)：`sorted(edge_path.rglob("*"))`；
- [`src/call_graph_edges.py`](src/call_graph_edges.py#L80)：依次加载文件中的 edge；
- [`src/call_graph_edges.py`](src/call_graph_edges.py#L81)：调用 `_dedupe_edges(edges)`。

`_dedupe_edges()` 对相同 caller/callee 的边进行合并。每组数据的 `source` 取第一次出现的值，`callsite_names` 和 `info_names` 也按出现顺序合并，但最终列表明确经过排序：

```python
for (_caller_fqn, callee_fqn), data in sorted(merged.items()):
```

对应源码位于 [`src/call_graph_edges.py`](src/call_graph_edges.py#L234)，最终排序位于第 257 行。

因此需要区分两个顺序：

- 组内字段保留首次出现顺序；
- 去重后的 edge 列表按 caller/callee 字典序输出。

## 2. 错误要求最初在哪里产生

`load_call_edges()` 位于 Layer 0，当时没有更上层 caller expectation。模型在分析它时，根据目录遍历的排序和一般的稳定去重习惯，为结果增加了顺序语义。

生成后的上层 SPEC 写道：

> Results derived from a directory walk are returned in a stable order consistent with the filesystem walk ordering.

记录位置：[`load_call_edges.py.spec.json`](fm_agent/extracted_functions/src/call_graph_edges-py/load_call_edges.py.spec.json#L4)。

同一次生成还创建了 `load_call_edges.py.info.json`。其中对 `_dedupe_edges()` 的要求进一步变成：

> The relative order of first occurrences is preserved.

记录位置：[`load_call_edges.py.info.json`](fm_agent/extracted_functions/src/call_graph_edges-py/load_call_edges.py.info.json#L16)，具体 post-condition 位于第 19 行。

这就是“保持首次出现顺序”的直接源头。原始生成记录保存在 [`opencode_b1baa9eb891d4e7bac42ca164501a54f.jsonl`](fm_agent/trace/opencode/opencode_b1baa9eb891d4e7bac42ca164501a54f.jsonl) 第 8 行，写入文件的工具调用位于第 10 行。由于单行 JSON 很长，可以搜索以下文字快速定位：

```text
Since this is a layer 0 function
Results from a directory are returned in a stable
The relative order of first occurrences is preserved
```

## 3. expectation 如何跨层传递

分层元数据把 `load_call_edges()` 放在 Layer 0，并记录它调用 `_dedupe_edges()`：

生成下一层 batch prompt 时，`generate_batch_prompts.py` 会读取 earlier-layer caller 的 `.info.json`，找到与当前 callee 匹配的条目，并把内容原样加入 `CALLEE EXPECTATIONS FROM CALLERS`：

- [`generate_batch_prompts.py`](fm_agent/spec_prompts/generate_batch_prompts.py#L265)：定位 caller 文件；
- [`generate_batch_prompts.py`](fm_agent/spec_prompts/generate_batch_prompts.py#L269)：读取 caller 的 `.info.json`；
- [`generate_batch_prompts.py`](fm_agent/spec_prompts/generate_batch_prompts.py#L272)：提取当前 callee 的 expectation；
- [`generate_batch_prompts.py`](fm_agent/spec_prompts/generate_batch_prompts.py#L281)：加入 `caller_expectations`；
- [`generate_batch_prompts.py`](fm_agent/spec_prompts/generate_batch_prompts.py#L294)：写入 batch prompt。

这一步只负责传播 expectation，没有验证它是否来自文档、测试或真实消费行为。

完整内容保存在 [`opencode_e4add81bed8a4a268e2349f4cc730415.jsonl`](fm_agent/trace/opencode/opencode_e4add81bed8a4a268e2349f4cc730415.jsonl) 第 4 行。可以搜索：

```text
CALLEE EXPECTATIONS FROM CALLERS
What callers expect from src::call_graph_edges-py::_dedupe_edges
The relative order of first occurrences is preserved
```

## 4. 为什么下层模型选择了 expectation

SPEC 生成规则要求以 caller 需求为准，并且将实现与 caller need 的差异视为潜在 Bug：

- [`system_prompt.md`](fm_agent/spec_prompts/system_prompt.md#L11)：要求关注 ordering 等不变量；
- [`system_prompt.md`](fm_agent/spec_prompts/system_prompt.md#L31)：声明必须可验证、可证伪；
- [`system_prompt.md`](fm_agent/spec_prompts/system_prompt.md#L35)：SPEC 是 caller-driven；
- [`system_prompt.md`](fm_agent/spec_prompts/system_prompt.md#L41)：SPEC 描述 intended correct behavior；
- [`system_prompt.md`](fm_agent/spec_prompts/system_prompt.md#L43)：不能因为当前实现不同就放弃 caller need。

Layer 1 模型其实注意到了冲突：源码使用 `sorted()`，caller expectation 却要求保留首次出现顺序。它最后按照 Rule 4 和 Rule 5 选择相信 caller expectation，并把冲突理解为实现缺陷。

这段权衡完整记录在 [`opencode_e4add81bed8a4a268e2349f4cc730415.jsonl`](fm_agent/trace/opencode/opencode_e4add81bed8a4a268e2349f4cc730415.jsonl) 第 8 行。建议搜索：

```text
Caller expectations from batch prompt
The implementation sorts the result
the gap IS the bug
```

最终生成的下层 SPEC 位于 [`_dedupe_edges.py.spec.json`](fm_agent/extracted_functions/src/call_graph_edges-py/_dedupe_edges.py.spec.json#L4)。至此，一条由上层模型推导出的偏好已经固化成必须满足的函数契约。

## 5. 如何生成 MISMATCH

Reasoner 收到的两个条件分别是：

- Condition A：实现按 caller/callee 字典序输出；
- Condition B：SPEC 要求保持首次出现顺序。

Validator 沿用同一条 SPEC，构造了顺序为 `B、A、C` 的输入：

```text
SPEC 期望：B、A、C
实际输出：A、B、C
```

Validator 成功证明了实现不符合给定 SPEC，但它没有独立证明“首次出现顺序”是产品契约。

## 结论

048 展示的是一条完整的契约回声链：模型先在上层 `.info.json` 中生成 callee expectation，批次生成器再把它作为调用方需求传入下层；下层模型依据 caller-driven 规则将其固化为 SPEC，Reasoner 与 Validator 又围绕同一要求形成一致证据。

避免此类问题，需要为 callee expectation 保留来源和证据等级。由自动生成的上层 SPEC 或 INFO 推导出的要求，应标记为“推导约束”；只有得到文档、测试、schema 或真实调用方行为支持后，才适合升级为确认 Bug 所使用的强制契约。
