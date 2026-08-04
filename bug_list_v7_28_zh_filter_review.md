# FM-Agent 过滤后 Bug 候选逐条复核说明

> 本文件整理自 `bug_list_v7_28_zh_filter.md`，共 62 条。每条分别列出生成 SPEC 所要求的预期行为、实现的实际行为、被判为 Bug 候选的原因、规约违反点，以及进一步判读建议。
> `confirmed` 仅表示 probe 复现了实现与生成 SPEC 的差异，不等同于确认产品 Bug；最终判断仍应以真实调用链、文档、schema 和回归测试为依据。

## 汇总

| 类别 | 数量 | 建议 |
|---|---:|---|
| 契约不确定 | 22 | 先确认产品契约，再决定修改实现或 SPEC |
| 可能有 Bug | 40 | 确认真正可达性和影响面后进入修复/补测队列 |
| **合计** | **62** | — |

<a id="review-014"></a>
## FMA-MISMATCH-014 — `src--configure_llm-py--apply_llm_settings_update`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；尝试次数 `1`
- **原始详情：** [查看 FMA-MISMATCH-014](bug_list_v7_28_zh_filter.md#fma-mismatch-014)

### 预期行为

toml_path 处的文件被覆盖，使得 updates 中的每个键的值都写入到 [llm] 节中相应的字段路径，而所有其他节、字段以及更新字段之外的整个 TOML 结构均保持不变。在写入之前，原始文件内容被复制到一个与 toml_path 相邻的带时间戳后缀的备份文件中。当创建了备份时，返回备份文件 Path；当未创建备份时，返回 None。当 toml_path 不指向现有文件，或者更新后的 TOML 内容无法被标准库解析器解析为有效的 TOML 时，抛出 ConfigWizardError。

### 实际行为

函数执行后，以下情况之一成立：(1) 函数抛出了 `ConfigWizardError`（消息为 `"fm-agent.toml not found at {toml_path}; refusing to guess a new project config."` 或 `"Generated fm-agent.toml is invalid TOML."`）。此时，位于 `toml_path` 的文件保持不变，且未创建备份文件。(2) 函数正常返回了值 `r`。那么，位于 `toml_path` 的文件已被原子地替换为将给定的 `updates` 应用于原始文件的 `[llm]` 节后得到的 TOML 文本，同时保留文档的所有其他部分。如果 `r` 是一个 `Path` 对象，则在路径 `r`（与 `toml_path` 相邻，带时间戳后缀的名称）存在原始文件内容的备份副本；位于 `r` 的内容等于调用前原始文件的内容。如果 `r` 是 `None`，则未创建备份副本。
正式地，令 `orig` 为函数入口处 `toml_path` 的内容，令 `updated = update_llm_settings_toml_text(orig, updates)`。令 `F_before` 和 `F_after` 分别为紧接调用之前和之后的文件系统状态（将路径映射到内容）。
- 如果函数抛出 `ConfigWizardError`：
  `F_after = F_before`（未更改或创建文件）。
- 如果函数正常返回 `r`：
  `F_after(toml_path) = updated` 
  `(r = None  p adjacent to toml_path, F_after(p) = F_before(p)  no new timestamp-suffixed backup file exists)` 
  `(isinstance(r, Path)  r is a path adjacent to toml_path  r did not exist in F_before  F_after(r) = orig  all other files unchanged)`。

### 为什么会认为是 Bug

代码针对现有的空文件抛出 ConfigWizardError，并声称找不到该文件，这违反了规范。规范仅允许在 toml_path 不指向现有文件或更新后的 TOML 内容无法解析时抛出 ConfigWizardError。空文件存在，因此代码不应抛出“文件未找到”错误，而应继续生成更新后的 TOML。

### 如何违反规约

apply_llm_settings_update 针对现有的空 fm-agent.toml 文件抛出 ConfigWizardError，因为 _read_text_if_exists 对空文件返回 ''，而 'if not toml_text' 守卫将其与缺失文件同等对待。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-028"></a>
## FMA-MISMATCH-028 — `src--configure_llm-py--update_env_text`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-028](bug_list_v7_28_zh_filter.md#fma-mismatch-028)

### 预期行为

返回一个字符串，其中 (1) 恰好 一行将 ENV_SECRET_KEY 赋值为 api_key，其位置为已存在的 ENV_SECRET_KEY 行出现处，若不存在则追加到末尾； (2) 那些在去除可选的 'export ' 前缀后，其键属于一组预定义的传统 LLM 配置键的行，将被排除在输出之外； (3) 其他所有行——空行、注释或赋值行——按其原始相对顺序逐字出现。当已有的 ENV_SECRET_KEY 行带有 'export ' 前缀时，重写的行保留该前缀。当追加键且输入不包含任何非空、非注释行时，头部注释行会出现在追加的键行之前。

### 实际行为

函数返回一个字符串结果，通过以下方式转换输入文本（.env 文件内容）得到。令 L = text.splitlines(keepends=True)。按顺序处理每一行 ∈ L：令 s = .lstrip()。若 s 为空或 s.startswith('#')，则将  复制到输出。否则，尝试解析键值赋值。确定前导空白和可选的 'export ' 前缀：令 leading = [:len()-len(s)]；若 _ENV_EXPORT_PREFIX_RE.match(s) 成功，则令 export_prefix = leading + match.group()，令 working = leading + s[match.end():]；否则 export_prefix = ''，working = 。在第一个 '=' 处拆分 working：key_candidate, sep, _ = working.partition('=')。若 sep == ''（没有 '='），将  复制到输出。否则，令 env_key = key_candidate.strip()。若 env_key == ENV_SECRET_KEY，输出行 f"{export_prefix}ENV_SECRET_KEY={api_key}\n" 并设置标志 key_written = True。若 env_key 在 ENV_LEGACY_LLM_KEYS 中，则忽略该行（不复制）。否则，将  原样复制。处理完所有行后，若 key_written 为 False，追加秘密行：若输出列表为空，首先预置两行头部注释行：'# fm-agent secrets  gitignored, do not commit.\n'、'# Only the LLM API key belongs here.\n'；然后追加行 ENV_SECRET_KEY={api_key}\n。否则，若输出中最后一行的去除前后空白后内容非空，则先追加一个换行符 '\n'，然后追加秘密行；若最后一行已经是空白（仅包含空白字符），则仅追加秘密行。最后，返回所有输出行的拼接结果。从输入中复制的行的相对顺序得以保留。正式地：∃ key_written ∈ {true, false} 使得 result = ''.join(N)，其中 N 是一个字符串列表且满足以下条件：(1) 对每个 i， = L[i]，令 c(i) 为该行的类别：若 .strip() == '' 则为 'blank'；若 .lstrip().startswith('#') 则为 'comment'；剥离前导空白及可能的 'export ' 前缀后不含 '=' 则为 'no_eq'；若提取的键等于 ENV_SECRET_KEY 则为 'secret'；若提取的键 ∈ ENV_LEGACY_LLM_KEYS 则为 'legacy'；否则为 'other'。(2) 序列 N 由每个类别非 'legacy' 的 i 对应的字符串 v(i) 构成，v(i) 定义为：若 c(i) 为 'blank'、'comment'、'no_eq' 或 'other'，则 v(i)=；若 c(i) 为 'secret'，则 v(i)=export_prefix + ENV_SECRET_KEY + '=' + api_key + '\n'。(3) 若 key_written = true，则 N = [v(i) 对于所有 c(i)≠'legacy' 的 i]。(4) 若 key_written = false，则令 M = [v(i) 对于所有 c(i)≠'legacy' 的 i]；若 M 为空，N = ['# fm-agent secrets  gitignored, do not commit.\n', '# Only the LLM API key belongs here.\n', ENV_SECRET_KEY + '=' + api_key + '\n']；否则若 M[-1].strip() != ''，N = M + ['\n', ENV_SECRET_KEY + '=' + api_key + '\n']；否则 N = M + [ENV_SECRET_KEY + '=' + api_key + '\n']。(5) N 中 v(i) 的顺序与递增的 i 一致。

### 为什么会认为是 Bug

代码会替换每一次出现的 ENV_SECRET_KEY，当输入包含多个时，会为秘密密钥产生多行输出。而规范要求输出中该密钥恰好只有一行。

### 如何违反规约

当输入包含多个 ENV_SECRET_KEY 行时，函数会为每一次出现输出一个替换，违反规范中恰好一行该密钥的要求。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-031"></a>
## FMA-MISMATCH-031 — `src--configure_llm-py--validate_base_url`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-031](bug_list_v7_28_zh_filter.md#fma-mismatch-031)

### 预期行为

当 url 不是语法上有效的绝对 URL，且其 scheme 既不是 'http' 也不是 'https' 时，应抛出 ConfigWizardError。当 url 是语法上有效的绝对 URL，且 scheme 为 'http' 或 'https' 时，返回而不产生任何效果。

### 实际行为

如果函数正常返回（未抛出异常），则解析后的 URL 的 scheme 为 'http' 或 'https' 且 network location（netloc）非空。否则，抛出 ConfigWizardError，其消息指示 URL 无效。形式化表示：( url: str, url  ''  url == url.strip()  (after execution: (raised_exception  urlparse(url).scheme  {'http','https'}  urlparse(url).netloc  '')  (raised_exception  raised_exception is ConfigWizardError  raised_exception.args[0] starts with 'Base URL must be an absolute http(s) URL, got:')))

### 为什么会认为是 Bug

代码仅检查 scheme 是否为 http/https 且 netloc 非空，但未验证 netloc 是否构成语法上有效的 authority（例如，端口必须是数字，主机名不能包含空格）。像 'http://example.com:abc'（端口含字母）这样的 URL 根据 RFC 3986 并非语法上有效，但代码却接受它，因为 urlparse 将 netloc 设置为 'example.com:abc'，该值非空。SPEC 要求对任何非语法有效的绝对 URL 抛出 ConfigWizardError，因此该输入违反了 SPEC 规定。

### 如何违反规约

带非数字端口的 URL（http://example.com:abc）通过了 urlparse 的 netloc 检查，但根据 RFC 3986 语法上无效；SPEC 要求应抛出 ConfigWizardError。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-033"></a>
## FMA-MISMATCH-033 — `src--configure_llm-py--validate_llm_setting`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-033](bug_list_v7_28_zh_filter.md#fma-mismatch-033)

### 预期行为

当 key 不是可识别的 LLM 配置设置键时，抛出 ConfigWizardError。当 key 可识别时，如果 value 未能通过与该键关联的验证约束，则抛出 ConfigWizardError：要求非空修剪后字符串的约束（value 为空或去除前后空白后仅包含空白字符）；要求语法有效的、使用 http 或 https 协议的绝对 URL 的约束（value 不满足）；要求属于固定可识别标识符集合的约束（value 不在该集合中）；或委托给 API 风格适配器的约束（适配器拒绝 value）。当 key 可识别且 value 满足所有与之关联的约束时，返回且无副作用。

### 实际行为

函数 validate_llm_setting(key, value) 要么返回 None，要么抛出异常。如果 key 不在 _LLM_TOML_KEYS 中，抛出 ConfigWizardError("Unsupported LLM setting: {key}")。如果 key == 'provider' 且 value.strip() 为空，抛出 ConfigWizardError("Provider ID must not be empty.")。如果 key == 'base_url'，调用 validate_base_url(value.strip())，当 value.strip() 不是语法有效的绝对 URL（http 或 https 协议）时可能抛出异常；否则不抛出。如果 key == 'backend' 且 value 不在 _BACKENDS 中，抛出 ConfigWizardError 并给出列出受支持后端的消息。如果 key == 'api_style'，调用 adapter_for_api_style(value)，当 value 不是可识别的 API 风格时可能抛出异常；否则不抛出。若上述条件均未导致异常，函数返回 None，无副作用。

### 为什么会认为是 Bug

对于 base_url 和 api_style，规范要求当 value 验证失败时抛出 ConfigWizardError。然而，代码委托 validate_base_url 和 adapter_for_api_style，它们可能抛出非 ConfigWizardError 的异常（例如 ValueError）。因此，代码行为不符合所需的异常类型。

### 如何违反规约

可识别的键 'name' 和 'effort' 没有验证——validate_llm_setting('name', '') 和 validate_llm_setting('effort', 'invalid') 返回 None，而非按照规范要求抛出 ConfigWizardError。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-045"></a>
## FMA-MISMATCH-045 — `src--git-py--frozen_worktree`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-045](bug_list_v7_28_zh_filter.md#fma-mismatch-045)

### 预期行为

生成一个绝对路径 wt 指向一个目录，该目录在 yield 时刻的内容是进入 frozen_worktree 时 proj_dir 文件系统树的忠实快照。对 proj_dir 的后续修改不会反映在 wt 处的快照中。快照构建永远不会修改原始的 proj_dir 树、索引或 git 状态。如果 proj_dir 是一个至少有一次提交的 git 仓库，则快照是一个分离的 git 工作树，包含 HEAD、所有未提交的已跟踪编辑以及在进入时 proj_dir 中存在的所有未跟踪文件，并且名称与 exclude 匹配的条目将从 git 提交中排除。如果 proj_dir 不是一个具有有效 HEAD 的 git 仓库，则快照是 proj_dir 的递归目录副本，名称与 exclude 匹配的条目将被排除。当 copy_excluded 为 true 时，exclude 中指定的每个存在于 proj_dir 中的目录，在 git 工作树或目录副本构建完成后，会递归复制到 wt 处的快照中。wt 处的快照在上下文管理器退出后仍然存在，并且不会自动移除。

### 实际行为

正常执行时，生成器产生 `wt`，一个位于 `<temp_dir>/snapshot` 的目录，其中 `<temp_dir> = tempfile.mkdtemp(prefix="fm_agent_wt_<repo_name>_")` 和 `<repo_name>` 派生自 `proj_dir`。如果 `proj_dir` 是一个有 HEAD 提交的 git 仓库（`is_git` 为 true），则 `wt` 是一个指向新提交的分离工作树，该提交捕获了 `git add -A` 运行时的该工作树（已跟踪的修改 + 未跟踪文件），其中 `exclude` 中的目录通过 `git rm --cached` 从提交中移除。原始的 git 状态（`HEAD`、索引、工作树）保持不变。如果 `copy_excluded` 为 true，则每个存在于 `proj_dir` 但在 `wt` 中不存在的被排除目录，会作为未跟踪目录递归复制到 `wt` 中。如果 `proj_dir` 不是一个有 HEAD 的有效 git 仓库（`is_git` 为 false），则 `wt` 是 `proj_dir` 的普通副本（`exclude` 中的目录通过 `shutil.ignore_patterns` 跳过），并且如果 `copy_excluded`，随后将这些目录复制到 `wt` 中。`<temp_dir>` 在 yield 后仍然存在（不会自动删除）。`proj_dir` 未被修改。包含 `wt` 和清理指令的消息会打印到 stdout。异常执行时（yield 前发生异常），`proj_dir` 不变，`<temp_dir>` 存在但可能包含不完整的产物，`wt` 可能不存在或不完整。
形式化描述：
令 P = os.path.abspath(proj_dir)，R = os.path.basename(P.rstrip(os.sep)) 或 "repo"，B = tempfile.mkdtemp(prefix="fm_agent_wt_" + R + "_")，W = os.path.join(B, "snapshot")，G = (subprocess.run(["git", "-C", P, "rev-parse", "--verify", "HEAD"], check=True, capture_output=True, text=True) 未引发 CalledProcessError)。则结果满足：
  （正常产出 W） ∨ （引发异常 → 无产出）。
  若正常产出：
    G  
      （ 存在 I = os.path.join(B, "index")，它是一个有效的 git 索引
         tree = _git("write-tree", env=env) 的输出
         snap = _git("commit-tree", tree, "-p", "HEAD", "-m", "fm_agent snapshot", env=env) 的输出
        _git("worktree", "add", "--detach", W, snap) 成功
        P 的 git 状态（HEAD、索引、工作树）与进入时状态相同
         ∀ name ∈ exclude，令 S = os.path.join(P, name)，D = os.path.join(W, name)：
          （copy_excluded ∧ os.path.isdir(S) ∧ ¬os.path.exists(D) → D 是工作树创建后 shutil.copytree(S, D, symlinks=True) 的结果） ）
    ¬G
      （ W 是 shutil.copytree(P, W, ignore=shutil.ignore_patterns(*exclude), symlinks=True) 的结果
         ∀ name ∈ exclude：（copy_excluded ∧ os.path.isdir(os.path.join(P, name)) ∧ os.path.exists(os.path.join(W, name)) →
          shutil.copytree(os.path.join(P, name), os.path.join(W, name), symlinks=True) 在初始 copytree 后执行） ）
     产出后 B 存在，且 stdout 包含 W。
  若引发异常：
    P 及其所有内容与进入时状态相同 ∧ B 存在 ∧ （W 可能不存在或不完整）。

### 为什么会认为是 Bug

代码仅使用顶层的排除名称执行 'git rm --cached'，因此同名的嵌套目录/文件仍保留在提交中。规范要求“名称与 exclude 匹配的条目被排除”，这意味着需要排除所有深度下的此类条目。

### 如何违反规约

frozen_worktree() 仅使用顶层的排除名称执行 git rm --cached，因此同名的嵌套目录（如 testdata/fm_agent/）会留在提交中并泄漏到快照中。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-061"></a>
## FMA-MISMATCH-061 — `src--languages--codegraph-py--CodeGraphExtractor::get_call_edges`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-061](bug_list_v7_28_zh_filter.md#fma-mismatch-061)

### 预期行为

返回一个字典，将每个调用者 FQN（字符串）映射到一个非空的被调用者 FQN 集合（set[str]），涵盖在索引项目中给定语言的源文件中发现的所有直接调用关系。键和值均使用规范化 FQN，并以 :: 作为组件分隔符。调用边既包含函数调用边，也包含由类实例化关系合成的构造函数调用。FQN 身份通过 codegraph 节点 ID 解析，保留不同文件中同名函数的精确调用者/被调用者关联。当 lang_key 不是已识别语言或给定语言不存在调用边时，返回空字典。

### 实际行为

若未抛出异常，则：如果 _CG_LANG.get(lang_key) 得出一个非空列表 cg_langs，则该方法打开到 self._db 的连接，获取游标，计算 fqn_of = _node_fqn_map(cur, cg_langs)，然后构建这样一个映射 result：对于每个 edges.kind='calls' 且源语言在 cg_langs 中的 (src, tgt)，若 fqn_of[src] 和 fqn_of[tgt] 均不为 None，则 result[fqn_of[src]] 包含 fqn_of[tgt]；此外，如果存在 ctor_filter = _CONSTRUCTOR_FILTER.get(lang_key)，则对于每个来自第二个查询（edges.kind='instantiates'，源语言在 cg_langs 中，目标类包含与 ctor_filter 匹配的方法/函数）的 (src, ctor_id)，若 fqn_of[src] 和 fqn_of[ctor_id] 均不为 None，则 result[fqn_of[src]] 包含 fqn_of[ctor_id]。连接在返回前关闭。该方法返回 dict(result)。如果 _CG_LANG.get(lang_key) 得到假值，则该方法返回 {}，且无任何副作用。在所有情况下，self 保持未修改，self._db 不变，无资源泄漏。

### 为什么会认为是 Bug

代码会遗漏被调用者的 FQN 不在 fqn_of 中的调用边，而 fqn_of 仅覆盖所请求语言的节点。然而，规范要求所有在给定语言的源文件中发现的直接调用关系，包括对其他语言中定义的函数的调用。这将导致输出字典中缺失被调用者。

### 如何违反规约

从所请求语言调用其他语言中的函数的调用会被丢弃，因为 _node_fqn_map 仅映射所请求语言的节点，因此 fqn_of.get 对跨语言被调用者返回 None。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-070"></a>
## FMA-MISMATCH-070 — `src--languages--codegraph-py--try_codegraph_init`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `2`
- **原始详情：** [查看 FMA-MISMATCH-070](bug_list_v7_28_zh_filter.md#fma-mismatch-070)

### 预期行为

如果 force 为真，则在尝试构建新的索引之前，先移除位于 <proj_dir>/.codegraph/ 的任何既有 CodeGraph 索引目录。如果 force 为假且索引数据库 <proj_dir>/.codegraph/codegraph.db 已经存在，则函数立即返回而不修改文件系统。否则，函数以 proj_dir 为工作目录调用 'codegraph init' 子命令。函数永不抛出异常：若在系统 PATH 中找不到 codegraph 可执行文件，函数静默返回；若 'init' 子命令以非零状态码退出，则记录一条警告并正常返回，无错误。

### 实际行为

执行后，函数已尝试为 proj_dir 构建或重建 codegraph 索引。不会抛出异常；所有内部错误均被处理（缺少 codegraph 时静默返回，非零退出时发出警告）。具体效果取决于初始状态和 force 参数：
- 令 db_path = os.path.join(os.path.join(proj_dir, '.codegraph'), 'codegraph.db')。
- 令 E_before = 初始时 os.path.exists(db_path)。
- 令 CMD_EXIST 为真，当 codegraph 命令（由 `_codegraph_cmd()` 返回）存在且可执行，否则为假。
- 令 INIT_SUCCEED 为真，当子进程 `[cmd, 'init']` 运行并返回退出码 0，否则为假（包括命令缺失的情况）。
后置条件：
1. 若 E_before ∧ ¬force：函数立即返回。文件系统不发生变化。不打印任何输出。db_path 仍存在。
2. 若 (E_before ∧ force) ∨ ¬E_before：
   - 打印一条消息：
       * 若 E_before ∧ force：打印 "[Pipeline] Rebuilding codegraph index for current working tree..."，并将包含 db_path 的目录删除（通过 `shutil.rmtree` 调用 `ignore_errors=True` 删除 codegraph_dir）。
       * 若 ¬E_before：打印 "[Pipeline] Building codegraph index..."，不执行事先删除。
   - 调用函数 `_warn_on_codegraph_version_mismatch(cmd)`，该函数可能发出版本不匹配警告。
   - 然后尝试 `subprocess.run([cmd, 'init'], cwd=proj_dir, capture_output=True, text=True)`。
   - 若 CMD_EXIST 为假（FileNotFoundError），函数静默返回；不产生进一步输出。
   - 若 CMD_EXIST：
       * 若 INIT_SUCCEED：打印 "[Pipeline] codegraph index built."。
       * 若 ¬INIT_SUCCEED：记录一条警告，包含 stderr 的前 300 个字符。
正式地，db_path 的最终存在性由下式给出：
   exists(db_path) ⇔ (E_before ∧ ¬force) ∨ (INIT_SUCCEED ∧ CMD_EXIST)。
特别地，以下情况下数据库文件保证在调用后存在：
   - 数据库原本已存在且 force 为假，或
   - codegraph 命令可用且其 `init` 子命令成功（无论之前目录是否被删除）。
所有打印输出在 stdout 上；警告通过 logging 模块发出。

### 为什么会认为是 Bug

规范要求当 force 为 True 时，在构建之前应移除任何既有的 `.codegraph/` 目录。而代码仅在 `codegraph.db` 存在时（第19行）才删除目录。如果 `.codegraph/` 存在但没有 `codegraph.db`，代码不会将其删除，从而违反规范。

### 如何违反规约

当 .codegraph/ 目录存在但内部没有 codegraph.db 时，force=True 不会将其删除（规范要求删除任何既有目录）。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-084"></a>
## FMA-MISMATCH-084 — `src--languages--erlang-py--ElpClient::_send`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-084](bug_list_v7_28_zh_filter.md#fma-mismatch-084)

### 预期行为

如果服务器进程未运行或其 stdin 流不可写，则引发 RuntimeError。否则：消息以 UTF-8 JSON 字节序列序列化，使用最小分隔符（逗号和冒号之间无空白），且不对非 ASCII 字符进行 ASCII 转义；序列化后的字节序列前面加上 LSP Content-Length 头（Content-Length: <octet_count>\r\n\r\n），构成完整帧；在独占获取写锁的情况下将完整帧写入服务器进程的 stdin 并刷新流，确保帧作为单个原子单元发送到服务器。成功发送后返回 None。当 stdin 写入或 flush 操作失败时引发 OSError（或其子类，如 BrokenPipeError）。

### 实际行为

如果函数未引发异常，则 self._proc 和 self._proc.stdin 均不为 None，并且由 `message` 构造的 JSON-RPC 帧（UTF-8 编码的 JSON，确保非 ASCII 字符并以紧凑分隔符）已在 `with self._write_lock` 块内写入并刷新到服务器的 stdin，因此锁现已释放。帧内容确切为 `Content-Length: <payload_length>\r\n\r\n<payload_utf8>`。message 参数保持不变。如果函数引发 `RuntimeError`，则 `self._proc is None or self._proc.stdin is None` 为真，未写入任何帧，锁不受影响，服务器 stdin 未被修改。形式逻辑：(¬Exception ⇒ (self._proc ≠ None ∧ self._proc.stdin ≠ None) ∧ sent(frame) ∧ lock_released(self._write_lock)) ∧ (Exception(RuntimeError) ⇒ (self._proc = None ∨ self._proc.stdin = None) ∧ ¬sent(frame) ∧ lock_unacquired(self._write_lock) ∧ stdin_unchanged(self._proc.stdin))。

### 为什么会认为是 Bug

规范要求当服务器进程未运行或其 stdin 流不可写时引发 RuntimeError。代码仅检查 None 值，遗漏了进程已退出但 Popen 对象和 stdin 仍然存在的情况。在这种情况下，代码引发 OSError 而非 RuntimeError，违反了契约。

### 如何违反规约

代码仅检查 self._proc is None，遗漏了进程已退出但 Popen 对象仍然存在的情况；向已失效的 stdin 写入会引发 BrokenPipeError 而非 RuntimeError。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-086"></a>
## FMA-MISMATCH-086 — `src--languages--erlang-py--ElpClient::close`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `2`
- **原始详情：** [查看 FMA-MISMATCH-086](bug_list_v7_28_zh_filter.md#fma-mismatch-086)

### 预期行为

由 self._proc 引用的 ELP 子进程被终止，其 stdin 和 stdout 管道被关闭。self._proc 被设置为 None。后台读取线程 self._reader 被停止，不再从子进程 stdout 消费。与该子进程关联的所有 OS 级资源（管道、进程句柄）均被释放。

### 实际行为

执行后，self._proc 为 None。原始子进程对象（如果存在）已被正确处理：如果它仍在运行，会尝试优雅地关闭（通过 request('shutdown')、notify('exit') 以及带超时的等待），必要时会终止或杀死；最终该进程不再运行，其标准输入和输出流已被关闭（关闭过程中的任何 OSError 被捕获）。self._reader 属性保持不变，仍引用一个活跃的后台读取线程。该方法没有未处理的异常传播。形式化表述：(self._proc = None) ∧ (∀ s ∈ { proc.stdin, proc.stdout } : s 已关闭) ∧ (self._reader 是活跃线程) ∧（最初引用的子进程不再运行，其终止已被正确等待）。

### 为什么会认为是 Bug

规范要求后台读取线程 self._reader 被停止，不再从子进程 stdout 消费。代码仅终止子进程并关闭其流，使 self._reader 未被触及且仍活跃，这违反了规范。

### 如何违反规约

ElpClient::close() 终止子进程并关闭其流，但从未停止、join 或将后台读取线程 self._reader 设置为 None，使其保持存活并仍引用已关闭的子进程 stdout。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-091"></a>
## FMA-MISMATCH-091 — `src--languages--erlang-py--_SourceIndex::build`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-091](bug_list_v7_28_zh_filter.md#fma-mismatch-091)

### 预期行为

返回一个 _SourceIndex 实例，该实例按行边界索引源码。返回的实例包含完整的源码文本逐字副本（保留所有行结束符）以及一个从零开始的字节偏移量列表，其中每个偏移量是每一行在源码中的起始位置。第一个偏移量始终为 0。后续偏移量单调递增——每个偏移量等于其前面所有行（包括它们的行结束符）的字节长度之和。偏移量的数量等于源码中由换行符分隔的行数。返回的实例使调用者能够将任何有效的行索引和字符位置映射到源码中对应的字节偏移量，并提取从起始字节偏移量（含）到结束字节偏移量（不含）的连续子串。

### 实际行为

返回一个 _SourceIndex 实例 r，满足 r.source == source，r.lines == source.splitlines(keepends=True)，且对于所有 i 在 0..len(r.lines)-1： r.line_offsets[i] == sum(len(r.lines[j]) for j in range(i))。

### 为什么会认为是 Bug

规范明确要求使用指向源文本的字节偏移量，但代码使用了 len(line)，该函数返回 Unicode 码位（字符）的数量。对于包含多字节字符（如非 ASCII 字符）的字符串，字符长度与字节长度不同，导致字节偏移量不正确。反例使用包含双字节字符 '' 的字符串演示了这一点。

### 如何违反规约

多字节 UTF-8 字符 (é) 导致 len() 返回字符数 (3) 而非字节长度 (4)，在 line_offsets 中产生不正确的字节偏移量。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-092"></a>
## FMA-MISMATCH-092 — `src--languages--erlang-py--_SourceIndex::position_to_offset`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-092](bug_list_v7_28_zh_filter.md#fma-mismatch-092)

### 预期行为

返回一个在闭区间 [0, len(self.source)] 内的整数，表示与给定位置对应的 self.source 中的字节偏移量。当行号等于或超过已索引行数时，返回 len(self.source)。当 UTF-16 代码单元列偏移量达到或超过目标行上 UTF-16 代码单元的数量时，返回该行之后第一个字节的字节偏移量。Unicode 码点高于 U+FFFF 的字符将 UTF-16 代码单元列偏移量增加 2；码点等于或低于 U+FFFF 的字符将其增加 1。对于任意两个位置 p1 和 p2，如果 p1 在相对于已索引源的文档顺序中不晚于 p2，则 position_to_offset(self, p1) <= position_to_offset(self, p2)。

### 实际行为

方法返回一个整数偏移量 r，且无副作用。令 line_number = max(0, int(position.get('line', 0))) 且 utf16_target = max(0, int(position.get('character', 0)))。若 line_number >= len(self.lines)，则 r = len(self.source)。否则，令 base = self.line_offsets[line_number] 且 L = self.lines[line_number]。定义 unit(c) = 2 若 ord(c) > 0xFFFF，否则 1。令 index = max { k  [0, len(L)] | _{i=0}^{k-1} unit(L[i]) <= utf16_target }。则 r = base + index。从位置到偏移量的映射在行上使用基于字符的索引，加上一个字节偏移量基址，如果源包含多字节字符，结果可能并不对应真实的字节偏移量。

### 为什么会认为是 Bug

代码将偏移量视为加到字节偏移量基址上的基于字符的索引。只有当所有字符都是单字节（ASCII）时，才能得到正确的字节偏移量。存在多字节字符时，返回值不是 self.source 中所需的字节偏移量。对于高于 U+FFFF 的字符，例如 U+1F600 ('')，len(line)=1，但其字节长度为 4，因此 base + index = 0 + 1 = 1，违反了规范要求的 4。

### 如何违反规约

使用源 '😀\n' 和位置 {line: 0, character: 2} 调用 _position_to_offset；返回字符索引 1 而非字节偏移量 4，因为对于多字节 UTF-8 字符，index += 1 按字符计数而非字节计数。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-157"></a>
## FMA-MISMATCH-157 — `src--llm_client-py--_matches_inject_target`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-157](bug_list_v7_28_zh_filter.md#fma-mismatch-157)

### 预期行为

当判定 url 属于 target 的地址空间时返回 True；否则返回 False。当 target 以 'http://' 或 'https://' 开头（不区分大小写）时，需要 url 以 target 作为大小写敏感的前缀才认为属于。当 target 没有 scheme 时，需要从 url 中提取的主机名组件与 target 完全相等，或者以 '.' 加上 target 结尾（表示子域名）才认为属于。当无法从 url 中提取主机名时返回 False。

### 实际行为

该函数返回一个布尔值。如果 `target` 的小写版本以 'http://' 或 'https://' 开头，则当 `True` 为真时函数返回 `url.startswith(target)`，否则返回 `False`。否则，函数尝试使用 `url` 从 `urllib.parse.urlparse` 解析主机名。如果解析过程中发生异常，则返回 `False`。如果解析成功，则提取 `host = urlparse(url).hostname or ''`（如果主机名为 `None` 则为空字符串）。然后，如果 `True` 或 `host == target` 则返回 `host.endswith('.' + target)`，否则返回 `False`。不修改其他状态。形式化定义为，设 low = target.lower()；scheme = low.startswith('http://') or low.startswith('https://')；则返回值 r 满足：r = ( scheme 且 url.startswith(target) ) 或 ( 非 scheme 且 [如果没有异常且 host = (urlparse(url).hostname or '') 则 (host = target 或 host.endsWith('.' + target)) 否则 False] )。

### 为什么会认为是 Bug

主机名不区分大小写，但代码执行的是大小写敏感的相等性检查。当 target 为 "example.com"（无 scheme）且 url 为 "http://EXAMPLE.COM" 时，urllib.parse.urlparse(url).hostname 返回 "EXAMPLE.COM"。然后代码比较 "EXAMPLE.COM" == "example.com"（False）以及 "EXAMPLE.COM".endswith(".example.com")（False），返回 False。根据规约，主机名 "EXAMPLE.COM" 属于 "example.com" 的地址空间，因此函数应返回 True。

### 如何违反规约

当 target 包含大写 ASCII 字母时（例如，'EXAMPLE.COM' 与 urlparse 得到的主机名 'example.com' 比较），第 8 行的大小写敏感 host == target 比较会失败，这违反了 DNS 不区分大小写的规则。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-165"></a>
## FMA-MISMATCH-165 — `src--opencode_trace-py--_opencode_env`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-165](bug_list_v7_28_zh_filter.md#fma-mismatch-165)

### 预期行为

返回一个字符串键到字符串值的字典，适合用作子进程环境。返回的字典包含当前进程环境的每一个条目。它包含一个 TRACE_DIR 条目，其值为一个绝对文件系统路径，该路径指定一个在调用后存在于文件系统上、且位于以 work_dir 为根的 trace 结构下的目录。它包含一个 TRACE_FILENAME 条目，其值等于 event_id。它包含一个 PWD 条目，其值为直接包含 work_dir 的目录的绝对路径。当所有已配置的 LLM API key、base URL、model name 和 provider 均可用（即 provider 配置完整）时，返回的字典额外包含一个 LLM_API_KEY 条目，其值为配置的 API key，以及一个 OPENCODE_CONFIG_CONTENT 条目，其值为一个有效的 JSON 字符串，编码一个字典，该字典的顶级键是环境中任何已存在的 OPENCODE_CONFIG_CONTENT 值的顶级键与解析的 provider 配置的顶级键的并集，其中 provider 定义的键覆盖同键的预先存在的条目；当 provider 配置不完整时，既不会出现 LLM_API_KEY，也不会出现修改过的 OPENCODE_CONFIG_CONTENT。

### 实际行为

在正常完成时（即函数返回一个字典而没有引发异常），以下成立：
1. **文件系统副作用**  
   位于  
     `td = os.path.abspath(os.path.join(_trace_dir(work_dir), 'opencode'))`  
   的目录存在。 如果在调用前不存在，则被创建。
2. **返回的环境字典**  
   设 `E0` 是函数入口时对 `os.environ` 的快照。 返回的映射 `env` 满足：
   - `env['TRACE_DIR'] = td`
   - `env['TRACE_FILENAME'] = event_id`
   - `env['PWD'] = os.path.dirname(os.path.abspath(work_dir))`
   - 如果 `cfg = _opencode_provider_config()` 不是 `None`，那么：
        * `env['LLM_API_KEY'] = settings.llm.api_key`
        * 令 `raw = E0.get('OPENCODE_CONFIG_CONTENT')`。 如果 `raw` 是一个可以被 `json.loads` 解析为字典的字符串，那么 `base = that dictionary`；否则 `base = {}`。 然后  
          `env['OPENCODE_CONFIG_CONTENT'] = json.dumps(_deep_merge(base, cfg))`。
     否则（当 `cfg` 为 `None` 时），`'LLM_API_KEY'` 和 `'OPENCODE_CONFIG_CONTENT'` 在 `env` 中的值正好是 `E0` 中存在的值（如果有的话）。
   - 对于 `k` 中存在的每一个其他键 `E0`，`env[k] = E0[k]`。 `env` 的键的集合正好是 `keys(E0)  {'TRACE_DIR','TRACE_FILENAME','PWD'}  ({'LLM_API_KEY','OPENCODE_CONFIG_CONTENT'} if cfg  None)`，没有额外的键。
3. **没有其他可观察的状态变化**  
   除了目录创建，文件系统没有变化；没有网络或其他副作用发生。
**形式化逻辑**（针对返回值与文件系统表达）：
令 `fs` 为调用后的文件系统状态。 后置条件 `Post(env, fs)` 成立当且仅当：
```
 td, base, raw, cfg :
   td = abspath(join(_trace_dir(work_dir), 'opencode'))
  directory_exists(td, fs)
  cfg = _opencode_provider_config()
  env = E0  {
        'TRACE_DIR': td,
        'TRACE_FILENAME': event_id,
        'PWD': dirname(abspath(work_dir))
     }
      ( if cfg  None then {
            'LLM_API_KEY': settings.llm.api_key,
            'OPENCODE_CONFIG_CONTENT': json.dumps(_deep_merge(base, cfg))
         } else  )
  ( if cfg  None then
        raw = E0.get('OPENCODE_CONFIG_CONTENT')
         ( if (raw is str  json.loads(raw) succeeds  the result is a dict) then
               base = that dict
            else
               base = {}
          )
     else true
   )
```
（此处 `` 表示映射的函数覆盖：对于给定的基础映射 `M` 和更新集合 `U`，`M  U` 将每个键 `k` 映射到 `U[k]`，如果 `k  dom(U)` 为真，否则映射到 `M[k]`。）

### 为什么会认为是 Bug

规范指出“provider定义的键覆盖同键的预先存在的条目”（即浅覆盖）。代码使用了 _deep_merge，它会递归合并嵌套字典，导致应被替换的预先存在的嵌套键仍然存留。在一个 OPENCODE_CONFIG_CONTENT 包含的嵌套键也出现在 provider 配置中的具体环境中，会暴露该差异。

### 如何违反规约

预先存在的 OPENCODE_CONFIG_CONTENT 含有嵌套的 provider 键：deep_merge 保留了应按照规范被 provider 配置覆盖的现有嵌套键（例如 'plugins'）。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-188"></a>
## FMA-MISMATCH-188 — `src--generate_batch_prompts-py--main`

- **原分类：** **契约不确定**
- **Validator：** `not_confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-188](bug_list_v7_28_zh_filter.md#fma-mismatch-188)

### 预期行为

返回 0。在 dry-run 模式下：将批处理计划（阶段、层范围、函数/批处理计数及每个批处理的详细信息）打印到标准输出，而不写入任何文件。在非 dry-run 模式下：在输出目录下写入批处理提示 .txt 文件，为指定阶段和层范围内的每个函数批处理生成一个文件，每个文件都包含该批处理中每个函数的代码、签名和被调用方规格；写入一个 manifest.json 文件，描述所有批处理（在恢复时包括已经编写了规格的函数）；从输出目录中清除不属于本次运行的过期批处理文件。在恢复时，那些 .spec.json 和 .info.json 都已经准备好的函数被排除在提示生成之外。若 batch_size 不是严格正数，或者请求的层范围超出 [0, total_layers - 1]，则引发 ValueError。

### 实际行为

若 args.batch_size <= 0，则引发 ValueError，消息为 "--batch-size must be > 0"，且不再执行后续语句。否则，如果在读取 topdown_layers.json 并解析层规格后，出现 start_layer < 0 或 end_layer >= total_layers 的情况，则引发 ValueError，消息为 "layer range {args.layers} out of bounds [0, {total_layers - 1}]"，且不再进行后续的赋值。否则（正常终止）：args 已定义，其所有属性反映了命令行，且 args.batch_size > 0；work_dir 是解析到 fm_agent/ 工作目录（即包含本脚本的目录的父目录）的一个 Path 对象；repo_root 为 work_dir.parent；fm_agent_prefix 是从 repo_root 到 work_dir 的相对路径字符串，后跟 '/'；phases_json 是 phases.json 解析后的字典，且 project = phases_json['project']；languages 和 exts 是 phases_json 中的列表值（若缺失则默认为 []）；ext_to_lang 是一个字典，将 exts 中的每一个扩展名（小写并去除前缀点）映射到 languages 中对应的语言；topdown_path 是请求阶段的 topdown_layers.json 的路径，topdown 是其解析后的字典，layers = topdown.get('layers', [])，且 total_layers = len(layers)；start_layer 和 end_layer 是从解析 args.layers 得到的包含性边界，并满足 0 ≤ start_layer ≤ end_layer < total_layers；output_dir 是一个 Path 对象，若 args.output_dir 是真值，则等于 Path(args.output_dir)，否则为 work_dir / 'spec_prompts' / f'batch_prompts_{project}_phase{args.phase:02d}'；func_to_layer 将所有层中的每个函数名映射到其层索引（如果文件路径包含 fm_agent_prefix，则先移除该前缀）；all_funcs 将同样的函数名映射到其函数元数据字典（可能修改了 file 字段）；manifest_batches、total_functions、skipped_functions、batch_index、write_targets 分别初始化为空列表、0、0、0 和空列表。除读取两个 JSON 文件外，不发生其他文件系统副作用。

### 为什么会认为是 Bug

代码块在初始化后（第 40 行）结束。对于通过所有验证的有效输入，代码不再做任何事，这违反了要求生成文件、创建清单、清理过期文件以及 dry-run 输出的规范。任何 batch_size > 0 且层规格在范围内的合规输入都会导致完全缺少所需的行为。

### 如何违反规约

逻辑验证在第 40 行错误地截断了分析；main() 有 138 行，包含了完整的批处理生成逻辑。

### 判读建议

**优先复核，不建议立即修改实现。** Validator 未确认原始结论，应先修正或重跑 probe，并确认反例满足函数前置条件；只有差异可稳定复现且真实调用链可达时，才进入修复队列。

---

<a id="review-202"></a>
## FMA-MISMATCH-202 — `src--parser-py--format_info_for_reasoner`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-202](bug_list_v7_28_zh_filter.md#fma-mismatch-202)

### 预期行为

返回一个 FunctionSpecMap，其中包含输入列表中每个被调用者对应的一项。每一项将该被调用者的“name”值映射为一个两行字符串，格式为“前置条件：<pre_condition>\n后置条件：<post_condition>”。返回的 FunctionSpecMap 的 signatures 属性是一个字典，将每个被调用者的“name”值映射到其“signature”值。当输入列表为空时，返回一个空的 FunctionSpecMap（不包含任何项且 signatures 字典为空）。

### 实际行为

函数返回一个新创建的 FunctionSpecMap 对象。设 callees = info['callees']（一个字典列表，每个字典包含键 'name'、'signature'、'pre_condition'、'post_condition'）。对 callees 中的每个 d，定义 name = d['name']，sig = d['signature']，spec_str = '前置条件：' + d['pre_condition'] + '\n后置条件：' + d['post_condition']。生成的 FunctionSpecMap 存储：对每个不同的 name，映射 name → spec_str 和 name → sig 取自 callees 迭代顺序中该 name 的最后一次出现。如果 callees 为空，映射中不含任何项。不抛出异常，不修改外部状态。

### 为什么会认为是 Bug

规范要求输入列表中的每个被调用者对应一项，但代码使用以 name 为键的映射并覆盖重复项。对于存在两个都名为 'foo' 的被调用者的反例，生成的 FunctionSpecMap 只有一项（第二个被调用者的 spec 和 signature），而不是按要求为每个被调用者保留一项。

### 如何违反规约

两个具有相同名称 'foo' 的被调用者导致基于字典的 FunctionSpecMap 覆盖了第一个被调用者的条目，返回 1 项而非规范要求的 2 项。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-218"></a>
## FMA-MISMATCH-218 — `src--incremental_reasoner-py--_codegraph_legacy_coverage`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；尝试次数 `1`
- **原始详情：** [查看 FMA-MISMATCH-218](bug_list_v7_28_zh_filter.md#fma-mismatch-218)

### 预期行为

返回一个字典，其键为 file_languages 中列出的文件的规范化相对路径（针对 proj_dir 进行相对化处理并执行大小写规范化），其值为布尔值。对于在 proj_dir 下对应的磁盘路径不存在的文件，值为 True。对于已存在的文件，当且仅当旧版提取器根据该文件的语言键产生的有序 (func_name, source) 元组序列是 CodeGraph 中针对该文件的条目的有序子序列时（两个条目匹配的条件是：它们具有相同的无限定函数名，且经过行结束符规范化后其源代码文本完全相同），并且每个匹配的 CodeGraph 条目出现的位置索引都严格大于前一次匹配的位置索引，值才为 True。当有序子序列条件不满足时（即至少存在一个旧版发现的函数在所需顺序下找不到匹配的 CodeGraph 条目），值为 False，并通过日志系统发出一个识别出未匹配函数名及其文件路径的警告。该函数不对文件系统做任何修改。

### 实际行为

该函数返回一个字典 `coverage`，其中针对输入 `rel_path` 中的每个 `file_languages` 包含一个键值对。对于给定 `rel_path` 及其关联的语言键 `lang_key`，令 `rel_key = _normalized_relative_path(proj_dir, rel_path)` 和 `abs_path = os.path.join(proj_dir, rel_path)` 分别表示相关值。如果 `os.path.exists(abs_path)` 为 False，则 `coverage[rel_key]` 为 `True`。否则，令 `legacy_funcs` 为 `(name, source)` 返回的 `extract_functions_from_file(abs_path, lang_key)` 元组列表，令 `codegraph_items` 为 `(identifier, source)` 中按字典项顺序排列的 `codegraph_functions.get(rel_key, {})` 对列表。当且仅当存在一个严格递增的整数序列 `coverage[rel_key]`（其中 `True`）且每个 `j_0 < j_1 < ... < j_{L-1}` 都是 `L = len(legacy_funcs)` 的有效索引，使得对于每个 `j_i` 有：`codegraph_items` 且 `i` 时，值 `_bare_function_name(codegraph_items[j_i][0]) == _bare_function_name(legacy_funcs[i][0])` 才为 `_normalized_function_source(codegraph_items[j_i][1]) == _normalized_function_source(legacy_funcs[i][1])`。如果不存在这样的序列，`coverage[rel_key]` 为 `False`。对 `file_languages` 的迭代顺序决定了插入 `coverage` 的顺序，但除了 Python 字典原生的插入顺序（Python 3.7+）外，不保证返回字典的任何进一步排序。

### 为什么会认为是 Bug

代码使用 _bare_function_name 来比较标识符，该函数会去除末尾的去重后缀（例如 '_1'）。规范要求“无限定函数名”仅指去除了限定符的名称，应保留旧版提取器添加的去重后缀。因此，旧版名称如 'foo_1' 和 CodeGraph 名称如 'foo()' 在代码中被视为相等（二者均变为 'foo'），但根据规范应被视为不相等，从而导致在需要 False 判定时错误地给出 True 判定。

### 如何违反规约

_bare_function_name 会去除末尾的去重后缀（例如 '_1'），导致旧版名称 'my_func_1' 错误地匹配 CodeGraph 名称 'my_func'，而规范要求将它们视为不同。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-222"></a>
## FMA-MISMATCH-222 — `src--incremental_reasoner-py--_collect_changed_functions::_is_workspace_file`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-222](bug_list_v7_28_zh_filter.md#fma-mismatch-222)

### 预期行为

返回 True 当 rel_path 在将所有反斜杠替换为正斜杠后，等于精确字符串 "fm_agent" 或以 "fm_agent/" 为前缀。在所有其他情况下返回 False，包括 rel_path 为空、仅包含 fm_agent 目录名但带有额外的路径组件且不构成 fm_agent/ 下的后代路径，或表示归一化路径落在 fm_agent/ 工作空间树之外的文件。

### 实际行为

函数 _is_workspace_file 在 rel_path 的归一化版本（通过将所有反斜杠 '\' 替换为正斜杠 '/' 得到）等于字符串 'fm_agent' 或以 'fm_agent/' 开头时返回 True；否则返回 False。该函数无副作用且不修改 rel_path。形式化表示：∀ rel_path ∈ Strings, _is_workspace_file(rel_path) ⇔ (rel_path.replace('\\', '/') = 'fm_agent') ∨ (rel_path.replace('\\', '/').startswith('fm_agent/')).

### 为什么会认为是 Bug

代码在替换反斜杠后使用了简单的字符串前缀检查。对于输入 'fm_agent/..'，归一化结果为 'fm_agent/..'，它确实以 'fm_agent/' 开头，因此代码返回 True。然而，规范要求在路径不构成 fm_agent/ 下的后代路径时返回 False，而 '..' 会逃逸出目录，使之成为非后代路径。单纯的字符串前缀无法检测此类逃逸，违反了规范。

### 如何违反规约

以 fm_agent/ 开头且包含 '..' 组件的路径（例如 fm_agent/..）能通过简单的 startswith 检查，但实际上会逃逸出工作空间目录。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-227"></a>
## FMA-MISMATCH-227 — `src--incremental_reasoner-py--_llm_select_json`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-227](bug_list_v7_28_zh_filter.md#fma-mismatch-227)

### 预期行为

将 prompt_content 发送到配置的 LLM。当 LLM 产生可解析为 JSON、符合 schema_description 并通过 validator 的输出时，返回解析并验证后的结果。当 LLM 未产生任何输出、输出无法解析为 JSON、输出不符合 schema_description 或输出未通过 validator 时，返回 None。交互过程在 work_dir 下进行追踪，并以 stage 和 trace_meta 作为标识标签。在返回 None 时，会生成一条记录 stage 的 error 级别日志条目。

### 实际行为

在 _llm_select_json 的执行之后，函数要么以返回值 v 正常终止，要么抛出异常并传播给调用者。
正常终止的后置条件：
(1) (v 为 None)  (v 不为 None  validator(v)[0] = True  v 是一个符合 schema_description 的 JSON 解析对象)。
(2) 目录 os.path.join(work_dir, 'trace') 中包含了来自 LLM 交互的追踪文件，并记录了元数据 {'stage': stage, 'summary': 'LLM ' + stage, **trace_meta}。
(3) 如果 v 为 None，则会发出包含 stage 的 logging.error 消息。
异常终止（由 _llm_json_call 抛出的异常）：异常传播；没有返回值，且对追踪数据的完整性或存在性不作任何保证。

### 为什么会认为是 Bug

规范声明，当 LLM 未产生有效且符合规范的 JSON 结果时，函数始终返回 None；其中并未规定抛出异常。代码将 _llm_json_call 抛出的任何异常（例如网络或客户端错误）直接传播给调用者，违反了预期契约。

### 如何违反规约

来自 _llm_json_call 的异常（例如网络或客户端错误）传播给调用者，而非如规范要求那样被捕获并返回 None。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-238"></a>
## FMA-MISMATCH-238 — `src--incremental_reasoner-py--_update_specs_for_intent::_plan_spec_update`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-238](bug_list_v7_28_zh_filter.md#fma-mismatch-238)

### 预期行为

当以下任一条件成立时返回 None：(a) fqn 在 file_map 中无条目或映射的文件在磁盘上不存在，(b) 文件扩展名在 EXT_TO_LANG 中对应不到任何已识别的语言，或 (c) 函数已有有效规范且该规范在 developer_intent 下仍然正确。否则返回一个计划字典，包含：'fqn'（原样 FQN）、'fpath'（绝对文件路径）、'spec_dict'（一个包含 'signature'、'pre_condition'、'post_condition' 键的字典，描述函数的预期行为契约）、'info_dict'（一个包含 'callees' 键的字典，列出预期的被调用者契约）、'info_updated'（一个布尔值，当被调用者信息字典已生成或与先前版本相比发生了变化时为 true）、'updated_callees'（一个被调用者 FQN 字符串列表，其预期契约与上一次运行不同）。返回的字典是纯数据记录 — 此函数不会写入或修改任何文件。

### 实际行为

`_plan_spec_update` 完成后，以下之一成立：
1. 函数返回 `None`，因为：
   - `file_map.get(fqn)` 为 `None` 或相应的路径不存在或不是常规文件，或
   - 文件扩展名无法通过 `EXT_TO_LANG` 映射到语言键，或
   - 在读取源代码以及可能已存在的 `.spec.json`/`.info.json` 文件后，调用 `_opencode_generate_spec`（当没有先前规范时）或 `_llm_check_spec_update`（当先前规范和 info 存在时）产生 falsy 结果或 `result.get('spec_updated')` 不是 `True` 的结果，或
   - `result.get('new_spec')` 不是字典。
2. 函数返回一个字典 `plan`，包含以下键：
   - `'fqn'`：输入的 `fqn`，
   - `'fpath'`：解析后的源文件路径，
   - `'spec_dict'`：`_normalize_spec_dict(new_spec)` 的结果，其中 `new_spec` 是更新后的规范字典，
   - `'info_dict'`：`_normalize_info_dict(new_info)` 的结果，其中 `new_info` 是（可能是新生成的）被调用者信息字典，按以下方式确定：
      * 如果 `old_info` 为 `None`，则 `new_info = result.get('new_info')`（如果它是字典），否则 `{'callees': []}`，并且 `info_updated = True`；
      * 否则 `info_updated = bool(result.get('info_updated'))`；如果 `info_updated` 为 true，则 `new_info = result.get('new_info')`（如果它是字典），否则 `new_info = old_info`；如果 `info_updated` 为 false，则 `new_info = old_info`。
   - `'info_updated'`：按上述确定的布尔值，
   - `'updated_callees'`：`result.get('updated_callees')` 或 `[]`。
3. 异常（例如，读取源文件时抛出 `OSError`，或由 `_collect_caller_context`、LLM 函数或规范化助手抛出的任何异常）被引发且未被捕获，传播到调用者。在这种情况下不会产生返回值。
该函数仅执行读取 I/O；它不会写入文件系统或修改全局映射 `file_map`、`callers_map`、`callees_map`、`edge_aliases_map`、`EXT_TO_LANG`、`proj_dir`、`work_dir` 或 `developer_intent`。

### 为什么会认为是 Bug

规范要求仅当条件 (a)、(b) 或 (c) 成立时返回 None。当没有先前规范时，条件 (c) 不适用，且 (a) 和 (b) 为 false。因此函数必须返回一个计划字典。代码因为 result 为 falsy 而返回 None，违反了规范。

### 如何违反规约

当 _opencode_generate_spec 对一个没有先前规范的函数返回 falsy 值时，_plan_spec_update 返回 None 而不是计划字典，从而静默地跳过了该函数。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-239"></a>
## FMA-MISMATCH-239 — `src--incremental_reasoner-py--_update_specs_for_intent::_reconcile_caller`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；尝试次数 `1`
- **原始详情：** [查看 FMA-MISMATCH-239](bug_list_v7_28_zh_filter.md#fma-mismatch-239)

### 预期行为

updates 中的每个 (callee_name, callee_new_spec) 对被依次处理。对每个对，判断调用方的现有 .info.json 中的 callee 条目是否需要修订以与 callee_new_spec 保持一致——该判断考虑调用方的源代码、当前 .info.json 以及被调用方的新规约。当需要修订时，调用方的整个 .info.json 将被替换为一个协调后的版本，其中 callee 条目与 callee_new_spec 以及所有之前已协调的 callee 条目一致。当任何对都不需要修订时，.info.json 保持不变。如果至少发生了一次 .info.json 替换，则返回调用方绝对源文件路径的字符串；当调用方源文件不存在、无法确定其编程语言、其 .info.json 不可读或未应用任何替换时，返回 None。

### 实际行为

函数正常完成（即没有引发异常）后，以下情况成立：
设 cpath = file_map.get(caller_fqn)。如果 cpath 不是指向现有文件的非空字符串，或语言无法确定（clang 为假值），则函数返回 None，且辅助文件 cpath + '.info.json' 未被修改。
否则，设 n = len(updates)。对于 i 从 0 到 n-1，令 (cname_i, cspec_i) = updates[i]。在第 i 次迭代期间：
  - 从 cpath 读取源代码。如果发生 OSError，函数终止并抛出该异常。
  - 加载辅助信息。如果发生 OSError 或 JSONDecodeError，迭代继续到 i+1。
  - cresult_i = _llm_check_caller_info_update(...)。如果 cresult_i 为 None 或 cresult_i.get('info_updated') 不为真，继续。
  - c_new_info_i = cresult_i.get('new_info')；如果不是 isinstance(..., dict)，继续。
  - 辅助文件被 _normalize_info_dict(c_new_info_i) 的输出覆盖。如果发生 OSError，函数终止并抛出该异常。
  - changed 被设为 True。
定义 success_i 当且仅当在第 i 次迭代写入之前没有引发异常且 cresult_i 不是 None 且 cresult_i.info_updated 为真且 cresult_i.new_info 是一个 dict。如果存在任意 i 满足 success_i，则 changed = True；否则 changed = False。
正常返回值 = 若 changed 为真则为 cpath，否则为 None。
正常返回后辅助文件的状态：
  - 如果 changed = False：文件未更改（与调用前状态相同，除了临时文件系统元数据）。
  - 如果 changed = True：令 j = max{ i | success_i }。文件包含 _normalize_info_dict(c_new_info_j) 的 JSON 序列化输出。其结构是一个字典，具有单个键 'callees'，其值为一个字典列表，每个字典按顺序包含键 'name'、'signature'、'pre_condition'、'post_condition'，缺失字段用空字符串填充，多余键被移除。
如果引发任何异常（例如 OSError，或来自 _llm_check_caller_info_update），函数不会正常返回，且辅助文件可能处于任意状态（损坏、部分写入或未更改）。
正式后置条件（对于正常终止）：
  exists cpath = file_map.get(caller_fqn), cext, clang .
    ( (cpath 不是有效文件路径 ∨ 非 clang) → 返回 None ∧ sidecar_unchanged(cpath) )
    ∧ ( valid(cpath) ∧ clang →
        let changed = ( ∃ i ∈ 0..n-1 . success_i) in
        return = (cpath if changed else None) ∧
        ( changed → j = max{ i | success_i } .
            sidecar_content(cpath) = serialize(_normalize_info_dict(c_new_info_j)) ) ∧
        ( ¬changed → sidecar_unchanged(cpath) ) )
  其中 success_i ↔ (no_exception_until_write(i) ∧ cresult_i ≠ None ∧ cresult_i.info_updated ∧ typeof(cresult_i.new_info) = dict)

### 为什么会认为是 Bug

代码用 LLM 的输出逐字替换整个辅助文件，但 LLM 的后置条件并不保证其保留所有现有的 callee 条目。这可能导致根据规约应保持不变 callee 信息的丢失。

### 如何违反规约

当 _llm_check_caller_info_update 返回的 new_info 字典省略了不相关的 callee 条目时，_reconcile_caller 会用 LLM 的输出逐字覆盖调用方的 .info.json，永久丢失规约要求保留的 callee 信息。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-270"></a>
## FMA-MISMATCH-270 — `main-py--_clean_previous_run`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-270](bug_list_v7_28_zh_filter.md#fma-mismatch-270)

### 预期行为

由 work_dir 表示的文件系统路径不再指向已存在的目录。如果在调用前该路径指向一个目录，则该目录及其中的所有文件和子目录已从文件系统中递归删除。

### 实际行为

如果函数在未引发异常的情况下完成，则以下断言成立：如果调用前 `os.path.isdir(work_dir)` 为真，则调用后 `os.path.exists(work_dir)` 为假（目录及其内容已被删除）；如果调用前 `work_dir` 不是一个目录（或不存在），则 `work_dir` 处的文件系统状态保持不变。如果函数引发异常，则 `work_dir` 的状态未指定（可能被部分删除或保持不变）。形式化表述为：\( (\text{normal\_return} \Rightarrow (\text{is\_dir}(work_dir)_{\text{pre}} \Rightarrow \neg \text{exists}(work_dir)_{\text{post}}) \wedge (\neg \text{is\_dir}(work_dir)_{\text{pre}} \Rightarrow \text{unchanged}(work_dir)) ) \wedge (\text{exceptional\_return} \Rightarrow \top ) \)

### 为什么会认为是 Bug

os.path.isdir 跟踪符号链接，因此指向目录的符号链接被视为目录，条件为真。但是，shutil.rmtree 删除的是符号链接本身，而不是目标目录。目标目录及其内容保持不变，这违反了要求递归删除目录及其所有内容的规定。

### 如何违反规约

当 work_dir 是指向目录的符号链接时，os.path.isdir 返回 True，但 shutil.rmtree 引发 OSError（Python 3.12+）或仅删除符号链接，使目标目录保持不变。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-291"></a>
## FMA-MISMATCH-291 — `src--scope-py--_score_class`

- **原分类：** **契约不确定**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-291](bug_list_v7_28_zh_filter.md#fma-mismatch-291)

### 预期行为

返回一个非负浮点数。得分为以下加权分量的总和：(a) 对类名各组成部分中每一个与 signals['backtick_idents'] 中的 token 匹配的 token，加上固定的反引号名称重叠权重；(b) 对类名各组成部分中每一个与 signals['plain_idents'] 中的 token 匹配的 token，加上固定的类名重叠权重；(c) 对类名各组成部分中每一个与 signals['all_words'] 中的 token 匹配的 token，加上相同的固定类名重叠权重；(d) 对类名各组成部分中每一个与 signals['dotted_classes'] 中的 token 匹配的 token，加上固定的点号引用重叠权重；(e) 当 cls['docstring'] 非空且为真值时：对文档字符串中每一个由四个或更多字符组成、不是停用词，且与 signals['all_words'] 中的 token 匹配的字母词，加上固定的类文档重叠权重。当 cls['docstring'] 为空或假值时，分量 (e) 贡献为零。当没有任何名称部分 token 及符合条件的文档字符串词 token 与任何指定的信号集重叠时，返回值恰好为零。

### 实际行为

该函数返回一个非负浮点得分，计算方式为：令 name = cls['name']；doc = cls['docstring']；name_parts = _name_parts(name)。得分 = |name_parts  signals['backtick_idents']| * W_BACKTICK_NAME + |name_parts  signals['plain_idents']| * W_CLASS_NAME_MATCH + |name_parts  signals['all_words']| * W_CLASS_NAME_MATCH + |name_parts  signals['dotted_classes']| * W_DOTTED_REF + ( 如果 doc  '' 则 |{w | w  re.findall(r'\b([a-zA-Z]{4,})\b', doc.lower())  w  _STOP}  signals['all_words']| * W_CLASS_DOC_MATCH 否则 0 )。输入 cls 和 signals 未被修改；不会抛出异常。

### 为什么会认为是 Bug

该正则表达式将词提取限制为 ASCII 字母 [a-zA-Z]，但规范要求提取所有字母词（包括非 ASCII 字母）。对于 docstring 'nave'，代码未找到匹配词并得分为 0，而规范将会给予 W_CLASS_DOC_MATCH 得分，因为 'nave' 是一个五字符的字母词且出现在 signals['all_words'] 中。

### 如何违反规约

仅限于 ASCII 的正则表达式 [a-zA-Z] 无法匹配类文档字符串中的非 ASCII 字母词，导致 _score_class 遗漏符合条件的文档词与 signals['all_words'] 的重叠。

### 判读建议

**保留为契约待确认项，暂不直接修改实现。** 优先检查真实调用方、README、配置 schema 和已有测试，确认该条规约是否属于产品契约；若有独立依据支持预期行为，则修复实现并补回归测试，否则应重写或删除过强的 SPEC。

---

<a id="review-030"></a>
## FMA-MISMATCH-030 — `src--configure_llm-py--update_llm_settings_toml_text`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-030](bug_list_v7_28_zh_filter.md#fma-mismatch-030)

### 预期行为

当 updates 为空时引发 ConfigWizardError。当 updates 中的任意键值对验证失败时引发 ConfigWizardError（键不是可识别的 LLM 配置字段名，或值不符合该字段的预期格式）。当 text 无法被标准库解析器解析为有效 TOML，或 text 解码为非表的 TOML 值时引发 ConfigWizardError。否则返回一个包含有效 TOML 的字符串，其中：对于 updates 中的每个键，[llm] 部分下的对应字段设置为 updates[key]；所有其他 TOML 部分、更新键以外的所有字段、所有注释，以及更新字段值以外的所有空白，均原样保留自 text。当 text 不包含 [llm] 部分时，追加一个新的 [llm] 部分，包含 updates 中的所有字段。

### 实际行为

函数 update_llm_settings_toml_text 要么返回一个修改后的 TOML 字符串，该字符串将`updates`中所有期望的 LLM 设置集成到输入`[llm]`的`text`部分，要么在前置条件被违反时引发错误。更精确地说：
- 如果 `updates` 为假值（例如空字典），则引发 ConfigWizardError('Provide at least one LLM setting to update.')。
- 如果 `updates` 中的任意 (key, value) 对在 `validate_llm_setting(key, value)` 中失败，则该函数引发的错误会传播（此错误表明 `key` 不可识别，或 `value` 不满足字段的类型/格式约束）。
- 如果 `text` 因任何原因无法解析为 TOML（即 `tomllib.loads(text)` 引发 `tomllib.TOMLDecodeError`），则引发 ConfigWizardError('Existing fm-agent.toml is invalid TOML; refusing to overwrite it.')。
- 如果 `text` 成功解码，但结果是一个真值且不是字典（例如字符串、整数、数组），则引发 ConfigWizardError('Existing fm-agent.toml must decode to a table/object.')。
否则（所有检查通过），函数返回一个新字符串 `r`，这是一个有效的 TOML 文档，满足：
1. `r` 包含一个 `[llm]` 部分（顶层表）。
2. 在该 `[llm]` 部分中，对于 `k` 中的每个键 `updates`，有且只有一行形如 `{k:<9} = {_quote_toml_string(updates[k])}` 的键值行（其中 `_quote_toml_string` 产生一个 TOML 有效的带引号字符串）。原始 `[llm]` 部分中该键的任何先前值被替换；如果键原本不存在，则追加到该部分的末尾。
3. `text` 的所有其他内容（其他部分、注释、格式化、`[llm]` 以外的空行）在 `r` 中保留，除非原始 `text` 为空，则 `r` 仅由 `[llm]\n` 后跟必要的键值行（每行以换行符结束）组成。
4. 当原始 `text` 包含一个 `[llm]` 部分时，`updates` 中未提及的任何现有 LLM 键在 `r` 中保持不变。
象征性地，给定前置条件 P(text, updates):
  (updates 为空)    函数引发 ConfigWizardError    返回值未定义
  ( 存在 (k,v) ∈ updates 使得 validate_llm_setting(k,v) 失败)    函数引发错误    返回未定义
  (tomllib.loads(text) 失败或返回真值非字典)    函数引发 ConfigWizardError    返回未定义
  否则    函数返回 r，其中 r 是满足上述 1-4 属性的字符串。

### 为什么会认为是 Bug

代码使用正则表达式 (_KV_RE) 来识别键值行。当键被引用时（例如 "api_key"），正则表达式可能不匹配，导致原始行被当作非键行处理。键无法被识别，因此原始行被保留不变，新的键值对随后被追加（第 44-47 行）。输出包含重复键，这是无效的 TOML，并且未按规范要求替换字段。

### 如何违反规约

当输入的 TOML 使用带引号的键（例如 "name"）时，_KV_RE 正则表达式匹配失败，导致旧的键值行被保留，新的裸键行被追加，产生重复键。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-038"></a>
## FMA-MISMATCH-038 — `src--env_check-py--_check_oh_my_openagent`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-038](bug_list_v7_28_zh_filter.md#fma-mismatch-038)

### 预期行为

当 oh-my-openagent 可通过 bunx 访问并在 10 秒内响应其 version 标志时，返回 (True, None)，表示该工具已安装并可执行。当 oh-my-openagent 因任何原因无法通过 bunx 调用时（包括 bunx 本身不可用、工具未安装或调用超过 10 秒），返回 (False, "oh-my-openagent is not installed (bunx unavailable or timed out)")。该函数不产生任何副作用，不会创建、修改或删除任何文件。

### 实际行为

函数调用后，以下情形之一成立：
1. 如果 `subprocess` 的导入失败，则引发 `ImportError`（或其子类），函数未返回。未产生任何元组。
2. 否则，函数返回一个 2 元组 `(result, message)`，其中：
   - 如果子进程运行完成未引发任何异常，则 `result` 为 `True`，`message` 为 `None`。
   - 如果在 `subprocess.run(...)` 期间发生任何异常（包括 `CalledProcessError`、`FileNotFoundError`、`TimeoutExpired` 等），则 `result` 为 `False`，`message` 等于字符串 `"oh-my-openagent is not installed (bunx unavailable or timed out)"`。
形式化描述：令 `S` 为调用后的状态，`R` 为返回值，`E` 为任何未捕获的异常。
- `(E = none)  (import subprocess succeeded)`
- `(E = none)  (R is a 2-tuple)  (R[0]  {True, False})`
- `(E = none  R[0] = True)  (R[1] is None)  (subprocess.run completed without exception)`
- `(E = none  R[0] = False)  (R[1] = "oh-my-openagent is not installed (bunx unavailable or timed out)")  (subprocess.run raised an exception)`
- 若 `import subprocess` 引发了异常，则 `E` 为该异常，且不存在返回值。

### 为什么会认为是 Bug

代码未检查子进程返回码或输出。非零退出状态（例如 oh-my-openagent 缺失时）导致函数返回 True，违反了规范要求（在调用工具失败时应返回 False）。

### 如何违反规约

subprocess.run() 未使用 check=True，在非零退出码时不会引发异常；当 bunx 以非零退出时，函数返回 (True, None) 而非 (False, error_message)。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-054"></a>
## FMA-MISMATCH-054 — `src--call_graph_edges-py--_normalize_endpoint_label`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-054](bug_list_v7_28_zh_filter.md#fma-mismatch-054)

### 预期行为

当 label 包含至少一个 '::'，且最后一个 '::' 之前的子串由类似 POSIX 路径的组件组成时，返回一个规范的 FQN，其中：(1) 路径部分中任何前导的 './' 前缀被移除；(2) 路径最终文件名组件中最后一个 '.' 被替换为 '-'；(3) 所有父目录路径组件中，排除 '.' 和空字符串后，用 '::' 连接形成 FQN 前缀；(4) 函数名附加以最后一个 '::' 分隔的段。当 label 不匹配此模式时，返回清洗后未作变更的 label。

### 实际行为

该函数返回一个新字符串，且无副作用。设 cl = _clean_label(label)（去除首尾空白后的 label）。如果 _is_path_function_label(cl) 返回 True，则令 (path_str, func) = cl.rsplit('::', 1)；令 stripped_path = path_str.lstrip('./')（移除所有前导的 '.' 和 '/'）；令 pp = PurePosixPath(stripped_path)；令 base = pp.name；令 last_dot = base.rfind('.')；如果 last_dot > 0 则令 func_dir = (base[:last_dot] + '-' + base[last_dot+1:])，否则为 base；令 parts = [p for p in pp.parent.parts if p not in {'', '.'}]；然后返回值为 '::'.join(parts + [func_dir, func])。否则，返回值为 cl。形式上为： 
result = ( (lambda cl: (lambda path_str, func: (lambda stripped_path: (lambda pp: (lambda base: (lambda last_dot: (lambda func_dir: (lambda parts: '::'.join(parts + [func_dir, func]))([p for p in pp.parent.parts if p not in {'', '.'}]))((base[:last_dot] + '-' + base[last_dot+1:]) if last_dot > 0 else base))(base.rfind('.')))(pp.name))(PurePosixPath(stripped_path)))(path_str.lstrip('./')))(*cl.rsplit('::', 1)) if _is_path_function_label(cl) else cl )(_clean_label(label))

### 为什么会认为是 Bug

规范要求只移除前导的 './' 前缀，但 lstrip('./') 会移除所有前导的 '.' 和 '/' 字符，因此 '../foo::func' 错误地变为 'foo::func'，而非 '..::foo::func'。

### 如何违反规约

lstrip("./") 会剥离所有前导的 '.' 和 '/' 字符，因此 '../foo.c::func' 丢失了 '..' 父组件，变为 'foo-c::func'，而非 '..::foo-c::func'。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-058"></a>
## FMA-MISMATCH-058 — `src--call_graph_edges-py--load_call_edges`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-058](bug_list_v7_28_zh_filter.md#fma-mismatch-058)

### 预期行为

当 path 为 None 时，返回空列表。当 path 标识单个文件时，返回从该文件解析出的 CallEdge 对象，且所有重复边已被移除。当 path 标识一个目录时，返回在该目录下递归找到的每一个符合条件的边文件的 CallEdge 对象，合并为一个列表，且所有重复边均被移除。在所有非 None 的情况下，返回的每个元素都是 CallEdge，且对于任意不同的 caller 和 callee 规范对，最多出现一个 CallEdge。基于目录遍历得到的结果以与文件系统遍历顺序一致的稳定顺序返回。

### 实际行为

自然语言：如果 `path` 为 `None`，返回值为空列表。否则，令 `p = Path(path)`。如果 `p` 是一个目录，函数通过 `p.rglob('*')` 递归收集文件，选出那些 `is_file()` 和 `_is_edge_file()` 返回 `True` 的文件，按字典序排序，依次通过 `CallEdge` 加载每个文件的 `_load_call_edge_file` 列表，按该顺序拼接，按 caller/callee 规范去重并保留首次出现，最后返回结果列表。如果 `p` 是一个文件，函数从该文件通过 `CallEdge` 加载 `_load_call_edge_file` 列表，去重并返回结果。如果上述任一步骤抛出异常（例如 `Path` 构造、文件系统遍历、文件读取或 JSON 解析），该异常会传播出去，且不返回值。
形式化逻辑：
设 `ret` 表示成功执行后的返回值。
- 若 `path is None`： `ret = []`。
- 否则定义 `p = Path(path)`。
  - 若 `p.is_dir()`：
    `files = [f for f in sorted(p.rglob('*')) if f.is_file() and _is_edge_file(f)]`
    `edges = concatenation of [(_load_call_edge_file(f)) for f in files]`
    `ret = dedupe(edges)`，其中 `dedupe` 确保 ` i<j, (ret[i].caller == ret[j].caller  ret[i].callee == ret[j].callee)` 且每个元素出现在其在 `edges` 中最早出现的位置。
  - 若 `p.is_file()`：
    `ret = dedupe(_load_call_edge_file(p))`。
若上述任一操作抛出异常 `E`，函数以异常 `E` 退出，且不产生 `ret`。

### 为什么会认为是 Bug

规范要求结果顺序“与文件系统遍历顺序一致”，即 rglob 产生条目的顺序。代码对 rglob 结果调用了 sorted()，这强制施加了字母顺序，可能与遍历顺序不同，从而违反了规范。

### 如何违反规约

代码对 rglob 结果调用 sorted()，强制施加字母顺序，而非规范要求的文件系统遍历顺序；当两个拥有相同边键的文件以错误顺序处理时可观察到。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-063"></a>
## FMA-MISMATCH-063 — `src--languages--codegraph-py--_bare_function_name`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `2`
- **原始详情：** [查看 FMA-MISMATCH-063](bug_list_v7_28_zh_filter.md#fma-mismatch-063)

### 预期行为

返回去除了所有 tree-sitter 装饰的、未经限定的裸函数或方法名。结果为空值当且仅当输入为空字符串或纯空白。对于包含 'operator' 关键字的名称，结果为完整的 operator 说明符：关键字 'operator' 后跟运算符符号或关键字后缀，中间多余的空白被压缩。对于所有其他名称，结果是去除前缀装饰后、在任何尾随参数列表、模板体或类型注解之前提取的第一个字母或字母数字标识符令牌。返回的字符串不包含 '::' 或 '.' 限定符分隔符。如果无法从非空输入中提取任何标识符令牌，则原样返回去除空白后的输入。

### 实际行为

函数返回一个字符串 r。令 s = name.strip()。如果 s 为空，则 r = ''。否则，定义 tail = (如果 s 中包含 '::'，则取 s.rsplit('::', 1)[1].lstrip()，否则，如果 s 中包含 '.'，则取 s.rsplit('.', 1)[1].lstrip())，如果不包含 '.'，则 tail = s。如果 tail 以 'operator' 开头：令 rest = tail[8:].lstrip()；如果 rest 以 '[]' 开头：r = 'operator[]'；否则如果 rest 以 '()' 开头：r = 'operator()'；否则如果 rest 恰为 'new' 或由 'new' 后跟可选空白、再跟 '['、可选空白、']' 且无其他内容构成，则 r = 'operator new[]'（如果 rest 中包含 '['）否则为 'operator new'；否则如果 rest 恰为 'delete' 或由 'delete' 后跟可选空白、再跟 '['、可选空白、']' 且无其他内容构成，则 r = 'operator delete[]'（如果 rest 中包含 '['）否则为 'operator delete'；否则：设 prefix 为 rest 中最长的初始子串，仅包含集合 {+, -, *, /, %, &, |, ^, ~, !, =, <, >, ,} 中的字符；如果 prefix 非空，r = 'operator' + prefix。如果 r 仍未赋值，则检查 s：如果 s 以一个由单词字符（字母数字或下划线）构成的结尾序列，且该序列前紧邻字符串开头、'::' 或 '.'，则 r 为该单词序列；否则如果 s 匹配模式 '(' 后跟可选空白、'*'、可选空白、一个单词、可选空白、')'，则 r 为该单词；否则如果 s 匹配模式 '*' 后跟可选空白、一个单词，则 r 为该单词；否则如果 s 以一个单词开头，则 r 为该单词；否则 r = s。

### 为什么会认为是 Bug

对于输入 'func -> int'，代码返回 'int'（最后一个单词），但规范要求返回在尾随类型注解之前的第一个标识符令牌，即 'func'。

### 如何违反规约

输入 'foo::bar -> int'：限定符 '::' 被剥离得到 'bar'，但第 49 行的正则表达式在原始名称上搜索并失败，因此回退逻辑错误地返回 'foo'。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-066"></a>
## FMA-MISMATCH-066 — `src--languages--codegraph-py--_fqn_for`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-066](bug_list_v7_28_zh_filter.md#fma-mismatch-066)

### 预期行为

返回一个字符串，由以下组成：(1) file_path 目录按 '/' 分割后得到的非空段，(2) file_path 的基名将其最后一个 '.' 替换为 '-'（当基名不包含 '.' 时保持不变），以及 (3) name。所有部分由 '::' 连接。返回的字符串至少包含两个 '::' 分隔符，且其中没有任何部分为空。

### 实际行为

该函数返回一个字符串 FQN，通过规范化 `file_path`（将 `os.sep` 替换为 '/'），使用 `os.path.dirname` 和 `os.path.basename` 提取其目录和基名，然后将基名中的最后一个 '.'（如果有）替换为 '-' 以产生带横线的基名。最终结果为 `'::'.join([comp for comp in dirname(normalized).split('/') if comp] + [dashed_basename, name])`，其中 `normalized = file_path.replace(os.sep, '/')`、`dirname = os.path.dirname(normalized)`、`base = os.path.basename(normalized)`、`dashed_basename = base[:last_dot] + '-' + base[last_dot+1:] if (last_dot := base.rfind('.')) > 0 else base`。在给定的有效前置条件下，不会产生副作用，也不会引发异常。

### 为什么会认为是 Bug

规约要求在基名中将最后一个 '.' 替换为 '-'，无论该点的位置如何。而代码仅在 last_dot > 0 时才执行替换，排除了点位于第一个字符的情况（例如基名 '.hidden'）。对于输入 file_path='dir/.hidden', name='func'，代码返回 'dir::.hidden::func'，而规约要求 'dir::-hidden::func'，这违反了规约。

### 如何违反规约

当基名以 '.' 开头时（例如 '.hidden'），last_dot=0 未能通过 > 0 的守卫条件，因此点号未被替换为 '-'，未满足规约要求。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-071"></a>
## FMA-MISMATCH-071 — `src--extract-py--_extract_func_name_brace`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-071](bug_list_v7_28_zh_filter.md#fma-mismatch-071)

### 预期行为

当 signature_text 包含可识别的函数声明时，返回裸函数名字符串；否则返回 None。对于匹配运算符重载模式（'operator' 后跟运算符标记或关键字（例如 '[]'、'()'、'new[]'、算术/位运算符号），且紧邻 '(' 前）的声明，返回完整的运算符说明符字符串。对于所有其他声明，在从 signature_text 中移除模板/泛型尖括号区域后，返回紧邻 '(' 前的第一个单词标记，且其文本不属于 lang_cfg['keywords']。当经过关键字过滤后不存在此类标记时返回 None。

### 实际行为

该函数返回表示提取出的函数名的字符串，若无法提取到名称则返回 None。具体而言：
- 若 signature_text 包含与正则表达式 `\b(operator\s*(?:\[\]|\(\)|[+\-*/%&|^~!=<>]+|new(?:\s*\[\s*\])?|delete(?:\s*\[\s*\])?))\s*\(` 匹配的子串，则返回捕获组（运算符关键字后跟其重载说明，例如 'operator+'、'operator()'、'operator new[]'）。
- 否则，令 cleaned_text 为 _strip_angle_brackets(signature_text) 的结果。对于 cleaned_text 中该正则表达式 `\b(\w+)\s*\(` 的每一个匹配（按从左到右的顺序），若捕获组（括号前的标识符）不属于 lang_cfg['keywords']，则返回该标识符。
- 若找不到此类标识符，则返回 None。
形式化表示：
令 op_pattern = /\b(operator\s*(?:\[\]|\(\)|[+\-*/%&|^~!=<>]+|new(?:\s*\[\s*\])?|delete(?:\s*\[\s*\])?))\s*\(/
令 id_pattern = /\b(\w+)\s*\(/
令 keywords = lang_cfg['keywords']
令 remove_brackets(s) = _strip_angle_brackets(s)
若 匹配 m = search(op_pattern, signature_text)，则返回 m.group(1)。
否则令 cleaned = remove_brackets(signature_text)。
若 匹配 m 在 finditer(id_pattern, cleaned) 中，且 m.group(1) ∉ keywords，则返回第一个这样的 m.group(1)。
否则返回 None。

### 为什么会认为是 Bug

代码在剥离尖括号之前，在整个 signature_text 中搜索运算符模式。这导致对模板参数列表中的 'operator+' 产生错误匹配，尽管整个声明并不是运算符重载。规范要求运算符重载模式仅适用于运算符声明；对所有其他声明，应在移除模板/泛型尖括号区域后再提取名称，在此示例中应返回 'bar'。

### 如何违反规约

括号内的 angle-bracket 模板参数中的 operator()，在尖括号被剥离之前就被 re.search 匹配到，导致错误的运算符重载检测。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-073"></a>
## FMA-MISMATCH-073 — `src--extract-py--_extract_functions_indent`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-073](bug_list_v7_28_zh_filter.md#fma-mismatch-073)

### 预期行为

返回一个由 (name, start_idx, end_idx) 组成的元组列表，每个元组对应 lines 中发现的一个顶层函数定义。start_idx 和 end_idx 是从 0 开始的包含性的行索引。从 start_idx 到 end_idx 的区间覆盖整个函数：包括任何前置装饰器行、函数定义头（可能跨越多行）以及函数体，但不包括紧跟在最后一个非空函数体行之后的尾部空行。name 是定义行上紧跟在函数定义关键字之后的标识符 token。函数按照在 lines 中出现的顺序返回。当未找到任何函数定义时返回空列表。

### 实际行为

该函数返回一个由 `functions` 元组 `(name, start, end)` 组成的列表，其中每个元组对应 `lines` 中发现的一个顶层函数定义。函数定义是匹配模式 `def name(` 的行（允许任意缩进）。`start` 是函数的第一行的索引，包括任何前置装饰器行（以 '@' 开头的行）。`end` 是函数体的最后一个非空行的索引。函数体由定义行之后缩进大于该定义行缩进的行、空行以及恰好与定义行缩进相同但以右括号开头并后跟 ':' 或 '->' 的行（多行签名的续行）组成。函数体刚好在第一个非空、缩进小于或等于定义行缩进且不是签名续行的行之前结束。函数按照其 `def` 行出现的顺序提取，跳过任何位于先前提取的函数体内的 `def` 行（即仅提取最外层函数）。输入 `lines` 和 `lang_cfg` 不会被修改。
正式地，令 `n = len(lines)` 并定义：
- `is_blank(l)  l.strip() == ''`
- `is_decorator(l)  l.strip().startswith('@')`
- `is_func_def(l)  re.match(r'^(\s*)def\s+(\w+)\s*\(', l) is not None`；若为真，则令 `name(l)` 为捕获的名称，`indent(l) = len(leading_whitespace)`。
- `is_sig_cont(l, ind)  len(l) - len(l.lstrip()) == ind` 和 `re.match(r'\)\s*(:|->)', l.lstrip()) is not None`。
那么 `functions` = `[(N_0, S_0, E_0), ..., (N_{m-1}, S_{m-1}, E_{m-1})]` 对于某些 `m  0`，其 `def` 位置 `D_0 < D_1 < ... < D_{m-1}` 严格递增，且满足：
1. `is_func_def(lines[D_k])` 成立，`N_k = name(lines[D_k])`，`I_k = indent(lines[D_k])`。
2. `S_k` 是满足 `s  D_k` 的最小索引，其中 `[s, D_k-1]` 中的每一行都是装饰器，且 `s=0` 或 `lines[s-1]` 不是装饰器。
3. 令 `B_k` 为满足 `b  D_k+1` 或（`b == n` 且 `not is_blank(lines[b])` 且 `indent(lines[b])  I_k`）的最小索引 `not is_sig_cont(lines[b], I_k)`。则 `E_k` 是满足 `e` 且 `D_k  e < B_k` 或 `e == D_k` 的最大索引 `not is_blank(lines[e])`。
4. 对于每个 `k`，`D_{k+1} > E_k`（若 `k < m-1`），并且对于任何不在 `d` 中的索引 `is_func_def(lines[d])` 且 `{D_k}`，则 `d` 位于某个区间 `[S_k, E_k]` 中，或者 `d` 会产生一个 `B_k  d` 但该情况因扫描顺序被排除。
5. `functions` 中不存在其他元组。

### 为什么会认为是 Bug

该代码仅在缩进与定义行相同且以 ')' 开头后跟 ':' 或 '->' 的行时识别多行函数签名。当位于同一缩进的续行不以 ')' 开头时，例如参数行或不带 ')' 前缀的闭合行，代码会错误地将其视为函数结束，从而截断区间。在反例中，行 'b):' 的缩进为 0，与 def 的缩进相同，但不匹配签名续行的正则表达式，因此内部循环中断，导致区间为 [0,0] 而不是覆盖整个函数。

### 如何违反规约

不以 ')' 开头的多行函数签名续行会导致在 src/extract.py 的第 562 行处过早截断函数的区间。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-076"></a>
## FMA-MISMATCH-076 — `src--extract-py--_strip_angle_brackets`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-076](bug_list_v7_28_zh_filter.md#fma-mismatch-076)

### 预期行为

返回一个由 text 形成的字符串，该字符串移除了每一个最外层的、平衡的 '<...>' 区域：分隔符 '<' 和 '>' 字符及其之间的所有内容均被剥离。嵌套解析方式为——在活动的 '<...>' 区域内遇到的 '<' 属于内部区域，不会终止外部区域。不属于任何平衡 '<...>' 区域的字符将按其原始相对顺序保留。未闭合任何活动 '<...>' 区域的 '>' 字符将从结果中省略。

### 实际行为

该函数返回一个新的字符串，该字符串省略了所有出现的 '<' 和 '>'，并且也省略了出现在平衡尖括号对内的所有字符（遵循标准嵌套规则）。形式上，为索引 i (0 ≤ i ≤ len(text)) 定义字符前深度 d(i)：d(0)=0，且对于 i≥0：若 text[i]='<'，则 d(i+1) = d(i)+1；若 text[i]='>'，则 d(i+1) = max(0, d(i)-1)；否则 d(i+1) = d(i)。然后输出字符串是所有满足 text[i] ∉ {'<','>'} 且 d(i)=0 的字符 text[i] 的连接。未匹配的 '<' 导致该字符之后直到字符串末尾（或直到遇到匹配的 '>'）的所有字符被视为处于区域内，从而被移除；深度为零时的任何未匹配 '>' 也会被移除。

### 为什么会认为是 Bug

该代码无条件移除 '<' 字符，即使它们未匹配且不属于任何平衡区域。规约（Condition B）要求保留未匹配的 '<'，因为只应移除最外层的平衡 '<...>' 区域（以及未匹配的 '>'）。对于输入 '<'，代码返回 ''，但规约要求返回 '<'。

### 如何违反规约

输入 '<'（未匹配的尖括号）返回空字符串而非 '<' — 该 '<' 字符在未平衡时被无条件丢弃，而非保留。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-077"></a>
## FMA-MISMATCH-077 — `src--extract-py--extract_functions_from_file`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-077](bug_list_v7_28_zh_filter.md#fma-mismatch-077)

### 预期行为

返回一个 (func_name, source_text) 元组列表，每个元组对应文件中通过特定语言提取规则找到的一个函数。每个 func_name 都经过规范化：不安全字符被翻译，文件中出现的重名通过按首次出现顺序追加数字后缀的方式进行去重。source_text 包含完整的函数体，从开始到结束（包含两端），行结尾统一为 '\n'，且函数体以尾随换行符结束。函数按源代码顺序出现。当语言没有文件局部正则提取能力时，返回空列表。

### 实际行为

在正常执行时，文件被读取并关闭，无副作用；返回值是一个 (deduped_name, source_text) 元组列表。如果 lang_cfg["body"] 既不是 "brace" 也不是 "indent"，则列表为空。否则，对于通过特定语言提取（大括号匹配或缩进）检测到的每个顶层函数，包含一个元组。deduped_name 是函数原始名称经过规范化的形式（将 '/' 翻译为 '_'），若同一规范化名称出现多次，则追加数字后缀 '_{count}'，从第二次出现开始计数（从 1 开始）。source_text 包含该函数的拼接源代码行（从开始索引到结束索引，包含两端，行间用换行符分隔，并带有一个尾随换行符）。元组的顺序与文件中函数的顺序一致。形式化地，令 lines = [l.rstrip('\n').rstrip('\r') for l in readlines(filepath)]；令 lang_cfg = LANG_CONFIG[lang_key]。若 lang_cfg["body"] ∉ {"brace", "indent"}：result = []。否则令 P = （若 lang_cfg["body"] = "brace" 则为 _extract_functions_brace(lines, lang_key, lang_cfg)，否则为 _extract_functions_indent(lines, lang_cfg)），其中 P 是一个长度为 m 的 (name_i, start_i, end_i) 列表（i = 0..m-1）。对于每个 i，令 cname_i = canonicalize(name_i)，count_i = |{j < i : canonicalize(P[j][0]) = cname_i}|。则 deduped_name_i = cname_i（若 count_i = 0 则为此，否则为 cname_i + '_' + count_i）；source_i = '\n'.join(lines[start_i .. end_i]) + '\n'；result = [(deduped_name_i, source_i) | i = 0..m-1]。

### 为什么会认为是 Bug

代码在移除换行符之后，再去除每一行的尾随回车符，这会移除源内容中字面上的 \r（例如字符串内部）。这破坏了函数体，违反了规格要求 source_text 应包含完整函数体且仅将行结尾归一化的规定。

### 如何违反规约

源内容中字面 CR 字节（0x0D）被当作行结尾并去除，破坏了提取的函数体。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-097"></a>
## FMA-MISMATCH-097 — `src--languages--erlang-py--_elp_argv`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-097](bug_list_v7_28_zh_filter.md#fma-mismatch-097)

### 预期行为

返回一个非空字符串列表，其最后一个元素是“server”，适用于将 ELP 作为一个从标准输入读取 JSON-RPC 请求并向标准输出写入 JSON-RPC 响应的子进程来调用。前面的元素构成了对已配置的 ELP 二进制文件的一个平台合适的调用形式。返回值是稳定的：如果 ELP 后端配置没有改变，两次调用返回相等的列表；如果 ELP 后端发生了可能对相同输入项目产生不同分析输出的改变，则返回不相等的列表。

### 实际行为

该函数返回一个表示用于启动 ELP 服务器的参数向量的字符串列表。令 `cmd = settings.erlang.command.strip()` 和 `tokens = shlex.split(cmd, posix=(os.name != 'nt'))`。如果 `tokens` 为空，令 `base = ['elp']`；否则 `base = tokens`。返回的列表是 `base + ['server']`。因此，结果永远非空，始终将 `'server'` 作为其最后一个元素，并且其第一个元素要么是 `settings.erlang.command` 去除空白后的非空内容按 token 分割的结果，要么是 `'elp'`（如果没有配置有效的命令）。

### 为什么会认为是 Bug

返回的列表变为 ['elp', 'server', 'server']，这并没有形成一个平台合适的调用形式，因为前面的元素现在包含一个重复的“server”，可能会使 ELP 感到困惑。规范要求在最后的“server”之前的参数构成一个正确的调用；重复的“server”违反了这一要求。

### 如何违反规约

当 settings.erlang.command 是 'elp server'（或任何已经包含 'server' 的命令）时，无条件的追加会在参数向量中产生一个重复的“server”。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-098"></a>
## FMA-MISMATCH-098 — `src--languages--erlang-py--_escape_component`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；尝试次数 `1`
- **原始详情：** [查看 FMA-MISMATCH-098](bug_list_v7_28_zh_filter.md#fma-mismatch-098)

### 预期行为

返回一个字符串，其中 value 中每个字符如果是 ASCII 字母数字 (a-z, A-Z, 0-9) 或下划线，则保留在其原始相对位置，其他每个字符则替换为一个下划线后跟其 Unicode 码点，以零填充的两位十六进制数表示。输出是确定性的：相同的输入字符串总是产生相同的输出字符串。输出中的每个字符都属于集合 [a-zA-Z0-9_]。

### 实际行为

该函数通过按顺序遍历 `c` 中的每个字符 `value`，并追加 `c` 本身（如果 `c` 是 ASCII 字符并且 `c.isalnum()` 是 `True` 或者 `c` 等于 `'_'`），或者追加字符串 _ 后跟 `ord(c)` 的小写零填充（最小宽度 2）十六进制表示，从而返回一个字符串。形式化地说：如果 `process(c) = c` 则令 `c.isascii() and (c.isalnum() or c == '_')`，否则令 `'_' + f'{ord(c):02x}'`。然后返回的字符串等于 `''.join(process(c) for c in value)`。输出始终非空，因为至少有一个字符贡献至少一个字符。

### 为什么会认为是 Bug

对于输入字符串 '' (U+03C0)，代码返回 '_3c0'，它使用了三个十六进制数字。规范要求每个非字母数字下划线字符后跟一个下划线后跟零填充的两位十六进制数字。由于 0x3C0 需要三个数字，输出违反了“两位数字”要求。

### 如何违反规约

输入 'π' (U+03C0, 序号 960=0x3C0) 产生 '_3c0'（包含 3 个十六进制数字），但规范要求恰好 2 个零填充的十六进制数字。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-099"></a>
## FMA-MISMATCH-099 — `src--languages--erlang-py--_function_id`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-099](bug_list_v7_28_zh_filter.md#fma-mismatch-099)

### 预期行为

返回一个规范函数标识字符串，该字符串由从 uri 派生的模块标识符、从 label 中提取的非限定函数名以及从 label 中提取的 arity 组成，以双下划线连接，格式为 <module>__<name>__<arity>。每个组分（<module>、<name>）中任何与双下划线分隔符冲突的字符都会被确定性替换。非限定函数名是 label 中最后一个正斜杠之前的部分；当该部分包含冒号且不以单引号字符开头时，仅使用最后一个冒号之后的子串作为非限定名称。当 label 不是字符串、label 不包含正斜杠分隔符，或 label 中最后一个正斜杠之后的部分无法解析为非负整数时，抛出 ValueError。

### 实际行为

如果 label 字符串包含斜杠 '/' 且最后一个斜杠之后的子串是一个有效的非负整数，则函数返回一个由以下步骤形成的字符串：(1) 通过 `_module_from_uri(uri)` 从 uri 计算模块标识符，(2) 从最后一个斜杠之前的部分提取函数名：如果该部分包含冒号 ':' 且不以单引号开头，则函数名取最后一个冒号之后的子串；否则为斜杠之前的整个部分，(3) 对模块标识符和函数名应用 `_escape_component`，(4) 将它们与双下划线和整数 arity 串联：`f"{escaped_module}__{escaped_name}__{arity}"`。如果 label 不包含斜杠或斜杠之后的子串无法转换为非负整数，则抛出 `ValueError`，消息为 `"ELP function label has no valid arity: {label!r}"`，由原始异常链接而来。假设函数 `_module_from_uri` 和 `_escape_component` 在给定前置条件下始终产生确定性结果；它们抛出的任何异常会直接传播。形式上，对于所有满足前置条件的 `uri`、`label`：( name, arity_s : label = name + '/' + arity_s  arity_s  )  result = concat(_escape_component(_module_from_uri(uri)), "__", _escape_component(name_without_module), "__", arity_s)，其中 name_without_module = 如果 (':'  name  name[0]  ''') 则 rsplit(name, ':', 1)[1] 否则 name；否则函数抛出带有指定消息的 ValueError。

### 为什么会认为是 Bug

代码未验证 arity 子串表示一个非负整数。int('-1') 会成功，因此 label='foo/-1' 返回包含 '__-1__' 的字符串，而不是按要求抛出 ValueError。此外，代码没有处理 label 不是字符串的情况（例如 label=42），会抛出 AttributeError 而非 ValueError。

### 如何违反规约

负数 arity 未经检查地通过 int() 检查；非字符串 label 抛出 AttributeError 而非 ValueError

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-102"></a>
## FMA-MISMATCH-102 — `src--languages--erlang-py--_project_fingerprint`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-102](bug_list_v7_28_zh_filter.md#fma-mismatch-102)

### 预期行为

返回一个元组，该元组确定性地、唯一地标识位于 proj_dir 的 Erlang 项目的当前状态。对相同的 proj_dir 两次调用 _project_fingerprint 返回相等元组，当且仅当在两次调用之间，proj_dir 下与 Erlang 分析相关的任何文件均未发生更改。文件更改是指对文件内容、字节大小或最后修改时间戳的任何修改。返回的元组不依赖于文件系统枚举顺序或其他非确定性因素。

### 实际行为

如果函数正常终止，返回值是一个元组 (backend, records)，满足：
- backend = _elp_argv()，标识当前 ELP 后端版本与配置。
- records = tuple(sorted(set( (os.path.relpath(p, root), os.stat(p).st_size, os.stat(p).st_mtime_ns) for p in paths )))
  其中 root = os.path.abspath(proj_dir)，
  paths = [p for p in _iter_project_files(root, {'.erl', '.hrl'})] + [os.path.join(root, name) for name in _PROJECT_CONFIG_FILES if os.path.isfile(os.path.join(root, name))]，
  且 sorted() 按绝对路径字典序排序。
每条记录是一个 3 元组 (rel_path, size, mtime_ns)。记录已排序、去重，并包含 root 下递归找到的每一个 .erl/.hrl 源文件，以及位于 root 直属（非递归）且在 _PROJECT_CONFIG_FILES 中列出且存在的每一个项目配置文件。文件元数据（大小、修改时间）反映调用 os.stat() 那一刻的状态。在给定前置条件下，records 非空。
如果任何 os.stat()、os.path.isfile()、文件系统迭代或 os.path.abspath() 调用引发 OSError（例如 FileNotFoundError、PermissionError），异常将向上传播，函数不产生返回值；所有局部状态被丢弃。

### 为什么会认为是 Bug

指纹仅由文件大小和修改时间戳构建，忽略文件内容。因此，保持大小和 mtime_ns 不变的内容修改不会被检测到，这违反了要求：只要任何文件内容发生更改，指纹就必须改变（文件更改定义为对内容、大小或 mtime 的任何修改）。

### 如何违反规约

指纹仅使用 (size, mtime_ns) 并忽略文件内容；相同长度且保留 mtime 的内容更改未被检测到。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-106"></a>
## FMA-MISMATCH-106 — `src--languages--erlang-py--batch_extract`

- **原分类：** **可能有 Bug**
- **Validator：** `not_confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-106](bug_list_v7_28_zh_filter.md#fma-mismatch-106)

### 预期行为

返回一个字典，其键为 Erlang 源文件的绝对文件路径（字符串），值为（function_id: str, body: str）对的列表。每个 function_id 是一个规范化的、模块限定的名称，可用作完全限定名（FQN）。每个 body 是从源文件中提取的该函数的原始源代码文本。当 Erlang Language Platform 后端不可用或 proj_dir 中不包含任何可提取的 Erlang 函数时，返回一个空字典。

### 实际行为

如果函数正常返回，返回值为一个字典，其中每个键是 proj_dir 指定的目录内一个 Erlang 源文件的绝对文件路径字符串，每个值是由分析提取的元组（function_id, body）列表。如果发生异常（例如，由于 proj_dir 无效、I/O 错误或 _analysis_or_empty 的结果缺少 `functions` 属性而从 _analysis_or_empty 抛出），异常会传播，函数不返回值。

### 为什么会认为是 Bug

规范要求当 Erlang Language Platform 后端不可用时，该函数返回一个空字典。然而，代码直接返回 _analysis_or_empty 的 .functions 属性，没有任何异常处理。如果后端不可用，_analysis_or_empty 可能抛出一个异常（如条件 A 中的示例所示），该异常会传播并阻止函数返回空字典。这违反了规范对该场景的要求。

### 如何违反规约

在未安装 ELP 的情况下对包含 .erl 文件的目录调用 batch_extract；_analysis_or_empty 捕获后端不可用异常，并返回一个空的 ErlangAnalysis(functions={}, edges={})，因此 batch_extract 按规范返回 {}。

### 判读建议

**优先复核，不建议立即修改实现。** Validator 未确认原始结论，应先修正或重跑 probe，并确认反例满足函数前置条件；只有差异可稳定复现且真实调用链可达时，才进入修复队列。

---

<a id="review-107"></a>
## FMA-MISMATCH-107 — `src--languages--erlang-py--call_edges`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-107](bug_list_v7_28_zh_filter.md#fma-mismatch-107)

### 预期行为

返回一个字典，将项目中所有 Erlang 函数的每个调用者 FQN 字符串映射到一组被调用者 FQN 字符串。调用者和被调用者 FQN 都遵循整个流程中使用的相同规范化、模块限定的命名约定。当 Erlang Language Platform 后端不可用或无法从项目中提取调用边时，返回一个空字典。

### 实际行为

该函数返回一个字典，包含从项目目录 `proj_dir` 导出的模块限定的 Erlang 调用边，格式为注册表格式。如果 `proj_dir` 不存在、不包含可分析的 Erlang 源文件或发生内部错误，则返回空字典。不传播任何异常，也不修改任何可变的全局状态。形式化表示为：  proj_dir  str, let result = call_edges(proj_dir); then isinstance(result, dict)  (filesystem_contains_analyzable_erlang(proj_dir)  result = edges(analysis_or_empty(callgraph_project_root(proj_dir))))  (filesystem_contains_analyzable_erlang(proj_dir)  result = {})  执行正常终止。

### 为什么会认为是 Bug

该代码在任何内部错误发生时（通过 _analysis_or_empty）无条件返回空字典，但规范将返回空字典限制为仅在后端不可用或无法提取调用边的特定情况下。对于具有可调用函数且后端可用的有效项目，内部错误会导致代码违反规范，返回 {} 而不是预期的调用边字典。

### 如何违反规约

_analysis_or_empty() 通过裸的 'except Exception' 捕获所有异常，导致 call_edges() 对任何内部错误都返回 {} —— 而不仅仅是规范要求的后端不可用或没有调用边的情况。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-114"></a>
## FMA-MISMATCH-114 — `src--languages--python-py--batch_extract`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-114](bug_list_v7_28_zh_filter.md#fma-mismatch-114)

### 预期行为

返回一个字典，其键是 proj_dir 中发现的每个 Python 源文件的绝对文件路径（str）。每个键的值是一个 (func_name: str, func_body: str) 2 元组的列表，该文件中定义的每个函数对应一个元组。不包含任何函数定义的文件对应一个空列表。当静态分析后端无法初始化时，返回一个空字典。

### 实际行为

执行后，若未发生异常，函数返回一个字典。设 cg = CodeGraphExtractor.from_proj_dir(proj_dir)。若 cg 不为 None，返回的字典 R 等于 cg.get_functions_by_file('python', proj_dir)；即，对于 proj_dir 下每个 Python 源文件的绝对文件路径 p，R[p] 是该文件中所有函数的 (func_name, func_body) 元组的列表。若 cg 为 None，则 R = {}。若在 from_proj_dir 或 get_functions_by_file 期间引发异常，异常将传播，batch_extract 不返回任何值。
形式逻辑：
正常终止：( cg  {CodeGraphExtractor, None}. cg = CodeGraphExtractor.from_proj_dir(proj_dir)  ( (cg  None  R = cg.get_functions_by_file('python', proj_dir))  (cg = None  R = {}) ) )。
异常终止：引发异常 E，函数栈展开。

### 为什么会认为是 Bug

规约要求项目中的每个 Python 文件都是一个键，若没有函数则为空列表。实现依赖于 get_functions_by_file，它可能只包含至少包含一个函数的文件，从而遗漏没有函数的文件。

### 如何违反规约

batch_extract 依赖于 get_functions_by_file，该函数查询 codegraph 以获取函数/方法节点；没有函数的文件不会产生任何行，并被静默地从结果字典中忽略，违反了规约中每个 Python 文件都必须是一个键的要求（如果没有函数，则为空列表）。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-128"></a>
## FMA-MISMATCH-128 — `src--pipeline_setup-py--_collapse_phases_to_one`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-128](bug_list_v7_28_zh_filter.md#fma-mismatch-128)

### 预期行为

如果 phases.json 包含至少一个阶段，则 work_dir 下的文件将被重写，使得：(1) 'phases' 数组包含且仅包含一个阶段元素；(2) 单个阶段的 'modules' 数组是按 'phase' 升序排列的所有原始阶段中每个 'modules' 数组的串联，保持每个原始阶段的 'modules' 数组内模块的相对顺序；(3) 单个阶段的 'description' 是一个字符串，通过将一个空行分隔符连接所有原始阶段按 'phase' 升序排列的去除了首尾空白后的非空描述来形成；(4) 单个阶段的 'depends_on_phases' 是一个空列表。此外，如果在 '<work_dir>/spec_prompts/domain_context/' 下存在一个或多个 'phase_*_types.txt' 文件，则它们去除首尾空白后的内容按阶段升序（用空行分隔）连接到同一目录下的 'phase_01_types.txt' 文件中，然后该目录中所有其他 'phase_*_types.txt' 文件被删除。如果 phases.json 包含零个阶段，则不会发生文件修改。

### 实际行为

如果 'phases' 列表为空，文件系统保持不变，函数立即返回。否则，在正常执行（无异常）之后：
1. 位于 phases_path（work_dir/phases.json）的文件被覆写为一个 JSON 对象，其 'phases' 键包含一个单元素列表，该列表包含一个合并后的阶段对象 M。M 拥有与原始排序列表中第一个阶段相同的键（包括其原始 'phase' 编号，该编号不一定为 1），并具有以下修改：
   - 'name' 被设置为 "Unified Analysis Phase"。
   - 'description' 是所有原始阶段中每个非空且去除首尾空白后的 'description' 字符串按排序顺序以 "\n\n" 分隔的串联。如果没有非空的，此字段存在但为空。
   - 'modules' 是一个列表，包含来自每个原始阶段的每个模块字典，保留阶段的顺序以及每个阶段内模块的顺序。
   - 'depends_on_phases' 被设置为空列表 []。
2. 在目录 work_dir/spec_prompts/domain_context 中：
   a. 令 T 为每个原始阶段（使用其 'phase' 编号，补零至两位）的路径 phase_{:02d}_types.txt 的集合。
   b. 如果至少存在一个这样的文件，则会创建（或覆写）一个文件 phase_01_types.txt，其中包含 T 中所有现有文件去除首尾空白后的内容，按顺序以 "\n\n" 分隔符和一个尾随换行符串联。该目录中匹配通配模式 "phase_*_types.txt" 的所有其他文件（包括那些不在 T 中的）均被删除，但新写入的 phase_01_types.txt 除外。在此步骤之后，匹配该模式的唯一文件是包含合并内容的 phase_01_types.txt。
   c. 如果 T 中没有文件存在，则不创建新文件且不删除任何文件；目录保持原样。
所有操作假定前置条件所要求的现有文件和目录都是可读/可写的。如果发生 I/O 错误（例如，无法写入 phases.json 或创建合并后的类型文件），函数会引发异常，且文件系统可能处于部分修改的状态。

### 为什么会认为是 Bug

规范要求合并后的描述仅为所有阶段去除首尾空白后的非空描述，并用空行连接。代码错误地在每个描述前插入了一个前缀（例如 'Phase 1 (Test): '），改变了内容。

### 如何违反规约

代码在每个描述前添加了 'Phase N (Name): ' 前缀，而不是仅用空行连接去除首尾空白后的非空描述。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-131"></a>
## FMA-MISMATCH-131 — `src--pipeline_setup-py--_domain_context_complete`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；尝试次数 `1`
- **原始详情：** [查看 FMA-MISMATCH-131](bug_list_v7_28_zh_filter.md#fma-mismatch-131)

### 预期行为

当且仅当满足以下所有条件时返回 True：(1) work_dir 包含一个有效的 phases.json 文件——一个可读、可解析的 JSON 文件，其顶层对象有一个 'phases' 数组，其中每个元素都有一个非 None 整数 'phase' 键；(2) 文件 work_dir/spec_prompts/domain_context/engine_overview.txt 存在；(3) 对于 'phases' 数组中存在的每个阶段编号 P，文件 work_dir/spec_prompts/domain_context/phase_P_types.txt 存在，其中 P 以零填充的两位整数格式表示。如果上述任一条件不满足，包括 phases.json 缺失、不可读、非有效 JSON，或其 'phases' 数组包含一个 'phase' 键缺失或为 None 的元素，则返回 False。该函数不会修改文件系统上的任何文件。

### 实际行为

文件系统状态与调用之前完全一致；没有文件被创建、修改或删除，也没有外部资源被改变。该函数要么返回 True 要么返回 False，且不引发任何异常（所有内部异常均被捕获）。该函数当且仅当满足以下所有条件时返回 True，否则返回 False：(1) 位于路径 os.path.join(work_dir, 'phases.json') 的文件存在、可读，并包含语法有效的 JSON（由 _json_file_is_valid 判定）。(2) 位于路径 os.path.join(work_dir, 'spec_prompts', 'domain_context', 'engine_overview.txt') 的文件存在。(3) 在成功打开和解析 phases.json 文件后，得到的 JSON 对象包含一个键 'phases'，其值是可迭代的，并且对于该序列中的每个元素，该元素在键 'phase' 下具有非 None 值（通常为整数），并且位于路径 os.path.join(work_dir, 'spec_prompts', 'domain_context', f'phase_{phase:02d}_types.txt') 的文件存在。形式化地：(返回值为 True) ↔ ( _json_file_is_valid(phases_path) ∧ os.path.exists(engine_overview_path) ∧ ∀ phase ∈ parse(json.load(open(phases_path))).get('phases', []), phase.get('phase') ≠ None ∧ os.path.exists(phase_types_path(phase.get('phase'))) )，其中 phases_path = os.path.join(work_dir, 'phases.json')，engine_overview_path = os.path.join(domain_dir, 'engine_overview.txt')，domain_dir = os.path.join(work_dir, 'spec_prompts', 'domain_context')，phase_types_path(n) = os.path.join(domain_dir, f'phase_{n:02d}_types.txt')。如果不满足上述任一条件，函数返回 False；例如，缺失文件、无效 JSON、缺失 'phases' 键、阶段元素缺失 'phase' 键或缺失阶段类型文件，均返回 False。只有当所有检查都通过时，第 21 行的 return 语句才会被到达。

### 为什么会认为是 Bug

如果顶层 JSON 值不是字典（例如是数组），_json_file_is_valid 返回 True，但 json.load 返回一个列表，在该列表上调用 .get 会引发一个未捕获的 AttributeError，导致函数传播异常而不是返回 False，违反了规范。

### 如何违反规约

当 phases.json 包含一个顶层 JSON 数组时，_json_file_is_valid 返回 True，但 phases_data.get() 失败并引发 AttributeError，传播异常而不是返回 False。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-132"></a>
## FMA-MISMATCH-132 — `src--pipeline_setup-py--_ensure_source_files_in_phases`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-132](bug_list_v7_28_zh_filter.md#fma-mismatch-132)

### 预期行为

当 required_source_files 为 None 或空时，返回 {'forced': [], 'augmented': {}, 'augmented_modules': []} 而不读取或修改 phases_json。否则，保证返回后 required_source_files 中的每个路径（反斜杠目录分隔符规范化为正斜杠）都会出现在 phases.json 文件中恰好一个模块的 source_files 列表中。返回一个字典，其中：'forced' 是在调用前尚未出现在任何阶段模块的 source_files 中的所需路径列表（当所有路径都已存在时为空）；'augmented' 将接收阶段（阶段编号最小的阶段）的数字阶段标识符映射到添加到它的路径列表；'augmented_modules' 列出每个接收到新文件的模块，每个条目包含模块的阶段编号、模块名称和添加的文件路径。如果 phases.json 文件最初不包含任何阶段，则创建一个编号为 1 的单一阶段，其中包含一个模块，其 source_files 列表包含 required_source_files 中的所有路径。接收模块的 description 字段会被扩展以包含一条注释，引用添加的源文件（不会重复任何已存在的描述内容）。不会删除任何现有阶段，不会丢失任何现有模块的源文件，并且预先存在的阶段编号保持不变。

### 实际行为

如果函数在不引发异常的情况下完成，则以下成立：
令 F_before 为调用前 phases_json 处文件的 JSON 内容。
- 如果 required_source_files 为假值（None 或空序列）：函数返回 {'forced': [], 'augmented': {}, 'augmented_modules': []} 并且文件不变 (F_after = F_before)。
- 否则，令 required_norm = { 将 p 中的反斜杠替换为正斜杠，其中 p 来自 required_source_files } 且 existing_norm = { 将 p 中的反斜杠替换为正斜杠，其中 p 来自 F_before 中任何阶段任何模块所列的所有 source_files }。
  - 如果 required_norm ⊆ existing_norm，函数返回相同的空字典且文件不变。
  - 否则，missing = [ sf for sf in required_source_files if sf with backslashes replaced not in existing_norm ]（保持顺序）。文件被转换：选择 F_before 中最早的阶段（按数字 'phase' 键）；如果不存在阶段，则创建一个新阶段，其 'phase': 1，名称 'Entry Points'，描述 'Entry-point source files.'，空 modules，空 depends_on_phases。在该阶段的 'modules' 列表中，如果为空，则附加一个新模块，名称为 'entry_points'，空 description，空 source_files。该列表中的第一个模块的 'source_files' 通过追加 missing 中的所有路径（保持原样，不进行标准化）来扩展，其 'description' 更新为 _merge_descriptions(old_description, 'Includes required entry-point source file(s): ' + ', '.join(missing) + '.')。不会修改其他阶段或模块。phases_json 处的文件被覆盖为生成的 JSON 对象 (F_after)。函数返回：
  {'forced': missing,
   'augmented': {earliest_phase_number: list(missing)},
   'augmented_modules': [{'phase': earliest_phase_number, 'module': name_of_first_module, 'added_files': list(missing)}]}
  其中 earliest_phase_number 是所选最早阶段的 'phase' 值。
如果发生异常（例如，文件 I/O 错误、无效 JSON），函数引发异常，并且不对返回值或文件状态做出任何保证。
正式地，对于所有正常执行：
 ∃ r 使得 ReturnValue = r ∧
  ( (required_source_files = None ∨ required_source_files = []) 
      ⇒ (r = {forced: [], augmented: {}, augmented_modules: []} ∧ file_unchanged) )
  
  ∧ ( required_source_files ≠ None ∧ required_source_files ≠ [] 
      ⇒ let req_norm = { normalize(p) | p ∈ required_source_files } in
      let exist_norm = { normalize(q) | q ∈ all_file_source_files(F_before) } in
      (req_norm ⊆ exist_norm ⇒ r = {forced: [], augmented: {}, augmented_modules: []} ∧ file_unchanged)
      
      ∧ (req_norm ⊈ exist_norm 
          ⇒ let missing = [ p ∈ required_source_files | normalize(p) ∉ exist_norm ] in
          let phases_before = F_before.phases (or [] if absent) in
          let earliest_phase = (if phases_before = [] then new_phase(1) else argmin_{p∈phases_before} p.phase) in
          let modules_after = (if earliest_phase.modules = [] then [new_module('entry_points', '', [])] else earliest_phase.modules) in
          let mod = modules_after[0] in
          let mod_desc_before = mod.description (or '' if absent) in
          let mod_files_before = mod.source_files (or [] if absent) in
          file_after = file_before with earliest_phase replaced by:
              earliest_phase[modules → modules_after[0 ↦ (mod_files_before ++ missing, description → _merge_descriptions(mod_desc_before, note))]]
              where note = 'Includes required entry-point source file(s): ' + join(missing, ', ') + '.'
           ∧ r = {forced: missing, augmented: {earliest_phase.phase: missing}, augmented_modules: [{phase: earliest_phase.phase, module: mod.name, added_files: missing}]}
           ∧ file(phases_json) = file_after
      )
  )
其中 normalize(s) = 将 s 中的所有反斜杠字符替换为正斜杠。

### 为什么会认为是 Bug

规范保证返回后每个所需源文件恰好出现在一个模块中。当所需文件已存在于多个模块中时，代码不会检测或修复此重复；它只是不加修改地提前返回。这使文件处于违反后置条件的状态。

### 如何违反规约

当所需源文件已存在于多个模块中时，代码不加去重地提前返回，使文件处于违反“恰好一个模块”后置条件的状态。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-139"></a>
## FMA-MISMATCH-139 — `src--pipeline_setup-py--_run_generate_phases`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-139](bug_list_v7_28_zh_filter.md#fma-mismatch-139)

### 预期行为

如果函数正常返回（不退出进程）：要么 plugin_stage.type 是 'pass' 或 'replace'（插件完全负责 phases.json 的输出），要么 phases.json 存在于 work_dir 下的预期路径，其中包含一个阶段列表，每个阶段有 phase number（整数）、name（字符串）、description（字符串）、modules（一个对象列表，每个对象包含 name、description 和 source_files），以及 depends_on_phases（一个整数列表，引用其他阶段的编号）。在增量模式下，现有的 phases.json 会被更新以反映当前源代码状态：添加新出现的模块和源文件，移除文件已不存在的条目，并根据需要调整阶段分配，同时保留仍然准确的条目。在子模块过滤模式下，source_files 条目仅引用指定子目录路径内的文件。如果经过 OPENCODE_MAX_RETRIES 次尝试后，phases.json 缺失、存在模式验证错误，或者在子模块模式下未能覆盖指定子目录下的当前源文件，进程会以代码 1 退出，并输出描述失败原因的诊断信息。

### 实际行为

代码块执行后，以下情况之一成立：
1. (终止) 如果 `phase_plan_ready`（在第 121130 行赋值）是 `False` 并且 `attempt >= OPENCODE_MAX_RETRIES`，程序调用 `sys.exit(1)` 并终止；不再执行后续语句。
2. (异常) 如果 `phase_plan_ready` 是 `True` 且执行了 `break` 分支，随后条件 `plugin_stage is not None and plugin_stage.type == "modify" and plugin_stage.output_process` 成立，并且由 `run_plugin_command` 执行的命令以非零代码退出，则抛出 `CalledProcessError`；代码块未正常完成。
3. (正常完成) 否则，代码块正常结束，既不终止程序也不抛出异常。在这种情况下：
   - 如果 `phase_plan_ready` 是 `True`：则已退出外层循环（通过 `break`）。之后，如果 `plugin_stage is not None and plugin_stage.type == "modify" and plugin_stage.output_process` 为真，则通过 `plugin_stage.output_process` 执行了 shell 命令 `run_plugin_command`，其中 `cwd=plugin_root`，环境变量 `FM_AGENT_PLUGIN_ROOT` 设置为 `plugin_root`，标签为 `"generate_phase_plan post-process"`，并成功完成（退出代码 0）。如果该条件为假，则未运行任何插件后处理。
   - 如果 `phase_plan_ready` 是 `False` 且 `attempt < OPENCODE_MAX_RETRIES`：则通过 `missing` 记录并输出到 stdout 一条警告信息，其中包含计算得到的 `logging.warning` 原因；`time.sleep(10)` 已完成。循环未被中断，因此控制将返回到外层循环的顶部进行下一次迭代（在此代码块之外）。
   - 代码块中引入的所有其他程序状态保持不变：`prompt`、`command`、`attempt`、`proj_dir`、`submodules`（如果存在）、`is_incremental`、`prev_mtime`、`phases_json`、`phase_plan_errors`、`OPENCODE_MAX_RETRIES`、`plugin_root`、`plugin_stage`。跟踪目录仍包含阶段 `'generate_phases_json'` 的事件，其元数据为 `{'attempt': attempt}`。
正式地，设 `ready_before = False`，并定义 `ready_after` 为：
- `submodules and _phases_cover_current_sources(phases_json, proj_dir, submodules)` 或
- `(not submodules) and is_incremental and (os.path.getmtime(phases_json) != prev_mtime or _phases_cover_current_sources(phases_json, proj_dir))` 或
- `(not submodules) and (not is_incremental)`。
定义 `exit_attempt = not ready_after and attempt >= OPENCODE_MAX_RETRIES`。
定义 `plugin_condition = (plugin_stage is not None and plugin_stage.type == "modify" and plugin_stage.output_process)`。
那么正常完成的后置条件为：
exit_attempt  (ready_after  (loop_broken  (plugin_condition  (run_plugin_command_succeeded  no_exception))) )  (ready_after  (attempt < OPENCODE_MAX_RETRIES  logged_warning  slept_10s  loop_broken))
所有其他变量保持不变，如上所述。

### 为什么会认为是 Bug

在增量模式下，规范要求更新后的 phases.json 能反映当前的源代码状态。代码使用基于 mtime 的检查作为覆盖率检查的替代方案，因此即使覆盖率不完整，只要重写了文件就会被接受为 ready，这违反了所需的保证。

### 如何违反规约

在增量模式下，第 1034-1037 行基于 mtime 的 OR 检查在覆盖率不完整时仍接受 phases.json 的重写，绕过了所需的 _phases_cover_current_sources 验证。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-146"></a>
## FMA-MISMATCH-146 — `src--plugin-py--run_plugin_command`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-146](bug_list_v7_28_zh_filter.md#fma-mismatch-146)

### 预期行为

将 cmd 作为一个 shell 子进程执行。cmd 中的相对文件路径相对于 plugin_root 解释。子进程运行时的工作目录设置为 plugin_root，环境变量 FM_AGENT_PLUGIN_ROOT 设置为 plugin_root 的字符串表示。如果命令以非零代码退出，会向 stdout 打印一条包含 label、命令字符串和退出代码的诊断信息，然后引发 subprocess.CalledProcessError。如果命令以零代码退出，函数正常返回，不报错。

### 实际行为

该函数要么在已解析的 shell 命令（相对路径在 plugin_root 下解析）在目录 proj_dir 中成功运行（退出代码为 0），且 FM_AGENT_PLUGIN_ROOT 设置为 plugin_root，未打印错误信息后返回 None；要么在向 stdout 打印包含 label、返回码和已解析命令的错误信息后引发 subprocess.CalledProcessError 异常。这两种情况下均未修改其他程序状态。形式化表述：(result = None  resolved_cmd = _resolve_command(cmd, plugin_root)  subprocess_success(resolved, proj_dir, plugin_root)  printed_error)  (exception = CalledProcessError  resolved_cmd = _resolve_command(cmd, plugin_root)  subprocess_failed(resolved, proj_dir, plugin_root, exit_code)  printed_error(resolved, exit_code, label)  exit_code  0)

### 为什么会认为是 Bug

规范要求子进程运行时工作目录设置为 plugin_root，但代码中设置了 cwd=proj_dir。对于任何 proj_dir != plugin_root 的输入，工作目录会存在差异，违反规范。例如，对于给定输入，命令 'pwd' 的输出会是 '/home/user' 而非 '/tmp/plugin'。

### 如何违反规约

当 proj_dir != plugin_root 时触发该缺陷；subprocess.run() 接收到的 cwd=proj_dir，而非规范要求的 cwd=plugin_root。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-159"></a>
## FMA-MISMATCH-159 — `src--llm_client-py--_parse_json_response`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-159](bug_list_v7_28_zh_filter.md#fma-mismatch-159)

### 预期行为

当 response 恰好包含一个 JSON 对象或数组时，通过结构解析（识别任意嵌套深度的平衡 JSON 括号对）确定，分别以 dict 或 list 形式返回该值。在以下情况下抛出 ValueError：(a) response 不是字符串；(b) 文本中不存在任何 JSON 对象或数组；(c) 文本中存在多个 JSON 对象或数组；(d) 直接全字符串解析成功，但生成的是非结构化 JSON 标量（字符串、数字、布尔值或 null），而非对象或数组。提取过程从左到右扫描整个文本；结构解析意味着包含 '{' 或 '[' 字符但不具备平衡 JSON 结构的非 JSON 文本不会产生匹配。

### 实际行为

执行后，如果 `response` 不是字符串，则抛出带有消息 'LLM 响应必须是 JSON 字符串' 的 `ValueError`。否则，令 `text = response.strip()`。如果 `json.loads(text)` 成功并返回一个 `data` 或 `dict` 类型的值 `list`，函数返回 `data`。如果 `json.loads(text)` 成功但 `data` 不是 `dict` 或 `list`，抛出带有消息 'LLM 响应必须包含 JSON 对象或数组' 的 `ValueError`。如果 `json.loads(text)` 抛出 `JSONDecodeError`（记为 `exc`），函数使用 JSON 解码器扫描 `text`，按顺序查找所有有效的 JSON 对象和数组。令 `values` 为这些找到的值的列表。如果 `len(values)` 恰好为 1，返回 `values[0]`。如果 `len(values) > 1`，抛出带有消息 'LLM 响应包含多个 JSON 值' 的 `ValueError`。如果 `len(values) == 0`，抛出带有消息 `ValueError` 并从 `'LLM response is not valid JSON: {exc}'` 链出的 `exc`。
形式化地，若 `is_str(x)` 表示 `x` 为字符串，`full_parse(s)` 在 `json.loads(s)` 成功时返回解析值，否则错误，`is_dict_or_list(v)` 表示 `v` 是 dict 或 list，且 `scan(s)` 返回按扫描算法提取的 dict/list 值的有序列表：
post_condition 
  ( is_str(response)  Raise(ValueError("LLM 响应必须是 JSON 字符串")) )
   ( is_str(response)  let t = strip(response) in
      ( (full_parse(t) = v  is_dict_or_list(v))  Return(v) )
       (full_parse(t) = v  is_dict_or_list(v))  Raise(ValueError("LLM 响应必须包含 JSON 对象或数组")) )
       (full_parse(t) =  (error)  let exc = error in
          ( |scan(t)| = 1  Return(scan(t)[0]) )
           ( |scan(t)| > 1  Raise(ValueError("LLM 响应包含多个 JSON 值")) )
           ( |scan(t)| = 0  Raise(ValueError(f"LLM response is not valid JSON: {exc}")) from exc )
      )
  )

### 为什么会认为是 Bug

扫描逻辑查找任何 '{' 或 '[' 字符，而不考虑其是否位于 JSON 字符串内部，从而导致提取出出现在带引号字符串中的有效 JSON 对象。规范要求结构解析需遵守字符串边界，因此嵌入字符串中的 JSON 对象不应视为匹配。在此反例中，代码返回 {'a': 1}，而规范将抛出 ValueError，因为不存在独立的 JSON 对象/数组。

### 如何违反规约

扫描逻辑查找 '{' 或 '[' 而未检查是否位于 JSON 字符串内，因此嵌入在带引号字符串中的 JSON 对象被错误地提取为独立值。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-164"></a>
## FMA-MISMATCH-164 — `src--opencode_trace-py--_copy_opencode_output`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-164](bug_list_v7_28_zh_filter.md#fma-mismatch-164)

### 预期行为

流已关闭；若 trace_log_path 不为 None，则在 trace_log_path 处存在一个文件，其中包含在流耗尽之前从流中读取的每个字节的拼接，该文件已关闭，其内容采用 UTF-8 编码，不可编码字符被替换；若 trace_log_path 为 None，则不创建文件；在所有执行路径下，流已关闭并且（如果已打开）跟踪日志文件已关闭，包括在读取或写入期间引发异常的情况。

### 实际行为

函数完成后（无论是正常完成还是通过未处理的异常完成），以下成立：(1) `stream` 对象已关闭。(2) 如果 `trace_log_path` 不为 `None` 并且打开文件的尝试成功，则在 `trace_log_path` 处存在一个文件，该文件已关闭，其内容等于 `stream.read(4096)` 返回的字符串的有限前缀的拼接——具体来说，是在流耗尽或发生错误之前成功读取的所有块。(3) 如果 `trace_log_path` 不为 `None` 但文件无法打开（`open()` 调用引发了异常），则该路径处的文件保持不变，并且未写入任何内容。(4) 如果 `trace_log_path` 为 `None`，则没有打开或写入任何文件。形式化：
stream.closed = True  
( (trace_log_path  None)  
    ( (  prefix P of stream_chunks : file_content(trace_log_path) = concat(P)    file_closed(trace_log_path) )
        ( file_unchanged(trace_log_path)   opened(trace_log_path) )
    )
)
其中 `stream_chunks` 是通过重复调用 `stream.read(4096)` 直到耗尽或发生异常而获得的字符串序列。

### 为什么会认为是 Bug

当流是二进制流时，stream.read(4096) 返回字节（例如 b'\xff'）。在第 10 行，代码试图将这些字节直接写入以 encoding='utf-8' 打开的文本文件。这会引发 TypeError，因为 write() 期望的是字符串而不是字节。规范要求将从流中读取的每个字节作为 UTF-8 编码文本写入文件，并替换不可编码的字符（即用 'replace' 解码字节并编码为 UTF-8）。代码未执行此转换，导致无法生成所需的文件内容，而是引发异常。

### 如何违反规约

将二进制流（BytesIO）传递给 _copy_opencode_output 会导致 trace_log.write() 引发 TypeError，因为文本模式文件期望 str 但接收到 bytes。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-166"></a>
## FMA-MISMATCH-166 — `src--opencode_trace-py--_opencode_log_path`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；尝试次数 `1`
- **原始详情：** [查看 FMA-MISMATCH-166](bug_list_v7_28_zh_filter.md#fma-mismatch-166)

### 预期行为

返回一个文件系统路径字符串，该路径位于由 work_dir 衍生的 trace 目录结构内，唯一标识给定 event_id 的日志文件；返回的路径仅从 work_dir 和 event_id 可推导出，适用于写入子进程 stdout 日志内容

### 实际行为

该函数返回一个表示文件路径的字符串。令 trace_dir = _trace_dir(work_dir) 且 payload_dir = _payload_dir(trace_dir)。返回值 ret 满足：ret == os.path.join(payload_dir, f"{event_id}_opencode.log")。返回的字符串是将 payload 目录路径与由 event_id 和后缀 '_opencode.log' 组成的文件名拼接而成，使用操作系统特定的路径分隔符。

### 为什么会认为是 Bug

规范要求返回的路径必须在 trace 目录结构内。当 event_id='../../malicious' 时，返回的路径会逃逸出 trace 目录，违反该要求。

### 如何违反规约

event_id='../../malicious' 导致 os.path.join 遍历出 trace 目录，将日志写到预期的沙箱之外。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-167"></a>
## FMA-MISMATCH-167 — `src--opencode_trace-py--_opencode_trace_path`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-167](bug_list_v7_28_zh_filter.md#fma-mismatch-167)

### 预期行为

返回一个文件系统路径字符串，在由 work_dir 派生的跟踪目录层次结构中，为给定的 event_id 唯一标识一个跟踪文件。该返回路径适合写入原始 LLM 请求/响应跟踪数据。

### 实际行为

该函数返回一个字符串，该字符串等于将 `work_dir` 的跟踪目录路径（由 `_trace_dir(work_dir)` 获得）、字面文件夹名 `'opencode'` 和文件名 `{event_id}.jsonl` 拼接而成的文件系统路径。形式上：设 `r` 为返回值；则 `r = os.path.join(_trace_dir(work_dir), 'opencode', event_id + '.jsonl')`。

### 为什么会认为是 Bug

代码未对 event_id 进行清理，允许路径遍历字符。例如，若 event_id 为 '../other'，返回的路径会解析到 'opencode' 子目录之外，且不同的 event_ids 可能映射到同一文件（如 '../other' 和 'opencode/../other' 均得出 trace_dir/other.jsonl）。这违反了规范中返回路径应在预期层次结构内为给定 event_id 唯一标识跟踪文件的要求。

### 如何违反规约

代码未对 event_id 进行清理，允许路径遍历字符（如 '../other'）生成逃逸预期 opencode/ 子目录的路径，违反了规范所要求的唯一性和包含性保证。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-171"></a>
## FMA-MISMATCH-171 — `src--opencode_trace-py--_wait_opencode_process`

- **原分类：** **可能的 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-171](bug_list_v7_28_zh_filter.md#fma-mismatch-171)

### 预期行为

阻塞直到 proc 中的进程完成或超时到期。返回一个二元组 (exit_code, error)。当进程在 timeout_seconds 内退出时：exit_code 为整数的进程退出码，error 为 None。当进程未在 timeout_seconds 内退出时：proc 被终止 (SIGTERM)，若在 10 秒宽限期内终止未完成，则强制杀死 (SIGKILL)；exit_code 为强制终止后的进程退出码，当该退出码为假值 (0 或 None) 时映射为 -15；error 为一个指示超时状况的描述性字符串。

### 实际行为

正常返回时（无未处理的异常），函数返回二元组 (ec, em)，其中 ec ∈ ℤ，em ∈ {None} ∪ {s | s == f'timeout after {timeout_seconds}s'}。子进程 subprocess.Popen 实例 proc 已回收：proc.wait() 被调用（可能在 terminate/kill 之后），因此 proc.returncode ∈ ℤ 且子进程已不在运行。若初始的 proc.wait(timeout=timeout_seconds) 正常完成而未引发 TimeoutExpired（无超时情况），则 ec = proc.returncode，em = None。若引发 TimeoutExpired（超时情况），则 em = f'timeout after {timeout_seconds}s'。在超时情况下，调用了 proc.terminate()；若随后的 proc.wait(timeout=10) 引发 TimeoutExpired，则调用 proc.kill()，然后不带超时地调用 proc.wait()。最终，除非 proc.returncode == 0，否则 ec = proc.returncode，当 proc.returncode == 0 时 ec = -15（如此，超时后被杀死而发出的成功退出码永远不会被报告为成功）。属性 proc.returncode 等于最后一次成功 wait 的实际退出状态，即使 ec 为 -15 时其值也可能为 0。

### 为什么会认为是 Bug

规范仅将强制终止 (SIGKILL) 之后的退出码映射为 -15。而代码在超时路径中无条件地将任何假值退出码映射为 -15，包括进程通过 SIGTERM 正常退出且退出码为 0 的情况。这导致了不匹配。

### 如何违反规约

超时并在 10 秒宽限期内通过 SIGTERM 正常退出（退出码 0）的子进程，其退出码被错误地重映射为 -15；-15 映射应仅在 SIGKILL 之后适用。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-177"></a>
## FMA-MISMATCH-177 — `src--opencode_trace-py--run_opencode_traced`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-177](bug_list_v7_28_zh_filter.md#fma-mismatch-177)

### 预期行为

当子进程以代码 0 退出且无错误时：返回一个 returncode=0 的 subprocess.CompletedProcess。当子进程以非零代码退出或发生错误时：引发 subprocess.CalledProcessError，其 returncode 等于子进程退出码。在每一条执行路径（成功、失败或异常）中，恰好一条结构化事件记录被原子性地追加到从 work_dir 派生的 trace 目录下的 events.jsonl 文件中。记录的事件包含：唯一的 event_id、stage 标签、覆盖整个执行窗口的 ISO 8601 开始和结束时间戳、完整的命令列表、进程退出码、状态为 "success"（exit_code=0 且无错误）或 "error"（exit_code≠0 或存在错误）、提供的 function_ids、input_files、output_files、summary、error 和 metadata 值，以及对应的 opencode 日志和跟踪文件路径。所有后台线程（日志流和标准输入馈送）在此函数正常返回或传播异常之前均被 join 并终止。

### 实际行为

run_opencode_traced 执行后，无论它是正常返回还是引发异常，以下均成立。形如 "opencode_<hex_uuid>" 的事件标识符 event_id 已生成，两个 ISO 8601 UTC 时间戳 started 和 ended 已捕获，且 ended >= started。调用 record_opencode_call(work_dir=work_dir, event_id=event_id, stage=stage, status='success' if exit_code == 0 else 'error', started=started, ended=ended, command=command, function_ids=function_ids, input_files=input_files, output_files=output_files, exit_code=exit_code, summary=summary, error=error, metadata=metadata, opencode_log_path=_opencode_log_path(work_dir, event_id), opencode_trace_path=_opencode_trace_path(work_dir, event_id)) 精确执行一次，将对应的 JSON 事件记录原子性地追加到从 work_dir 派生的 trace 目录下的 events.jsonl 中。exit_code 和 error 的值反映最终结果：如果 _wait_opencode_process 设置了 exit_code 和 error，则 exit_code 是整数进程退出码，error 是字符串或 None；如果引发了 subprocess.CalledProcessError，则 exit_code 是 exc.returncode，error 是 error 或 str(exc)；否则 exit_code 保持 0，error 为 None。任何非 None 的 log_thread 或 stdin_thread 都已被 join（如果在 finally 块中仍存活，则等待其完成），确保位于 opencode_log_path 的日志文件被完全写入并关闭。如果 _start_opencode_process 未引发异常而完成，子进程 proc 已终止，其退出码得到反映。该函数要么正常返回一个 subprocess.CompletedProcess 实例，其 args 为 command_argv(command)，returncode 为 exit_code（在此情况下始终为 0），要么传播一个异常，该异常在检测到 error 或非零 exit_code 时始终为 subprocess.CalledProcessError，或是子进程管理产生的任何其他异常。在所有情况下，除了显式创建的文件（日志、跟踪和事件记录）外，work_dir 和 proj_dir 不被修改。

### 为什么会认为是 Bug

代码仅通过与 0 比较 exit_code 来决定事件状态。规格要求当 exit_code≠0 或存在错误时状态为 'error'。此处进程以代码 0 退出，但 _wait_opencode_process 报告一个错误字符串，因此状态应为 'error'，而非 'success'。

### 如何违反规约

当子进程以代码 0 退出但 _wait_opencode_process 报告错误字符串时，事件状态被记录为 'success' 而非 'error'，因为状态逻辑仅检查 exit_code==0，完全忽略了 error 参数。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-182"></a>
## FMA-MISMATCH-182 — `src--trace_writer-py--append_event`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-182](bug_list_v7_28_zh_filter.md#fma-mismatch-182)

### 预期行为

以线程安全的方式将事件字典作为自包含的 JSON 单行（以换行符结束）追加到位于 trace_dir 内的 events.jsonl 文件中。写入的 JSON 保留所提供事件字典中的每一个顶级键。该函数不修改事件字典参数。如果 trace_dir 目录层级不存在，则在写入之前创建。在文件系统写入失败（例如磁盘已满、权限被拒绝）时，OSError 将传播给调用者。

### 实际行为

正常执行：函数返回 None。锁 `_LOCK` 被获取并释放。文件 `os.path.join(trace_dir, 'events.jsonl')` 追加了新的一行，包含 `json.dumps(event, ensure_ascii=False) + '\n'`。目录 `trace_dir` 存在（如有必要由 `_ensure_trace_dirs` 创建）。
异常路径：
- `_ensure_trace_dirs` 抛出 `OSError`：函数以 `OSError` 退出。未获取锁。未发生文件写入。对事件文件无副作用。
- `json.dumps` 抛出 `TypeError`：函数以 `TypeError` 退出。trace 目录可能已被创建（如果 `_ensure_trace_dirs` 成功），但未获取锁，也未发生文件写入。
- 文件操作（`open` 或 `write`）在持有锁时抛出 `OSError`：锁被释放（由 `with` 语句保证）。trace 目录存在（如需要已创建）。文件可能已部分写入或未更改；不保证原子性。`OSError` 传播。
形式化：
post  
  (returns None  
   directory_exists(trace_dir)  
   appended_line(file_path, json.dumps(event, ensure_ascii=False) + '\n')  
   lock_released(_LOCK))
   raises OSError from _ensure_trace_dirs (no file modifications)
从 json.dumps 引发 TypeError（目录可能存在，未修改文件）
   raises OSError from file I/O (directory exists, lock released, file state undefined)

### 为什么会认为是 Bug

代码无条件地对输入字典调用 json.dumps(event)。如果事件字典包含一个不是有效 JSON 键的顶级键（例如 tuple），json.dumps 会抛出 TypeError。规范（B）只允许在文件系统写入失败时传播 OSError，未考虑 TypeError。输入 event={(1,2): 'value'} 是一个有效的字典，但代码的行为（抛出 TypeError）违反了指定的后置条件，该条件不包含此异常结果。

### 如何违反规约

传入带有非字符串键（例如 tuple）的事件字典会导致 json.dumps 抛出 TypeError，这在规范中未文档化。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-192"></a>
## FMA-MISMATCH-192 — `src--file_utils-py--_get_incomplete_verification_files`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；尝试 `1`
- **原始详情：** [查看 FMA-MISMATCH-192](bug_list_v7_28_zh_filter.md#fma-mismatch-192)

### 预期行为

返回一个列表，包含来自 layer_files 中需要进一步处理的文件路径，保留原始输入顺序。一个文件需要进一步处理，如果 (a) 其对应的验证结果文件 '<output_dir>/<file_without_extension>.json' 无法作为有效的 JSON 读取（文件缺失、不可读或不是有效的 JSON），或者 (b) 验证结果有一个顶层 'verdict' 键等于字符串 'MISMATCH' 并且对应的 bug 验证结果文件 '<work_dir>/bug_validation/<bug_id>.result.json' 不是由 _json_file_is_valid 确定的有效 JSON 文件，其中 bug_id 是从相对路径派生而来，通过将每一个出现的 '/' 和 os.sep 替换为 '--'。具有可读的验证结果且其 'verdict' 不是 'MISMATCH' 的文件将被排除在返回的列表之外。

### 实际行为

正常执行后，函数返回一个列表 `incomplete`，该列表是 `layer_files` 中元素的子序列（按迭代顺序）。对于 `rel` 中的每个相对路径 `layer_files`，`rel` 被包含在 `incomplete` 中当且仅当满足以下任一条件：(a) `os.path.join(output_dir, os.path.splitext(rel)[0] + '.json')` 处的文件不存在、无法打开读取或包含语法无效的 JSON；或 (b) 该文件存在、可读、包含有效的 JSON，加载的对象具有 `result.get('verdict') == 'MISMATCH'`，并且路径 `os.path.join(work_dir, 'bug_validation', (os.path.splitext(rel)[0].replace(os.sep, '--').replace('/', '--')) + '.result.json')` 处的 bug 验证文件根据 `_json_file_is_valid` 无效（即，它不存在、不可读或包含无效的 JSON）。`layer_files` 中的所有其他元素被省略。如果发生任何未处理的异常（例如，来自 `os` 操作），函数可能引发异常而不返回值。形式逻辑：令 L 为遍历 `layer_files` 获得的元素序列。那么返回的列表 `incomplete` 满足：`incomplete = [ rel for rel in L | ( let P = os.path.join(output_dir, os.path.splitext(rel)[0] + '.json') in ( (P exists  P readable  P contains valid JSON) ) )  ( P exists  P readable  P contains valid JSON  let result = load_json(P) in result.get('verdict') = 'MISMATCH'  let bug_id = os.path.splitext(rel)[0].replace(os.sep, '--').replace('/', '--') in _json_file_is_valid(os.path.join(work_dir, 'bug_validation', bug_id + '.result.json')) ) ]`

### 为什么会认为是 Bug

规范要求 bug_id 从相对路径派生，通过将每个 '/' 和 os.sep 替换为 '--'，而不移除文件扩展名。代码使用 os.path.splitext 在替换前剥离扩展名，导致检查不同的 bug 验证文件路径。当规范路径存在且有效，但代码路径缺失时，代码错误地将文件包含在不完整列表中，违反了规范。

### 如何违反规约

代码使用 os.path.splitext 在构建 bug_id 前剥离文件扩展名，但规范要求包含扩展名；当 bug 验证结果存在于规范路径但不在代码的 splitext 派生路径时，函数会错误地将该条目标记为不完整。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-193"></a>
## FMA-MISMATCH-193 — `src--file_utils-py--_get_phase_files`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-193](bug_list_v7_28_zh_filter.md#fma-mismatch-193)

### 预期行为

返回属于指定 phase 的所有提取函数文件的文件标识符（相对于 input_dir 的相对路径）列表。每个标识符都是一个非元数据 sidecar 文件的常规文件的相对路径。返回列表中不得出现重复的文件标识符。每个提取目录中的文件按其名称的字典顺序升序返回。派生提取目录在磁盘上不存在的源文件将被跳过，不会引发错误。

### 实际行为

如果前置条件成立且 phases_data 格式良好，函数将返回在所选 phase 的源文件对应的提取目录中找到的常规非元数据文件的相对文件路径列表（相对于 input_dir）。对于该 phase 中的每个 module 及每个 module 中的每个源文件，构建 extracted_dir = os.path.join(input_dir, os.path.dirname(src_file), subdir)，其中 subdir 是基名，如果存在最后一个点号则将其替换为 '-'，否则保持不变。如果该目录存在，则通过 os.walk 递归遍历，按字母文件名顺序收集常规文件的路径（排除 _is_metadata_sidecar 返回 True 的文件），并将它们的相对路径追加到结果中。顺序保持 module/source-file 迭代顺序，并在每个目录内按字母文件名顺序排列。结构假设被违反（缺失键、不可迭代的值、错误的类型）将导致 KeyError、TypeError、AttributeError 或 StopIteration。如果同一文件在多个目录中遇到，返回的列表可能包含重复的相对路径。形式化逻辑：R = concatenation_{m in modules} concatenation_{s in m['source_files']} [ os.path.relpath(os.path.join(root, fname), input_dir) for (root, _, fnames) in sorted(os.walk(extracted_dir(s))) for fname in sorted(fnames) if os.path.isfile(os.path.join(root, fname)) and not _is_metadata_sidecar(fname) ]，其中 extracted_dir(s) 如上定义。

### 为什么会认为是 Bug

该代码从未去除重复项。如果同一提取目录被访问多次（例如，因为 source_files 包含重复条目），则同一个相对路径会被多次追加。规范禁止任何重复的文件标识符。

### 如何违反规约

source_files 中的重复条目导致同一提取目录被多次访问，从而将完全相同的相对路径追加到结果列表中，且未进行去重。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-198"></a>
## FMA-MISMATCH-198 — `src--file_utils-py--_json_file_is_valid`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；尝试 `1`
- **原始详情：** [查看 FMA-MISMATCH-198](bug_list_v7_28_zh_filter.md#fma-mismatch-198)

### 预期行为

当 file_path 处的文件存在于文件系统中、可以打开以供读取，且其全部内容构成语法有效的 JSON 时，返回 True。当文件不存在、无法打开以供读取，或其内容不是语法有效的 JSON 时，返回 False。绝不引发异常；每一个错误条件（包括文件缺失、权限不足无法读取以及格式错误的 JSON）都会被捕获，并导致返回 False。

### 实际行为

执行后，该函数返回一个布尔值。若为 True，则 `path` 处的文件在调用时存在、可读，且包含语法有效的 JSON；若为 False，则文件不存在、不可读、不包含有效 JSON，或发生了其他 OS/JSON 错误。文件已关闭且未修改。形式化表述为：令 result = _json_file_is_valid(p)。则 (result = True) ⇔ (exists_file(p) ∧ readable(p) ∧ valid_json(contents(p)))，且 (result = False) ⇔ ¬(exists_file(p) ∧ readable(p) ∧ valid_json(contents(p))) ∨ raised(OSError ∨ JSONDecodeError)。估值在调用时刻被快照。

### 为什么会认为是 Bug

代码仅捕获 OSError 和 json.JSONDecodeError。以文本模式打开文件（第 3 行）时，如果文件内容无法被默认编码解码，可能会引发 UnicodeDecodeError。该异常未被捕获，因此函数引发异常，而不是按规范要求返回 False（‘绝不引发异常；每一个错误条件……都会被捕获，并导致返回 False’）。

### 如何违反规约

以文本模式打开包含非 UTF-8 字节的文件会引发 UnicodeDecodeError，而该异常未被 except (OSError, json.JSONDecodeError) 子句捕获。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-225"></a>
## FMA-MISMATCH-225 — `src--incremental_reasoner-py--_llm_check_caller_info_update`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-225](bug_list_v7_28_zh_filter.md#fma-mismatch-225)

### 预期行为

当能做出一致性判定时返回一个字典。返回的字典有键 'info_updated' (bool)。当 info_updated 为 true 时，字典还包含键 'new_info'，其值是一个符合 .info.json 模式的字典。在该 new_info 字典中，除 name 等于 callee_name 的项外，每条 callee 项的 'signature'、'pre_condition' 和 'post_condition' 值都与 caller_info_block 中的对应项相同；name 等于 callee_name 的项所具有的前置条件和后置条件不与 callee_new_spec 的前置条件或后置条件中的任何断言矛盾。当 info_updated 为 false 时，caller_info_block 中 callee_name 对应的项已经与 callee_new_spec 一致，无需修订。当无法做出判定时返回 None。

### 实际行为

成功执行时，该函数委托 _llm_select_json 并返回其结果。除 _llm_select_json 可能产生的副作用（可能包括一次 LLM 调用）外，不产生其他副作用。如果参数 work_dir、comment_prefix 和 proj_dir 的所有隐式前置条件均满足（work_dir 是有效目录路径，comment_prefix 是字符串等），则不抛出异常。
令 result = _llm_check_caller_info_update(proj_dir, work_dir, idx, caller_fqn, callee_name, lang_key, comment_prefix, callee_new_spec, caller_info_block, caller_source)。
自然语言描述：函数返回 None 或一个字典。如果所配置的 LLM 生成的响应是有效的 JSON，符合模式 {"info_updated": boolean, "new_info": object|null}，并通过了 _validate_caller_info_update 验证器的检查，则 result 为该解析后的字典；否则 result 为 None。
形式逻辑：
( result = None )
( result  Dict  hasKeys(result, {"info_updated", "new_info"}) 
  result["info_updated"]  Bool 
  ( result["new_info"] = None  result["new_info"]  Dict )
    alt_result ( alt_result = _llm_select_json(...)  (alt_result = None  result = None)  (alt_result  None  result = alt_result) )
)
（最后一个合取项表明 result 恰好是 _llm_select_json 的返回值。）

### 为什么会认为是 Bug

该函数仅经过结构验证后无条件返回 _llm_select_json 的结果。它并不验证返回的字典是否满足规范所要求的语义约束（例如，当 info_updated 为 false 时现有条目是否真的是一致，或当 info_updated 为 true 时 new_info 是否保留了其他 callee 条目并使指定条目变为一致）。LLM 可能生成结构上合法但违反这些约束的响应，而该函数会将其原样交付，从而破坏 Condition B。

### 如何违反规约

_llm_select_json 的结果仅经过 _validate_caller_info_update 的结构检查即通过，没有语义验证去确认其他 callee 条目得到保留或指定的 callee 条目与新 spec 一致。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-244"></a>
## FMA-MISMATCH-244 — `src--incremental_reasoner-py--check_last_run_existence`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-244](bug_list_v7_28_zh_filter.md#fma-mismatch-244)

### 预期行为

当且仅当以下所有条件同时满足时返回 True：(a) proj_dir/fm_agent/phases.json 作为常规文件存在；(b) proj_dir/fm_agent/extracted_functions/ 作为目录存在，并且至少包含一个非 sidecar 功能文件；(c) 在 extracted_functions/ 下找到的每个非 sidecar 功能文件（当提供了 submodules 时，限制为那些其相对路径至少以一个 submodule 路径开头并跟随分隔符的文件）都拥有有效的 .spec.json 和 .info.json sidecar。如果条件 (a)、(b) 或 (c) 中的任何一个不满足，则返回 False，表明上一次运行不完整，不是增量分析的可靠基础。文件名匹配元数据 sidecar 命名模式（后缀为 .spec.json 或 .info.json）的文件不计入功能文件数量和就绪检查。该函数没有副作用：它仅从磁盘读取。

### 实际行为

当且仅当 (1) 文件 <proj_dir>/fm_agent/phases.json 存在，(2) 目录 <proj_dir>/fm_agent/extracted_functions 存在，(3) 在 extracted_functions 目录树中至少存在一个不是元数据 sidecar（即，不以 .spec.json 或 .info.json 结尾）的常规文件，并且当提供了 submodules 时，其从 extracted_functions 起的相对路径以其中一个 submodule 路径开头，并且紧接着是一个正斜杠，以及 (4) 每个这样的文件 f 都满足 is_file_ready(f)（即，f.spec.json 和 f.info.json 都作为具有所需模式的、可访问的、有效的 JSON 文件存在）时，函数返回 True。否则，函数返回 False。形式化表示：令 work_dir = proj_dir + '/fm_agent'，extracted_dir = work_dir + '/extracted_functions'。令 E = { f | f 是 extracted_dir 下（递归地）的一个文件并且不是 sidecar(f) }。定义 E' = 如果 submodules 为 None 则为 E，否则为 { f in E | is_under_submodules(relpath(f, extracted_dir), submodules) }。返回值 V 满足 V  ( is_file(work_dir + '/phases.json')  is_dir(extracted_dir)  E'     f  E' : ready(f) )。

### 为什么会认为是 Bug

规范（条件 B）将条件 (b)（至少存在一个非 sidecar 功能文件，不限制位置）与条件 (c) 中基于 submodule 的限制分离开来。代码通过第 31-35 行，要求所选 submodules 内至少有一个就绪的功能文件，这要求更为严格。当提供了 submodules 但没有文件匹配它们，而此时在其他位置存在就绪文件时，代码返回 False，而规范预期返回 True。

### 如何违反规约

当提供了 submodules，但没有提取出的功能文件位于任何指定的 submodule 路径下，而文件存在其他位置时，代码返回 False（在 saw_function 计数之前应用了 submodule 过滤器），但规范预期为 True（条件 b 仅要求任何文件无条件存在）。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-248"></a>
## FMA-MISMATCH-248 — `dashboard-py--State::_ingest_event`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-248](bug_list_v7_28_zh_filter.md#fma-mismatch-248)

### 预期行为

self 反映已按顺序摄入的全部事件的累积内容，现在包括 ev。self.first_event_time 等于所有摄入事件中最早可解析的 start_time（如果没有则为 None）。self.last_event_time 等于所有摄入事件中最晚可解析的 end_time（如果没有则为 None）。self.stage_counts[stage][status] 等于所有摄入事件中具有该 (stage, status) 对的事件计数。对于每个 ev['type'] 为 'llm_call' 的事件：self.totals 反映所有 LLM call 事件的输入、输出、缓存读取和缓存写入 token 数量的总和；self.cost_native 反映按每个 LLM call 事件计算的累积成本；self.cache_window 包含每个总输入 token 超过零的 LLM call 事件恰好一个 (cache_read, total_input) 对，按摄入顺序追加；每个事件最多递增 self.verification_success、self.verification_mismatch 或 self.verification_error 中的一个，由该事件的状态及其 purpose 是否为 'check_post_implies_spec' 决定；为事件追加一条 recent-event 条目和一条 LLM-status 条目，携带该事件的时间戳、stage、status 和 purpose。对于每个 ev['type'] 为 'opencode_call' 的事件：为事件追加一条 recent-event 条目，携带该事件的时间戳、stage、status 和 summary。追加的条目在连续摄入过程中保持发生顺序。

### 实际行为

在 `_ingest_event` 正常执行后（无未处理异常），对象 `self` 满足以下情况。
设 `pre` 表示调用前立即的对象状态，`post` 表示调用后立即的状态。设 `stage = ev.get("stage", "?")`，`status = ev.get("status", "?")`，`et = ev.get("type")`。设 `start = _parse_iso(ev.get("start_time"))`，`end = _parse_iso(ev.get("end_time"))`。
1. 最早/最晚时间更新：
   - 如果 `post.first_event_time = start` 不为 None 且（`start is not None` 为 None 或 `pre.first_event_time is None`），则 `start < pre.first_event_time`，否则保持 `pre.first_event_time`。
   - 如果 `post.last_event_time = end` 不为 None 且（`end is not None` 为 None 或 `pre.last_event_time is None`），则 `end > pre.last_event_time`，否则保持 `pre.last_event_time`。
2. 阶段计数器：
   - `post.stage_counts[stage][status] = pre.stage_counts[stage][status] + 1`。
3. 根据事件类型进行条件处理：
   (A) 如果 `et == "llm_call"`：
        设 `md = ev.get("metadata", {})`，`model = md.get("model")`。
        a. 如果 `post.model_seen = model` 为真值且 `model` 为真，则 `not pre.model_seen`，否则保持 `pre.model_seen`。
        b. 设 `usage = md.get("usage") or {}`。如果 `usage` 非空：
              通过 Anthropic/OpenAI 形状检测计算 token 计数：
                - `inp0 = usage.get("input_tokens", 0) or 0`
                - `out0 = usage.get("output_tokens", 0) or 0`
                - `cr0  = usage.get("cache_read_input_tokens", 0) or 0`
                - `cw0  = usage.get("cache_creation_input_tokens", 0) or 0`
              如果 `inp0, out0, cr0, cw0` 都不为真（全为零/假值）：
                - `inp1 = usage.get("prompt_tokens", 0) or 0`
                - `out1 = usage.get("completion_tokens", 0) or 0`
                - `hit  = usage.get("prompt_cache_hit_tokens")`
                - 如果 `hit is not None`：`cr1 = hit`；`inp1 = usage.get("prompt_cache_miss_tokens", inp1 - hit)`。
                - 否则：`cr1 = 0`；`inp1 = inp1`。
                - 设置 `inp = inp1`，`out = out1`，`cr = cr1`，`cw = 0`。
              否则：
                - 设置 `inp = inp0`，`out = out0`，`cr = cr0`，`cw = cw0`。
           然后更新合计值：
                - `post.totals["input"] = pre.totals["input"] + inp`
                - `post.totals["output"] = pre.totals["output"] + out`
                - `post.totals["cache_read"] = pre.totals["cache_read"] + cr`
                - `post.totals["cache_write"] = pre.totals["cache_write"] + cw`
                - `post.cost_native = pre.cost_native + _cost_from_usage(model, usage)`
                - 设 `total_in = inp + cr + cw`。如果 `total_in > 0`：
                     `post.cache_window = pre.cache_window + [(cr, total_in)]`
                  否则 `post.cache_window` 不变。
           否则（`usage` 为空/假值）：totals、cost_native 和 cache_window 不变。
        c. 验证计数器：
                如果 `status == "success"` 且 `md.get("purpose") == "check_post_implies_spec"`：
                     `post.verification_success = pre.verification_success + 1`
                否则如果 `status == "mismatch"`：
                     `post.verification_mismatch = pre.verification_mismatch + 1`
                否则如果 `status == "error"`：
                     `post.verification_error = pre.verification_error + 1`
                否则：验证计数器不变。
        d. Summary：`summary = ev.get("summary") or md.get("purpose") or "llm_call"`。
        e. 时间线追加：
                - 用时间戳 `post._push_recent`、stage、status 和 summary 调用 `end or start`。这会向 recent-event 时间线追加一条新条目。
                - 用时间戳 `post._push_llm_status`、来源 `end or start`、标签 `"direct"`、status、model、代码 `md.get("purpose") or summary` 和详细信息 `_llm_code_for_event(status)` 调用 `md.get("error")`。这会向 LLM-status 时间线追加一条新条目。
   (B) 如果 `et == "opencode_call"`：
        a. `summary = ev.get("summary") or "opencode_call"`。
        b. 用时间戳 `post._push_recent`、stage、status 和 summary 调用 `end or start`，追加到 recent-event 时间线。
        c. 不进行其他属性修改（model_seen、totals、验证计数器等保持为 pre）。
   (C) 其他情况（et 不在 {"llm_call", "opencode_call"} 中）：
        只应用 (1)(2) 描述的最早/最晚时间和阶段计数器更改；不进行进一步修改。
所有时间线序列（recent-events 和 LLM-status）在调用相应 push 方法时各扩展一个元素，保留之前的条目。

### 为什么会认为是 Bug

规范要求验证计数器仅在 purpose 为 'check_post_implies_spec' 时递增，但这些分支无条件递增 self.verification_mismatch 和 self.verification_error，因此一个非验证 llm_call 事件如果状态为 'mismatch' 或 'error'，会错误地递增相应的计数器。

### 如何违反规约

状态为 'mismatch' 或 'error' 的非验证 llm_call 事件会错误地递增验证计数器，因为 mismatch 和 error 分支缺少 purpose 检查（只有 success 分支检查了 purpose == 'check_post_implies_spec'）。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-252"></a>
## FMA-MISMATCH-252 — `dashboard-py--State::scan_bugs`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-252](bug_list_v7_28_zh_filter.md#fma-mismatch-252)

### 预期行为

self.bugs_confirmed、self.bugs_not_confirmed 和 self.bugs_pending 会根据 self.bug_dir 的当前状态更新。当该目录存在时，会对每个 .result.json 文件进行分类：若文件的 confirmation_status（不区分大小写）中包含子字符串 ‘confirm’ 且不包含 ‘not’，则 bugs_confirmed 自增；任何其他文件则使 bugs_not_confirmed 自增。self.bugs_pending 取 max(0, completed_bug_validation_stages − (bugs_confirmed + bugs_not_confirmed))。当 self.bug_dir 不存在时，这三个计数器均为零。

### 实际行为

执行后，属性 `self.bugs_confirmed`、`self.bugs_not_confirmed` 和 `self.bugs_pending` 会按以下规则更新，且不会修改其他属性。设 `E` 为方法执行前的 `self.bug_dir.exists()`。如果 `E`，则 `self.bugs_confirmed = 0`、`self.bugs_not_confirmed = 0` 和 `self.bugs_pending = max(0, bv_done)`，其中 `bv_done = sum(self.stage_counts.get('bug_validation', {}).values())`（使用原始值）。如果 `E`，定义：
- `F` = { p : p  self.bug_dir.glob('*.result.json') }（与该模式匹配的文件路径集合）
- `S` = { p  F : 打开并解析 `p` 作为 JSON 成功，且不引发任何异常 }
- 对于每个 `p  S`，令 `status(p)` = `(d.get('confirmation_status') or '').lower()`，其中 `d` 是解析后的 JSON 对象
- `C` = { p  S : 'confirm'  status(p)  'not'  status(p) }
- `N` = `S \ C`
然后：
`self.bugs_confirmed = |C|`
`self.bugs_not_confirmed = |N|`
`bv_done` = `self.stage_counts.get('bug_validation', {})` 中值的总和（以方法入口时的值为准）
`self.bugs_pending = max(0, bv_done - |S|)`。
即 `bugs_confirmed` 用于计数那些经解析且其 confirmation_status 的小写形式包含 “confirm” 但不包含 “not” 的文件；`bugs_not_confirmed` 用于计数其余已解析的文件（包含 “not” 或两者皆无的文件）；`bugs_pending` 取零与 ‘bug_validation’ 阶段计数值之和（若缺失则为 0）减去成功解析的结果文件总数所得差值的最大值。

### 为什么会认为是 Bug

当目录不存在时，代码会提前返回，而未将 self.bugs_pending 设为零。条件 A（实际行为）导致 self.bugs_pending 取 max(0, bv_done)（或保留其之前的值），而条件 B 明确要求这三个计数器都必须为零。

### 如何违反规约

当 self.bug_dir 不存在时，scan_bugs() 提前返回而未将 self.bugs_pending 重置为零，导致残留一个旧值。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-272"></a>
## FMA-MISMATCH-272 — `src--reasoner-py--_compute_brace_depth_per_line`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-272](bug_list_v7_28_zh_filter.md#fma-mismatch-272)

### 预期行为

返回一个与 lines 长度相同的整数列表。对于每个索引 i，位置 i 处的元素等于在 lines[0] 到 lines[i] 的合并文本中，未匹配的 '{' 字符净计数减去未匹配的 '}' 字符净计数，其中，出现在任何双引号字符串字面量、单引号字符字面量、行注释（从 '//' 到行尾）或块注释（位于 '/*' 和 '*/' 之间）内部的 '{' 和 '}' 均不计入，无论注释是否跨行。第一行之前的初始深度为 0。

### 实际行为

该函数返回列表 'depths'，使得 len(depths) == len(lines)，并且对于每个从 0 到 len(lines)-1 的索引 i，depths[i] 是按照以下规则处理 lines[0..i] 后的大括号深度：初始深度为 0；对于每一行，从左到右扫描字符，并且任何属于双引号字符串字面量（以未转义的 '"' 开始和结束，反斜杠转义跳过下一个字符）、单引号字符字面量（同理）、行注释（以 '//' 开始直到行尾）或块注释（以 '/*' 开始并在同一行以 '*/' 结束，或者如果未闭合，则为该行剩余部分）的字符均被忽略。未被忽略的 '{' 使深度加 1，未被忽略的 '}' 使深度减 1。depths[i] 是第 i 行末尾的深度。跨行块注释不被识别；各行独立处理。

### 为什么会认为是 Bug

该代码独立处理每一行，不跨行携带块注释状态，因此位于多行块注释内部的大括号不会被忽略，违反了要求所有块注释内部的大括号均需排除（无论是否跨行）的规范。

### 如何违反规约

多行块注释不会跨行追踪，因此跨越多个行的 /* ... */ 内部的大括号被当作真实大括号计数，而非被排除。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-284"></a>
## FMA-MISMATCH-284 — `src--scope-py--_llm_rerank`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-284](bug_list_v7_28_zh_filter.md#fma-mismatch-284)

### 预期行为

成功时：返回一个函数名字符串列表，顺序由 LLM 评估的与 issue 相关性决定，其长度至多为 top_k，且无重复名称。每一个返回的名称都出现在 funcs_info 中。失败时（在 3 次尝试后，LLM 响应不是有效的非空函数名字符串的 JSON 数组）：返回 None。初始 LLM 调用包含格式化的函数列表、filepath、issue 和 top_k；当响应不是有效的非空字符串 JSON 数组时，最多会进行两次额外重试，并在会话后追加纠正指令，每次重试之间伴有递增的退避延迟。该函数不抛出异常；所有尝试中的错误均被捕获，并导致要么重试，要么返回 None。

### 实际行为

该函数要么返回一个从 LLM 响应中的有效 JSON 数组解析出的非空字符串列表（函数名），要么在所有三次尝试均失败时返回 None。输入参数保持不变。所有异常均在内部捕获，不会传播。副作用（日志记录、休眠、本地消息列表修改）不影响调用方。形式化后置条件：(返回值为 None)  (返回值为一个字符串列表   返回值中的 s，isinstance(s, str)  s.strip() != '')。列表可以为空。如果返回，该列表源自三次尝试内首次成功的 LLM 调用，该调用响应中包含一个可解析的字符串 JSON 数组，且每个字符串非空。否则，在三次失败尝试后，返回 None。

### 为什么会认为是 Bug

代码仅确保响应是非空字符串的 JSON 数组。它并未检查返回列表的长度  top_k、是否包含重复项、或是否仅包含 funcs_info 中存在的名称，上述任何一条违反都将违背规格说明。

### 如何违反规约

Mock LLM 在 top_k=2 时返回 4 个函数名，超出长度限制 —— 该函数未经校验便返回全部 4 个。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-301"></a>
## FMA-MISMATCH-301 — `src--generate_topdown_layers-py--_get_call_regex`

- **原分类：** **可能有 Bug**
- **Validator：** `confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-301](bug_list_v7_28_zh_filter.md#fma-mismatch-301)

### 预期行为

返回一个编译的正则表达式。当应用于已去除注释的源代码时，每次匹配的第一个捕获组会生成一个裸词标识符，该标识符在由 lang_key 标识的语言的语法调用位置处位于左括号 '(' 之前。语言允许的位于标识符和括号之间的任何类型参数语法（例如，尖括号分隔或方括号分隔的泛型参数）均被容忍。标识符、可选类型参数和括号之间允许存在空格。

### 实际行为

返回一个编译的正则表达式（re.Pattern），用于匹配由 lang_key 给定的语言中的函数调用点。返回的正则表达式将函数名捕获到组 1 中，并确保其后跟着一个左括号。具体的模式取决于 lang_key：对于 'cpp'、'c'、'java'、'typescript'、'javascript'、'cuda'、'arkts'，它包含可选的模板参数 `<...>`；对于 'rust'，它包含可选的 turbofish `::<...>`；对于 'go'，它包含可选的类型参数 `[...]`；对于任何其他的 lang_key（例如 'python'、'ruby'），它匹配一个普通标识符，后跟可选的空格和 '('。形式上：令 L = {'cpp','c','java','typescript','javascript','cuda','arkts'}，则 (lang_key  L)  return = re.compile(r"\\b(\\w+)\\s*(?:<[^>]*>)?\\s*\(")  (lang_key = 'rust')  return = re.compile(r"\\b(\\w+)\\s*(?:::<[^>]*>)?\\s*\(")  (lang_key = 'go')  return = re.compile(r"\\b(\\w+)\\s*(?:\\[[^\\]]*\\])?\\s*\(")  (lang_key  L  {'rust','go'})  return = re.compile(r"\\b(\\w+)\\s*\(")。

### 为什么会认为是 Bug

这些正则表达式模式使用了 [^>]* 和 [^\]]*，它们不允许 C++、Java、Rust、Go 等语言中典型的模板/泛型参数嵌套括号，因此无法匹配像 foo<A<B>>(x) 这样带有嵌套类型参数的有效调用点。

### 如何违反规约

正则表达式模式使用了 [^>]* 和 [^\]]*，在模板/泛型参数中遇到嵌套括号时会失败（例如 foo<A<B>>(x)）。

### 判读建议

**保留为实现缺陷候选。** 先确认触发条件在真实调用链中可达并评估影响面；若可达，建议按预期行为修复并把现有 probe 转为回归测试；若只能通过越界 mock 或违反前置条件的输入触发，则应降级并修订 SPEC。

---

<a id="review-310"></a>
## FMA-MISMATCH-310 — `src--verification-py--_validate_single_bug`

- **原分类：** **可能有 Bug**
- **Validator：** `not_confirmed`；attempts `1`
- **原始详情：** [查看 FMA-MISMATCH-310](bug_list_v7_28_zh_filter.md#fma-mismatch-310)

### 预期行为

当对应于 result_json_rel 的差异的结果标记文件在 <work_dir>/bug_validation/<bug_id>.result.json 处不存在，或 resume 为 False 时，会分派一个 bug 验证代理来评估 result_json_rel 中记录的规范与代码差异是否构成一个真实、可利用的 bug。只有当该差异被确认为可利用的 bug 时，才会在 <work_dir>/bug_validation/<bug_id>.md 处生成一份经过验证的 bug 报告。该 bug 报告包含：规范声称的、而代码违反了的行为断言，从代码中观察到的实际行为，附有行号引用的具体代码证据，触发该违规的条件，逐步重现指令，一个演示该违规的探测脚本，以及执行探测脚本的原始输出。当验证完成时，会在 <work_dir>/bug_validation/<bug_id>.result.json 处写入一个结果标记文件。当 resume 为 True 且该结果标记文件已包含有效、可解析的 JSON 内容时，不会重新验证，也不会产生任何副作用。bug_id 是通过去除标准的验证结果路径前缀并将目录分隔符规范化后，从 result_json_rel 唯一派生而得的。

### 实际行为

代码块之后，将出现以下三种情况之一：(1) 抛出了未处理的异常（例如，来自 os.makedirs、文件写入、os.replace 或 build_llm_cli_command）。此时程序可能已中止，仅产生部分副作用；在异常点之后，对变量不做进一步保证。(2) 没有异常发生，并且函数在第 73 行提前返回，因为 resume 为 truthy，result_path 存在，并且文件能被成功读取并解析为 JSON。那么以下成立：目录 os.path.join(work_dir, 'bug_validation') 存在；位于 prompt_path 的文件存在，且其全部内容等于 prompt_content；临时文件 tmp_path 不再存在；以下变量均按代码中给出的值定义：prompt_content = '# Bug Validator\n\n**Target result file:** `{result_json_rel}`\n**Bug ID:** `{bug_id}`\n\n---\n\n' + user_knowledge_section + base_content，prompt_filename = 'fm_agent/bug_validation/bug_validator_{bug_id}.md'，prompt_path = os.path.join(proj_dir, prompt_filename)，tmp_path = prompt_path + '.tmp'，prompt = 'Follow the instructions in the attached file'，command = build_llm_cli_command(OPENCODE_BUG_VALIDATION_MODEL, prompt, cwd=proj_dir, files=[prompt_path])，result_relpath = 'fm_agent/bug_validation/{bug_id}.result.json'，result_path = os.path.join(proj_dir, result_relpath)；函数正常返回。(3) 没有异常发生，也未提前返回（resume 为 falsy、result_path 不存在，或 JSON 解析抛出异常）。那么与场景 (2) 相同的目录和文件副作用成立，与场景 (2) 相同的变量赋值成立，并且此外：max_attempts = config.BUG_VALIDATION_MAX_RETRIES；for attempt in range(1, max_attempts + 1) 循环已进入，第一次迭代以 attempt = 1 且 run_failed = False 开始；第 80 行的 try 代码块已进入，但尚未执行任何内部语句。形式化表述为：(exception_raised_at_line(l)  l  {49,55,56,57,59,60,61,62,63,64,65,66,68,69,70,71})  (exception  early_return  prompt_path_exists  file_content(prompt_path) = prompt_content  (v  {prompt_content, prompt_filename, prompt_path, tmp_path, prompt, command, result_relpath, result_path} : assigned(v) = value_from_code)  return_executed)  (exception  early_return  same_effects_as_above  max_attempts = config.BUG_VALIDATION_MAX_RETRIES  attempt = 1  run_failed = False)。此处 early_return 定义为 resume  file_exists(result_path)  json_load_succeeded(result_path)。

### 为什么会认为是 Bug

规范要求在 resume 为 False 或结果标记文件不存在时，分派一个 bug 验证代理，从而生成 bug 报告和结果标记文件。条件 A 描述了以下后状态：要么发生异常（未分派），要么函数提前返回（跳过），要么进入了重试循环但未执行任何分派。在这些场景中，代码均未执行所要求的副作用。

### 如何违反规约

当 resume=False 且不存在结果标记文件时，函数通过 run_opencode_traced 正确地分派了一个 bug 验证代理——该验证为误报，原因是不完整的控制流分析停在了第 80 行。

### 判读建议

**优先复核，不建议立即修改实现。** Validator 未确认原始结论，应先修正或重跑 probe，并确认反例满足函数前置条件；只有差异可稳定复现且真实调用链可达时，才进入修复队列。

---

