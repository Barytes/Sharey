# Sharey：测试与验收研究

日期：2026-10-11。
状态：**研究建议，尚未实现、安装评测框架或执行实验。**
范围更新（2026-10-11）：用户决定先完成功能实现；真实科研任务与文件共享收益对照移到后续。当前只采用软件正确性与小型使用路径的验证设计，本文其余科研评测建议不是实现前置条件。当前工作安排见 [实施方案](../mvp-implementation-plan.md)。
依据：[产品定义](../product-definition.md)与[实施方案草案](../mvp-implementation-plan.md)；当前确认的产品边界优先。

## 建议

采用 **pytest + FastAPI TestClient + 真实 HTTP / Git + Docker Compose + 原生 Agent CLI** 完成首轮验收。
先证明软件契约正确，再证明两种厂商的 Agent 能通过 Sharey 接续同一个真实科研任务。
Inspect AI 是有价值的后续评测工具；它目前能运行真实 Codex CLI 和 Claude Code，但现成适配器会改变模型接入链路。
软件正确性先在本机检查。根据随后提出的 Recursive 场景，正式科研任务首选改为 [有预算的 autoresearch 训练研究](automated-ai-research-acceptance.md)，下文 UCI HAR 保留为低成本备选。
autoresearch 原版需要 NVIDIA GPU；没有可用硬件时，单卡云主机有明确用途。云端位置本身不提高验收严谨性。

这里“正规”的含义是：有明确任务、独立判定、固定环境、完整尝试记录和可重复运行的流程。
真实公开数据能提高任务代表性；数据大小、Agent 数量和服务器位置都不能代替这些条件。
以下“来源事实”来自官方资料，“Sharey 建议”是针对当前产品的设计判断。

## 一手资料给出的事实

**软件测试。** FastAPI 官方支持直接使用 pytest 和基于 HTTPX 的 TestClient；后者直接调用应用，不建立真实 HTTP/socket 连接。因此应用测试通过，还需要另测真实进程与网络路径。[FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)、[TestClient Reference](https://fastapi.tiangolo.com/reference/testclient/)

pytest 的 `tmp_path` 给每个测试函数独立临时目录，适合准备工作区和 Git 仓库。它是测试资源管理机制；单纯使用不同目录不会限制同一用户进程读取其他目录。[pytest temporary directories](https://docs.pytest.org/en/stable/how-to/tmp_path.html)

**Agent eval。** Anthropic 将任务、单次尝试、评分器、轨迹和最终环境状态分别定义；因输出存在随机性，需要多次尝试。官方建议优先确定性评分、每次使用干净环境，并检查轨迹，避免只凭 Agent 的完成声明判定成功。[Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

**隔离与网络。** Compose 可定义多个服务；同一网络上的容器能按服务名互访。bind mount 将指定宿主目录暴露给容器，可配置只读。因此隔离效果取决于实际挂载与网络配置。[Compose networking](https://docs.docker.com/compose/how-tos/networking/)、[Docker bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)

**评测框架。** Inspect 提供评分器、自定义评分、重复 epochs 和日志；其 Docker sandbox 支持多个命名环境。配置 sandbox 不会自动把所有评测 Python 代码搬入容器，只有通过 sandbox 接口请求的工作在其中执行。[Inspect scorers](https://inspect.aisi.org.uk/scorers.html)、[metrics](https://inspect.aisi.org.uk/metrics.html)、[sandboxing](https://inspect.aisi.org.uk/sandboxing.html)

## 三层验收及其结论范围

以下分层是 Sharey 建议，不是外部框架规定。

| 层次 | 回答的问题 | 工具与判定 | 首版要求 | 可以支持的结论 |
| --- | --- | --- | --- | --- |
| 1. 软件正确性 | 输入、存储、读取、失败恢复是否遵守产品契约？ | pytest；TestClient；真实 Git；真实服务进程与 CLI；确定性断言 | 必须全部通过 | 这些契约在已测输入和环境成立 |
| 2. 科研接续 | 另一厂商 Agent 能否找到依据、运行完整 Skill、继续并发布？ | 两个隔离成员环境；原生 CLI；独立结果检查与人工语义评分 | 必做小规模完整回合 | 已测厂商组合和科研任务的局部可用性 |
| 3. 收益对照 | Sharey 相对现有文件共享，是否减少接续成本或提高成功率？ | 配对任务、预先确定指标与对照条件、足够重复 | 后续做 | 在对照条件下的增益证据 |

第 1 层可以使用人工构造的小文件和 CSV：它们用于精确触发软件规则。
第 2 层采用真实科研数据和可复算任务；通过小文件测试不等于科研接续已成功。
第 3 层不能由一次演示得出；两种 Agent 接续成功也不自动证明效率提高。

## 第 1 层：软件契约矩阵

建议每个测试使用独立项目、真实 bare Git 和临时成员工作区；不以存储 mock 代替 Git 行为。
应用路由可先用 TestClient 快速检查，再用真实服务进程覆盖完整 CLI 路径。

| 契约 | 最小场景 | 独立断言 |
| --- | --- | --- |
| 不可变快照 | 发布后修改、删除原文件，再读旧节点 | 旧节点文件清单、字节哈希和 commit ID 不变；新内容只进入新节点 |
| 当前工作区发布 | 选择 tracked-dirty 文件和 untracked 文件 | 服务端读回选定的当前字节；不要求先提交源代码 |
| 原仓库不受影响 | 从已有 Git 工作仓库发布 | 发布前后工作文件字节、index、HEAD、配置及 remotes 相同；无新增源仓库 commit |
| 非 Git 工作区与客户端 | 从普通目录发布；客户端环境中无 Git | 能发布和取回；Git 只由服务端要求 |
| 完整 Skill | 指令引用 scripts、references、assets 的相对路径 | 全目录清单与字节一致；在新目录实际执行依赖资源的步骤 |
| 多父 DAG | 根节点、两个分支、一个双父节点 | Git commit parents 与声明派生一致；INDEX 和节点读取表达同一结构 |
| 坏引用 | 引用不存在、其他项目的父节点、非研究节点 commit 或缺失资产 | 发布失败；无可见半成品节点；既有节点和 INDEX 不变 |
| 明确选取与私人内容 | 工作区放未选 canary，选部分目录发布 | 未选文件和 canary 字节不在共享清单及可取回内容中；不把 gitignore 当授权边界 |
| 项目凭证 | 正确、缺失、错误及另一项目的凭证 | 正确凭证可读写；其他请求被拒绝；错误响应不返回项目内容 |
| 并发发布 | 两个客户端同时基于同一父节点发布 | 两个节点都存在且可读；父节点不变；INDEX 无丢失 |
| 重试幂等 | 同一发布键重复/并发重发；同键换内容 | 相同请求只形成一个可见发布；不同内容复用同键明确冲突 |
| 真实进程重启 | 发布后停止服务进程，用同一数据目录新起进程 | 所有节点、文件、Skill、派生关系和可重试状态仍按契约可用 |
| 发布中断 | 在内容写入和引用可见边界附近终止进程，再启动并重试 | 不出现可读取的半份节点；已有发布可读；重试不会产生重复可见发布 |
| 归档路径 | 归档含绝对路径、`..`、链接或重复冲突路径 | 上传/取回按既定规则拒绝；目标目录外无写入；原有文件不被覆盖 |
| CLI 真实 HTTP | 子进程 CLI 经 TCP 调用真实服务完成查询、获取、发布 | 退出码、结构化输出、错误处理与服务端最终状态一致 |

归档的允许类型、覆盖行为和大小上限必须先作为公开契约确定，再写断言。
发布中断测试需要可控的故障注入点；不能用一次正常返回替代中断恢复检查。
进程终止测试证明进程级恢复；机器断电或磁盘损坏属于另一种故障模型。
并发测试在没有 Agent 的情况下完成，避免把推理随机性混进存储正确性判断。

## 第 2 层的低成本备选：真实科研样例

优先 AI 研究场景、可复用代码、GPU 条件与具体训练预算见 [自动化 AI 研究验收调研](automated-ai-research-acceptance.md)。以下 HAR 方案适合没有 GPU 预算时的完整任务验证。

### 已核实的数据事实

UCI 数据集 240，Human Activity Recognition Using Smartphones，包含 **10,299 个窗口、30 位受试者、6 类活动**。
每个窗口有 **561 个预计算特征**；官方已按受试者划分训练/测试集，分别来自 70% / 30% 的志愿者。
官方列出的 ZIP 大小为 **58.2 MB**，许可证为 **CC BY 4.0**，复用时应保留数据来源与署名。
以上均见 [UCI HAR 官方页面](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones)。

### Sharey 建议的任务形态

建议研究问题为：**官方未见受试者测试集上，全部 561 特征与事先固定的仅加速度特征子集表现如何，差异集中在哪些活动与受试者？**
使用完整官方数据，在 CPU 环境准备固定、成本有限的 baseline；建议采用 `LinearSVC(dual=False)` 与小型、事先固定的 C 候选集合。
先独立跑出参考结果，确认任务与评分器能正常完成，再把任务交给 Agent。
这里尚未安装依赖或测量运行时间，因此“CPU 可跑”是选型目标，不能写成已验证的时长。

保留官方受试者划分，检查 train/test 受试者不交叉；预处理仅在训练集拟合。
两条分支使用相同的 GroupKFold 协议，在官方训练集的受试者之间选择参数；不拿官方测试集调参。
分组规则使用 [scikit-learn GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html)，固定线性分类器使用 [LinearSVC](https://scikit-learn.org/stable/modules/generated/sklearn.svm.LinearSVC.html)；这些是复用的分析工具，研究协议仍需本项目预先确定。
仅加速度特征按固定索引选取；索引、库版本、参数候选和误差容限在预跑校准后锁定，正式验收开始后不更改。
锁定数据下载来源、内容哈希、Python/库版本、随机种子、线程配置和必要的数值容差。
不追求 SOTA；本任务检验研究上下文与方法能否被另一位成员准确复用。
不能为让验收通过而预先把全部结论直接写进 B 的任务提示。

建议形成以下研究过程：

1. R 发布根节点：数据来源、许可、哈希、固定受试者协议、研究记忆，以及可执行的完整 Skill。
2. 两个成员的新会话仅拿到项目入口、访问凭证与 Sharey 使用方法，通过概览定位 R。
3. 接收 Agent 说明目标、已有结果、受试者约束和待验证结论，并给出可读取依据。
4. 两个成员获取完整 Skill，使用共同验证协议；A 分支研究全特征，B 分支研究固定加速度特征子集。
5. 两分支分别发布配置、样本对应的预测、指标和研究记忆，明确结果支持什么、仍不支持什么。
6. C 角色启动没有 R/A/B 会话历史的新会话，经 Sharey 读取两分支，复算 accuracy、macro-F1、混淆矩阵与受试者指标。
7. C 解释两种特征设置的差异与限制，发布以 A/B 为双父节点的汇合及下一步研究判断。

R、A、B、C 是任务阶段/会话角色，可以复用两个厂商的 CLI；不要求四种 Agent 或四台服务器。
上述分支是可复算的分析工作；没有改善同样是有效结论，不追原论文成绩，也不把分类分数高作为 Sharey 通过条件。
58.2 MB 原始 ZIP 可在成员环境按固定地址和哈希准备；Sharey 先发布说明、代码、配置、指标和小型产物。
这仍是在完整真实数据上执行；不要求把原始数据 ZIP 放进 Sharey Git，避免擅自扩大大文件范围。
HAR 是 CPU 备选，尚未成为已通过的样例；它与 autoresearch 共用前述产品契约与证据要求。

## 独立评分：检查真实产物

评分器放在外部 runner；成员容器不获得评分器源码、参考输出、其他成员私有工作区或原始聊天。
任务说明应公开所有成功条件；隐藏参考答案不等于使用任务中未声明的要求扣分。
Agent 的“已经完成”只作为轨迹中的一句话，最终判定读取服务端与文件系统状态。

| 维度 | 判定方式 | 回合通过要求 |
| --- | --- | --- |
| 上下文理解 | 按目标、既有结果、关键约束、待验证结论逐项人工核对 | 关键事实正确；没有把假设当已证实结论 |
| 来源定位 | 由 runner 解析引用并获取对应节点/文件，核对支持内容 | 关键判断有实际可读且支持该判断的依据 |
| Skill 可执行 | 在 B 环境真实执行；检查退出码、依赖文件和输出 | 相对资源完整；最小科研任务完成 |
| 科研结果 | 独立脚本读取官方标签与发布预测，复算指标并检查协议 | 样本覆盖、重复、标签、受试者边界正确；指标和解释有数值依据 |
| 分支与汇合 | 直接读取服务端 commit parents 和节点内容 | 两分支存在；双父引用正确；汇合说明使用两条证据 |
| 共享边界 | 检查发布文件清单、旧快照哈希与 canary | 没有私人内容进入共享；旧节点保持不变 |

语义判断先用短而明确的人工 rubric；可按每维 0/1/2 记录不满足、部分满足、满足。
关键错误和缺失证据单独记为失败，不用其他维度高分冲抵。
确定性检查能解决的部分不用 LLM judge；后来引入模型评分时，先与人工标注校准。
评分器不导入 Agent 编写的评分代码；预测格式、参考复算方法、允许配置和数值容差预先固定。
参考复算应验证 accuracy、macro-F1 与混淆矩阵；数学定义可以复用 [scikit-learn F1](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html) 和 [混淆矩阵](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html)，不采用 Agent 自报的指标作为真值。
校准评分器时，完整参考产物应通过；故意删掉预测行、改错指标、引用不存在节点或删掉 Skill 依赖资源，应被对应检查判为失败。语义检查接受意思一致的表述。
分项分数用于定位问题；完整回合是否通过另设明确布尔条件，避免只展示平均分。
这些评分方式是本项目建议；框架自带的通用问答评分器不会自动理解 Sharey 的研究契约。

## Docker、本机与云服务器

建议 Compose 至少包含 Sharey 服务、成员 A、成员 B 三个服务，外部 runner 负责调度和判定。
A/B 各有自己的工作目录、CLI 配置和新会话；不能互相挂载工作区或整个宿主 home。
B 只能通过 Sharey HTTP 得到 A 已发布的内容；共享服务数据卷只挂载到服务端。
成员环境获得所需数据与科研依赖，评分器和参考产物保留在 runner 一侧。
公开数据可共享一个只读缓存；需要重新执行 Agent 产出的程序时，使用另一个干净的复算容器。无需常驻第三位 Agent。
不向成员容器暴露 Docker socket；API 密钥和项目凭证不写入可共享节点或公开日志。

每个独立回合重建成员工作区与会话，并从固定初始项目状态开始。
同一回合内应保留 Sharey 状态，让根节点、分支、汇合成为连续研究过程。
软件持久性测试故意保留数据卷重启服务；Agent 重复实验则使用新的回合状态。
仅换目录且共用原聊天/缓存，会削弱“没有 A 原始历史”的验收证据。

如果选 CPU 样例，云服务器可后续补做远程访问、TLS/反向代理配置、持久目录、进程重启和外部客户端 smoke test。
本机容器已经可以验证成员隔离、HTTP 交互与接续流程；云端部署应单独记录为部署证据。
如果选原版 autoresearch，GPU 是实际计算前提；可以将同一套成员隔离与服务环境放到一台单卡 GPU 主机上，不要求多机分布式部署。

## Inspect AI 的准确适用边界

**来源事实：可以直接运行现成 CLI。** Inspect 官方教程给出 `inspect_swe.claude_code()` 和 `codex_cli()`；真实 Agent 在 sandbox 中执行，无需把 Agent loop 重写成自定义 solver。[Inspect tutorial](https://inspect.aisi.org.uk/tutorial.html#coding-agents)、[Inspect SWE](https://meridianlabs-ai.github.io/inspect_swe/index.html)

**来源事实：模型调用被代理。** Sandbox Agent Bridge 将 CLI 的模型 API 请求送到容器内代理，再交由 Inspect 的模型 provider 处理。它默认不转发 CLI 的 temperature、max_tokens、reasoning 等生成参数；`forward_generation_config=True` 才以客户端参数为准。辅助模型名也需正确映射。[Inspect Agent Bridge](https://inspect.aisi.org.uk/agent-bridge.html)

Inspect 官方 OpenAI 与 Anthropic provider 分别要求 API key；其他云 provider 有自己的认证方法。当前查阅资料没有证明现成适配器能直接沿用用户本机 ChatGPT/Claude 订阅登录。[Inspect model providers](https://inspect.aisi.org.uk/providers.html)

CLI 版本可以固定或使用 sandbox 内预装版本。Codex 适配器默认由外层容器提供隔离，关闭其内部审批与 sandbox；相关选项必须记录。[Claude Code adapter](https://meridianlabs-ai.github.io/inspect_swe/claude_code.html)、[Codex CLI adapter](https://meridianlabs-ai.github.io/inspect_swe/codex_cli.html)

**Sharey 建议：首轮不让 bridge 成为必需依赖。** 先使用原生 CLI 接入路径验收，明确记录实际认证方式和模型配置；现有本机 CLI 可执行不等于容器认证已经可用。
如果采用 API key 受控模型矩阵，Inspect 可以复用隔离、日志、限额、重复运行和评分基础设施。
采用 bridge 时仍需自建 Sharey 场景与独立产物检查；同时固定代理配置、生成参数、辅助模型、重试次数和 CLI 版本。
若要声明生产配置兼容，另保留一次按用户实际 CLI 接入方式运行的验收，不能由桥接结果代替。
Inspect 并非“不支持真实 CLI”；本次后置它的理由是首轮需要先验证当前实际产品使用链路。

## 首轮运行规模与证据包

对于 HAR 或轻量接续回归，建议 Codex → Claude Code 和 Claude Code → Codex **各 3 个干净完整回合**，共 6 回合。
这是本地 MVP 的小规模建议，不是行业标准，也不足以估计广泛人群的可靠性。
每回合包括发布、无历史接续、完整 Skill 执行、分支与新会话汇合。
方向表示主要发布者与接收者的厂商互换；两个分支仍使用两个成员环境，汇合必须另起无历史会话。
保留全部 attempts；不只挑成功录像，也不把失败后人工补提示的结果算为原尝试通过。
先做少量预跑校准，锁定任务、检查项和每回合时间/调用预算后再正式计分。每回合包含多个会话，六回合不等于六次模型调用；目前没有实测总耗时与费用。
GPU 研究场景按专门方案先执行一个有独立多种子复跑的完整回合，不自动套用六回合规模。冻结真实实验产物后的轻量接续回归与重新训练的完整验收分别记录。

每回合证据包记录任务版本、Sharey commit、数据哈希、镜像/依赖版本、Agent/模型版本与配置。
同时保存提示、CLI 轨迹、工具结果、服务端请求日志、节点与文件哈希、科研产物、分项判定及判定理由。
单独记录耗时、可获取的 token/费用、超时、限流、认证/网络/容器失败，避免把环境故障混称模型错误。
报告总尝试数、完成数、完整通过数及逐回合结果；基础设施失败保留在总记录并标明原因。
软件契约有失败先修复；科研接续失败则区分材料编译、导航、Skill 包装、Agent 行为和环境问题。
确定性软件测试适合每次代码变更运行；涉及 CLI/Skill 使用路径的变更补做固定接续回归。完整 GPU 研究回合按需要和预算运行，不要求每次小改动重新搜索训练方案。

## 后续收益对照

产品可用后，再比较“同样公开材料的普通文件共享”与“Sharey 节点、研究记忆和 Skill 导航”。
两组保持任务、可见科研材料、Agent/模型、时间预算与评分器一致；明确普通共享组到底能看到哪些笔记。
普通共享组也获得相同的获准研究记忆、代码、完整 Skill 和表达父关系的文件清单；不能用“有上下文”对比“完全没有上下文”。
优先比较正确接续率、关键约束遗漏、达到合格产物所需时间与人工补充次数，再考虑 token 和费用。
使用新的干净会话与任务变体控制记忆泄漏；预先确定主要指标和排除/重跑规则。
对照规模根据预实验变异与希望识别的差异决定；本次 6 回合不能直接支持“Sharey 显著更好”。

## 可复用的外部科研任务

[ScienceAgentBench 官方仓库](https://github.com/OSU-NLP-Group/ScienceAgentBench)提供从 44 篇论文提取的 102 个科研编程任务，以及容器化评分流程；其目标输出是独立 Python 程序。当前仓库要求使用 verified split 和相应数据包，并有单任务运行入口。
对 Sharey 的建议是后续选择其中一个输出可确定性复核的任务，复用任务材料与评分逻辑，再增加跨成员接续步骤；首轮不引入整个 benchmark。科研编程评分通过与 Sharey 的节点、授权选取、跨 Agent 接续通过，分别记录。

本文仅完成官方资料核查与验收建议；未运行 pytest、Docker、Agent、科研 baseline 或云部署。
