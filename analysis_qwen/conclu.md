# Qwen 自验证运行结论

## 1. 运行范围与 baseline

- 验证对象：FM-Agent
- 模型：`qwen3.8-max`
- 对比 baseline：`7d490cbe14486dfa741a22086bf1383fbc280ec7`
- baseline 函数总数：457
- 最终结果目录：`/home/fancy/Projects_Vault/FM-Agent/fm_agent`
- baseline 记录：`fm_agent/version.log`

## 2. 最终运行结果

| 项目     | 数量 | 占全部函数 |
| -------- | ---: | ---------: |
| 函数     |  457 |       100% |
| MATCH    |  330 |     72.21% |
| MISMATCH |  127 |     27.79% |

127 个 MISMATCH 的二次 bug validation 最终也全部完成：

| Validator 结论 | 数量 | 占 MISMATCH |
| -------------- | ---: | ----------: |
| confirmed      |  113 |      88.98% |
| not_confirmed  |   14 |      11.02% |

最终审计还确认：

- 457 个函数均存在有效的 `.spec.json` 和 `.info.json`；
- 457 个 canonical 结果均为有效 JSON；
- 127 个 MISMATCH 均存在有效 validator 结果；
- `fm_agent/` 下共检查 1,514 个 JSON，全部可解析；

## 3. 8 个 validator 为什么初次失败

### 3.1 直接原因

这 8 项的初次失败具有相同的直接原因：

1. OpenCode 已经启动 Qwen validator，并进行了读取、推理或工具调用；
2. 在写出最终 `<bug_id>.result.json` 之前，某一次模型操作返回 `The operation timed out.`；
3. OpenCode 随后以 exit code 1 退出；
4. FM-Agent 配置中的 `bug_validation_max_retries = 1`，所以主流程没有在原位置自动再次尝试；
5. 因结果文件尚未落盘，这些项被统计为“validator 缺失”，而不是 canonical `ERROR`。

Trace 中没有出现以下证据：

- HTTP 429 或明确的 rate limit；
- quota/额度耗尽提示；
- 401/403 鉴权失败；
- 输入 JSON 损坏；
- canonical 验证失败。

因此不能把这 8 项归因于“Qwen 给不出判断”或“8 个函数本身有问题”。有证据支持的结论是：**validator 的 OpenCode/Qwen 操作发生瞬态超时，导致产物未落盘。**

### 3.2 可能的诱因

初次失败调用的最后一轮已记录 prompt 规模约为 5,578–53,390 Tokens，其中多项超过 30k Tokens；同时主流程会并发执行多个 OpenCode validator。长上下文、工具调用链以及并发压力都会增加单次请求超过超时窗口的概率。

这部分是基于 trace 的工程判断，不是服务端明确返回的根因。服务端只明确报告了 `The operation timed out.`。

### 3.3 分项记录

| 函数/Validator ID                                            | 初次调用表现             | 最后一轮 prompt Tokens | 补试结果                       | 最终结论          |
| ------------------------------------------------------------ | ------------------------ | ---------------------: | ------------------------------ | ----------------- |
| `src--extract-py--run_extraction`                          | 请求超时，exit 1，未落盘 |                 37,203 | 并行补试成功                   | `not_confirmed` |
| `src--languages--erlang-py--_analyze_project_uncached`     | 请求超时，exit 1，未落盘 |                 53,390 | 并行补试成功                   | `confirmed`     |
| `dashboard-py--State::scan_bugs`                           | 请求超时，exit 1，未落盘 |                 44,748 | 并行补试成功                   | `confirmed`     |
| `src--incremental_reasoner-py--_update_specs_for_intent`   | 请求超时，exit 1，未落盘 |                 37,446 | 并行补试成功                   | `confirmed`     |
| `src--scope-py--rank_functions_in_file`                    | 请求超时，exit 1，未落盘 |                 30,836 | 并行补试成功                   | `not_confirmed` |
| `src--scope-py--_collect_func_idents`                      | 请求超时，exit 1，未落盘 |                 48,499 | 并行补试成功                   | `confirmed`     |
| `dashboard-py--_trace_value`                               | 请求超时，exit 1，未落盘 |                  5,578 | 并行补试再次超时；串行补试成功 | `confirmed`     |
| `src--incremental_reasoner-py--_extracted_files_by_method` | 请求超时，exit 1，未落盘 |                 38,911 | 并行补试再次超时；串行补试成功 | `confirmed`     |

第一次人工补试将 8 项并行提交，成功补回 6 项。仍然超时的 `_trace_value` 和 `_extracted_files_by_method` 随后改为串行运行，两项均成功生成结果。这说明失败具有瞬态性，并且降低并发是有效的恢复手段。

## 4. 8 项补试后的实际判断

这 8 项最终并非全部是真实 bug：

- 6 项为 `confirmed`；
- 2 项为 `not_confirmed`：`run_extraction` 和 `rank_functions_in_file`。

两个 `not_confirmed` 的含义是，validator 的具体 probe 显示实现符合规约或原始 MISMATCH 的触发路径不可达：

- `run_extraction`：报告声称测试文件、缺失文件或未映射扩展会增加 `skipped_count`，但 probe 得到规约要求的 `(0, 0)`，三次尝试均未复现该误计数。
- `rank_functions_in_file`：报告声称 LLM 重排错误使用 AND 条件；probe 证明代码实际实现的是规约要求的 OR gate，达到函数数量阈值时能够触发重排。

其余 6 项均由 probe 成功复现，最终结果文件和详细报告保存在 `fm_agent/bug_validation/`。

## 5. 对后续运行的建议

1. 将 `bug_validation_max_retries` 从 1 提高到至少 2，使瞬态超时能在主流程内自动恢复。
2. 对 validator 使用较低的并发上限，特别是 prompt 超过 30k Tokens 时。
3. 将“OpenCode exit 1 且未落盘”与 validator 的业务结论 `error` 分开统计；前者是基础设施失败，后者才是完整执行后的验证结论。
4. 自动重试时保留同一 bug ID，并在 trace 中记录 attempt 序号、HTTP 状态和具体超时层级。
5. 对耗时较长但仍持续占用 CPU 的 OpenCode 进程，不应过早重复提交；本次 `run_extraction` 补试持续约 16 分钟后正常落盘。

## 6. 总结

本次 Qwen 自验证在相同 baseline `7d490cbe` 上完成了全部 457 个函数，并通过保守迁移复用了约四分之三的既有工作。最终没有 canonical ERROR、损坏 JSON 或缺失 validator。

8 个 initially missing validator 的共同根因是 OpenCode/Qwen 操作超时，而不是额度错误或验证输入损坏；补试后 8 项全部完成，其中 6 项确认问题、2 项否定原始 MISMATCH。当前结果可以作为后续 Qwen 分析和与 `fm_agent_ds` 对比的完整输入。
