# Sharey 上下文共享结构：mini research

调研日期：2026-10-11。状态：**设计提案，待用户决定**。范围限于 1 小时 MVP 的信息结构；核查 5 个一手页面，不评估完整记忆引擎。本文所述机制来自已打开的官方文档；Sharey 的目录、字段和取舍是设计推断，尚无运行结果支持。

> 讨论更新：本文最初建议把实验工作产物放入 sources、把研究叙述放入 records。用户随后提出，这会把同一研究过程拆成两套需要对应的演进结构，并选择 sources 保持为只读参考、records 共同承载演进的工作材料与记忆。本文保留原调研事实与提案用于追溯；当前内容模型以 [产品定义](../product-definition.md) 为准。

## 结论

**建议按“这条信息用来做什么”组织共享内容：项目入口、来源材料、研究记录、完整 Skill；时间和有效状态作为属性，读取时逐步展开。**

短中长期可以帮助管理单个 Agent 的工作记忆，但不足以成为研究组共享知识的主目录。队友首先需要知道：项目在做什么、已有哪项发现、依据在哪里、用什么方法继续做。一个月前发现的数据泄漏仍然必须遵守；今天刚提出的解释也未必成立。记录年龄既不代表重要性，也不代表可信度。

用户已经确定：成员自己的 Agent 编译；私人内容留在本地，明确分享的内容才进入项目；项目成员均可读。以下结构遵循这些决定，但结构本身尚未被接受。

## 一手来源支持的机制

### 1. OpenViking 的三层首先是读取粒度，而非短中长期

OpenViking 将 context 区分为 **resources、memories、skills**：外部参考资料、从交互与执行中保留的信息、可复用任务说明。当前内置 memory 类型包括 profile、preferences、entities、events、identity、soul、cases、trajectories、experiences；它没有将短中长期列为这里的顶层类型。[OpenViking Context Types](https://github.com/volcengine/OpenViking/blob/main/docs/en/concepts/02-context-types.md)

L0 是目录摘要，L1 是目录概览，L2 是原文或解析后的内容。L0/L1 是目录级辅助文件，不是每个文件必有的三份副本。这解决的是先定位、后深入的读取问题。[OpenViking Context Layers](https://github.com/volcengine/OpenViking/blob/main/docs/en/concepts/03-context-layers.md)

**对 Sharey 的推断：**借用“内容职责分开、按需展开”即可；没有必要在本次 MVP 引入 OpenViking 的整个数据库和抽取流程。时间跨度与摘要粒度是两个维度，不能混为同一层级。

### 2. Agent 更需要能导航的入口，而非一份越来越长的总结

Anthropic 的 context engineering 实践建议用路径、链接等轻量标识，在运行时按需读取；命名、目录和时间戳提供导航信号。其 structured note-taking 用外部笔记保存进展与依赖，之后再调入上下文。[Anthropic：Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

**对 Sharey 的推断：**默认返回一个小的项目入口，包含当前状态和相关记录、材料、Skill 的索引；细节单独读取。MVP 可用 Markdown 和普通目录表达，不需要先有向量数据库。

### 3. Skill 的共享单元是完整目录

Agent Skills 规范要求目录内至少有 `SKILL.md`，可包含 `scripts/`、`references/`、`assets/`。规范采用 metadata → instructions → resources 的逐步加载；`compatibility` 可表达产品、系统包及网络等环境要求。[Agent Skills Specification](https://agentskills.io/specification)

**对 Sharey 的推断：**Skill 应保持原目录及相对引用，项目索引只展示名称、用途与位置。把它压成一段“方法摘要”会丢掉执行所需脚本、模板和约束。标准格式能支持可移植的包装，但不能证明两个厂商的 Agent 已成功运行同一 Skill。

### 4. 科研共享要保留对象与依据的关系

RO-Crate 通过元数据描述文件、目录、Web 资源及其相关人员、组织等对象，用标识交叉引用；它还允许描述对象的制作历史与软件执行。其重点包括资料的发现、复用及产生背景。[RO-Crate 1.2 Introduction](https://www.researchobject.org/ro-crate/specification/1.2/introduction.html)

**对 Sharey 的推断：**本次只借用“可定位材料 + 记录到材料的链接”，不实现 JSON-LD、本体或 RO-Crate 合规。研究笔记中的发现要能回到结果文件、配置或论文原文；摘要不能成为唯一证据。

## 三种候选结构

以下比较是面向 Sharey 的设计判断，并非来源给出的产品优劣评测。

| 候选 | 典型结构 | 最有用的地方 | 本场景的问题 | 1 小时 MVP 判断 |
| --- | --- | --- | --- | --- |
| A. 时间分层 | 短期 / 中期 / 长期 | 管理工作中的活跃程度与保留周期 | 无法直接区分证据、假设、决策、方法；需要决定何时迁移或过期 | 不作主结构；先只记录更新时间 |
| B. OpenViking 式内容类型 | resources / memories / skills，各有摘要与详情 | 保留材料与经验的区别，按需读取 | “memory”仍以 Agent 为中心；研究者真正关心的是具体发现、决定及依据 | 可借机制，但不照搬全部引擎与分类 |
| C. 按研究协作用途 | 项目入口 / 来源材料 / 研究记录 / Skills | 回答项目做什么、已有何发现、依据何在、怎样继续做 | 需要约束记录质量，不能把个人猜测自动合并为共识 | **推荐；用 Markdown + 文件夹即可** |

## 推荐的最小编译产物

一个成员的 Agent 把选定内容整理成可发布的文件集合；Sharey 存储并提供项目范围内的列出与读取。下面表达逻辑结构，尚未决定 API、上传协议或数据库实现。

```text
project/
├── INDEX.md                   # 项目目标、目前进展、按用途组织的链接
├── sources/                   # 明确分享的原始材料，或可访问的固定版本引用
├── records/                   # 从材料/记忆提炼的研究记录
│   └── exp-017.md
└── skills/
    └── reproduce-baseline/
        ├── SKILL.md
        ├── scripts/
        └── references/
```

这里 `records/` 承接 Agent 记忆中对团队有用的部分。例如：发现、失败尝试、项目决定、当前假设与尚未解决的问题。私人偏好、聊天寒暄和与项目无关的历史不进入这一集合。MVP 先用一种 Markdown 记录，把这些类别写为正文小节或标签即可。

每份记录建议只要求：**标题、贡献者、记录时间、正文、来源链接**。正文明确写清“观察到了什么”“目前如何解释”“接下来做什么”；需要更正时指出替代哪条记录。时间表示何时形成这个判断，不触发自动升为长期记忆，也不自动让旧结果失效。

`INDEX.md` 默认先读，用短段落与列表回答：研究目标是什么、目前在做什么、哪些记录与任务相关、去哪里取证据和 Skill。它是导航与状态摘要；来源文件和记录仍然可单独读取。最新贡献先成为带作者的记录，是否进入项目共同采用的结论需要明确决定，MVP 不做自动共识合并。

来源必须是接收者能够读取的项目内路径或外部固定版本引用。发布者本机的绝对路径可以说明出处，但不能替代实际共享。对于大数据，MVP 可以先分享数据说明与已有可访问地址；这不代表平台已经共享了数据本体。

## 具体例子：队友继续一个实验

以下是虚构的设计例子，用于检验结构。

甲的本地 Agent 有论文 PDF、实验日志、聊天记忆和一个 `reproduce-baseline` Skill。记忆里提到：“上个月发现以帧随机划分会让同一个受试者进入 train/test；今天新试的归一化似乎提升了结果。”

编译后：

- `INDEX.md`：项目研究目标；当前需要在受试者划分下复现实验；链接到相关记录和 Skill。
- `records/split-leakage.md`：记录已经观察到的泄漏，链接检查输出及当时配置。它虽然较旧，仍然约束现在的实验。
- `records/normalization-try.md`：分别写初次运行的观察和“归一化可能有效”的假设；注明尚需多 seed 验证。它虽然最新，也不自动成为团队已接受的结论。
- `sources/`：已分享的配置、结果表、数据说明或固定版本链接。
- `skills/reproduce-baseline/`：完整保留步骤、脚本和运行环境说明。

乙的另一种 Agent 先读入口，再读泄漏记录与必要证据，最后获取 Skill；它应该能说明本次该用哪种划分、哪个结果仍待验证、如何运行。**这才是本 MVP 应检验的复用行为。**

## 如何在 1 小时内检验建议

只准备一个项目、一组明确分享的材料、一份从 Agent 记忆提炼的记录、一个已存在的 Skill。发布后让接收 Agent 在没有原聊天历史的条件下完成两项任务：

1. 回答项目目标、当前进展和一个必须遵守的实验约束，并指出来源。
2. 找到并获取完整 Skill；在既有环境支持的情况下，用它跑一个最小样例。

能返回上述正确内容且引用可读、Skill 依赖文件完整，才支持“可以复用”的局部结论。运行了一个 Agent 不能算跨厂商运行验证；只成功下载也不能算执行成功。

## 尚未解决，但不应扩成本次记忆系统工程

本轮没有实验比较三种结构的读取量或任务成功率，因此“用途优先”是有来源机制支撑的产品判断。需要用用户选定的真实材料验证；首个例子若暴露定位困难，再加索引字段或结构。

对于 1 小时 MVP，最重要的后续选择是：**首个共享样例具体是什么，以及由谁维护项目入口。** 多成员同时更新、自动失效、重复消除、访问控制细分和统一所有厂商的记忆提取流程，不是本轮结构建议成立的前提。

## 查阅范围

共 5 个主要一手页面：OpenViking Context Types、Context Layers；Anthropic Context Engineering；Agent Skills Specification；RO-Crate 1.2 Introduction。OpenViking 页面为访问时的 `main` 文档，未来可能变化；本文没有检查它的所有实现代码，也没有部署上述系统。未使用二手文章作为结论依据。
