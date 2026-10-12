# Sharey：自动 AI 研究任务验收

日期：2026-10-11。
状态：**研究建议，尚未实现验收 runner、准备数据或执行实验。**
范围更新（2026-10-11）：用户决定真实研究验收与收益对照后续再做。本文保留为后续研究设计，不作为当前 MVP 功能实现的前置条件。
依据：[产品定义](../product-definition.md)、[领域词汇](../../CONTEXT.md)与[通用测试研究](testing-and-acceptance.md)。
本报告聚焦真实 AI 研究场景，不替代软件契约测试，也不改变 Sharey 产品范围。

## 结论与适用范围

首选 **受限的 Karpathy autoresearch**，用原生 Codex CLI / Claude Code 完成有限实验、研究发布、无历史接续与分支汇合。
HAR 保留为低成本 CPU 备选；GPU 环境、可信模板或独立评分尚未准备好时，先用 HAR 验证接续。
先做一次真实完整 GPU episode，证明这一场景成立；改善 BPB 与平台通过分别报告。
这里的 episode 指从固定根状态开始，经过 R/A/B/C 研究阶段、发布与独立复跑的一次完整回合。
R/A/B/C 是阶段或会话角色，可复用两个厂商的 CLI，不要求四种 Agent 或四台机器。
本任务优化固定预算下的小模型训练方案，不据此宣称研究 Agent 自身递归增强或实现 superintelligence。

## 来源事实：Recursive 实际开放了什么

Recursive 文章描述了提出想法、实现、实验、验证和继续探索的系统，并明确开放其输出 artifacts。
作者承认基础模型可能知道已有公开技巧，结果不能直接视为独立重新发现；文章性能属于作者报告。[Recursive 原文](https://www.recursive.com/articles/first-steps-toward-automated-ai-research)

官方仓库提供发现的训练脚本、kernel 实现与结果；NanoChat 包还包含 tokenizer、dataloader、BPB 评测和时间预算的局部 harness。
公开仓库未提供文章描述的完整研究编排 Agent、多线程调度或上下文管理系统，不能直接部署为 Sharey eval runner。
SOL 只发布 235 个结果中的 10 个示例，其余保留私有。[成果仓库](https://github.com/recursive-org/first-steps-toward-automated-ai-research)、[NanoChat 包](https://github.com/recursive-org/first-steps-toward-automated-ai-research/tree/main/nanochat_autoresearch)

| 候选 | 任务与硬件事实 | 可复用部分 | 首版判断 |
| --- | --- | --- | --- |
| NanoChat / autoresearch | 固定训练预算，最小化 validation BPB；Recursive 成果在单 B200 上运行 5 分钟并报告 10 seeds | 训练脚本、局部 harness、逐 seed 结果；原版任务指令可供原生 CLI 使用 | 首选受限变体，先固定可信执行范围 |
| NanoGPT speedrun | 8×H100，尽快达到 FineWeb mean val loss ≤3.28 | 固定 token 流规则、同硬件对照、运行日志及统计验证 | 首轮设备与实验成本过高 |
| SOL-ExecBench | B200 上实现满足数值契约的快速 kernel；支持单题 | 独立 CLI、definition/workload/solution 接口、JSONL trace 与反作弊检查 | 后续 kernel 任务候选，无需首轮跑全套 |

NanoGPT 涉及 ML 改动的提交需足够运行日志支持均值达到阈值的 p<0.01；速度与基线在同硬件比较，纯系统优化有统计要求例外。[NanoGPT 官方规则](https://github.com/KellerJordan/modded-nanogpt#rules)
SOL 默认 seed=200、10 次 warmup、50 次计时迭代；官方 B200 锁定 1500MHz 后仍报告约 5% 时延波动，小 kernel 可达 10%。[SOL 官方接口与环境](https://github.com/NVIDIA/SOL-ExecBench#evaluating-a-solution)
这些是各 benchmark 的事实，不是 Sharey 必须达成的成绩或统一统计标准。

## 来源事实：原版 autoresearch 的可复用边界

基准固定为 Karpathy 仓库 commit **228791fb499afffb54b46200aca536f79142f117**，不从不断变化的 master 开始正式验收。
该版本要求单 NVIDIA GPU，在 H100 测试；官方未承诺最低 VRAM，能否在选定 GPU 上运行需预跑确认。
原版直接依赖 CUDA；改用 Mac CPU/MPS 移植版会改变基线与任务条件。[固定版本 README](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/README.md)

原协议只允许 Agent 改 train.py，禁止改 prepare.py、数据加载、分词器、评测及固定常量，也禁止新增依赖。
训练预算为 300 秒，排除启动、编译与评测；原协议另规定运行超过 10 分钟应终止。
原 program.md 要求 NEVER STOP 的无限实验循环，正式验收须替换为限额 Skill，并由外部 runner 强制执行总预算。[固定版本 program.md](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/program.md)

prepare.py 默认下载前 10 个训练 shard 与固定验证 shard_06542，不需要下载整套 400B 数据集；数据页声明 MIT。[数据页](https://huggingface.co/datasets/karpathy/climbmix-400b-shuffle)、[固定数据准备源码](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/prepare.py)
数据下载 URL 使用 resolve/main，attention kernel 动态加载未指定 revision；验收还需锁定文件哈希、tokenizer、依赖与 kernel 缓存。
原 train.py 固定 seed=42，没有多 seed 统计协议，也没有保存 checkpoint 供后续加载复评的默认路径。[固定训练源码](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/train.py)

## 工程建议：仅开放声明式数值参数

首轮采用范围收窄的任务变体：A 只研究 MATRIX_LR，B 只研究 WEIGHT_DECAY，其余模型和训练设置固定。
允许键、数值范围、最多候选数量及 seed 列表在预跑后锁定，正式计分时不再调整。
Agent 提交声明式参数文件与研究解释；执行入口只接受允许键下、范围内的有限数值。
外部 runner 从固定可信模板生成执行源码，冻结 forward、loss、数据、计时与 evaluation，并校验生成结果只包含允许 diff。
模板和评分器保存在 runner 一侧；Agent 工作区中的任意 Python 文件不作为正式训练入口。
这保留真实训练实验与接续判断，但不能称为复现 Recursive 全面架构搜索或其成绩。

冻结 prepare.py 本身不够：evaluate_bpb 调用可编辑模型的 model(x, y, reduction='none')，接受模型返回的 loss。
若候选能改 forward/loss，就可能返回假 loss 或引入标签泄漏；另起进程执行同一候选也不会自动消除它。[原版评测调用](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/prepare.py#L311)
首轮将整套模型与 loss 实现纳入可信模板，复用原版固定 BPB 评估路径；评分采用 runner 实际执行模板得到的结果，不采用 Agent 自报数值作为真值。
未来若开放模型 forward/loss 修改，再增加独立依据 logits 与真实标签计算分数的接口；首轮不为此重写完整评分系统。
数据与分词器哈希、训练/验证分离、因果前向、实际训练预算和全部评测输入在 runner 中核对。
公开验证集上的改进只支持该任务目标，不自动证明对其他数据或更大模型的泛化。

SOL 可复用的原则包括新输入多轮正确性检查、shape/dtype 检查、lazy tensor 拒绝、计时/评测函数完整性与后台线程检测。
其 driver 实际接入这些检查；Sharey 若后续采用 kernel 任务，应直接复用官方工具。[SOL eval driver](https://github.com/NVIDIA/SOL-ExecBench/blob/main/src/sol_execbench/driver/templates/eval_driver.py)

## 工程建议：一次完整 GPU episode 的限额

正式回合从固定基线、全新工作区与会话开始；A/B 仅通过 Sharey 获取其他成员明确发布的材料。
探索阶段可沿用 seed=42；最终独立复跑使用预先指定的同一组三个 seeds，不按结果挑 seed。

| 阶段 | 研究与发布 | 最多训练 attempts |
| --- | --- | ---: |
| R | 运行固定基线，发布来源、环境清单、基线配置、原始日志、研究记忆与完整 Skill | 1 |
| A | 从 R 接续，比较最多两个学习率候选，发布选择依据与失败记录，父节点为 R | 2 |
| B | 从 R 接续，比较最多两个 weight decay 候选，发布选择依据与失败记录，父节点为 R | 2 |
| C | 新会话读取 A/B，最多运行一次两参数组合，解释兼容性并发布双亲节点 | 1 |
| 独立复跑 | 冻结 R、A 所选、B 所选、C 组合四配置；每配置用相同三个 seeds 从头训练 | 12 |
| 合计 | 探索最多 6 次，加独立复跑最多 12 次 | **18** |

没有改善时 A/B 可以保留基线参数，C 也可以据证据否定组合；负结果是有效研究结论。
配置退回基线仍保留对应阶段记录，不因此增加搜索次数；没有有效候选时不得伪造成功分支。
失败、OOM、超时、基础设施失败及修复重试均占本轮槽位；不得把“重试”变成额外无限搜索。
缺少必要有效复跑时，报告未完成或失败，不把剩余有效结果包装成完整通过。
评分器保存尝试顺序、配置、seed、退出状态、原始输出及失败原因，区分研究失败与基础设施失败。

18 × 5 分钟 = **最多 90 分钟名义训练预算**；这不是整个回合的实际耗时或资源承诺。
另计数据/tokenizer 准备、编译、warmup、评测、Agent 推理、排队与失败处理，并分别记录实际 GPU 与墙钟时间。
实际每进程上限、总墙钟上限、模型调用/费用上限在预跑后锁定，由外部 runner 强制截止。
这份研究没有购买 GPU、启动云实例或承诺费用；所选 GPU 的显存与运行时长尚未实测。
四配置各三次是本地 MVP 的复核建议，不足以宣称可靠统计改善，也不等同 NanoGPT 的 p<0.01 规则。

## 隔离、评分与 Sharey 边界

公开数据、tokenizer 与依赖可使用固定只读缓存；成员的私人 workspace、聊天、CLI 配置与凭证分别隔离。
成员环境只获得自己的工作区和获准读取的缓存，不能挂载另一成员工作区、runner 评分器或服务端数据卷。
GPU 由外部 runner 排队独占；A/B 可以并行分析与写参数，不能同时争用一张 GPU 后比较 BPB 或速度。
多个 Docker 容器并不自动提供 GPU 性能隔离；基线和候选使用同硬件、同依赖和同计时规则。
Sharey 保存选定快照、完整 Skill、研究记忆与派生关系，提供 HTTP 查询、取回与发布。
实验调度、设备排队和预算属于外部验收 runner；不为此给 Sharey 增加调度领域模型。
PyTorch、CUDA 和科研数据属于独立实验环境，不成为 Sharey 服务端或客户端的安装依赖。

原版没有 checkpoint 复评入口；本方案在新进程中按冻结配置从头复跑训练，再由可信评分路径评测。
不能声称已经加载原实验权重独立复评；若以后增加 checkpoint 导出，需要另行定义格式和信任边界。
评分器读取真实服务端节点、commit parents、文件哈希、参数与日志；不以 Agent 的“完成”声明评分。
平台维度核对无历史接续、关键约束理解、依据可读、完整 Skill 实际执行、两个分支与双亲汇合。
同时核对不可变旧快照、私人 canary 未发布，以及已发布状态在真实服务重启后可读。
BPB 维度报告四配置逐 seed 结果、与基线差异及失败记录；平台通过不要求超过基线。
伪造分数、违反允许 diff 或缺失必要证据均不能以其他维度高分冲抵。

## 运行顺序与后续收益对照

先通过通用报告的软件正确性检查，再校准固定模板、依赖、GPU 基线和评分器，最后进行一次正式完整 GPU episode。
校准与正式回合分别留档；正式回合开始后不因结果不理想调整阈值、候选范围或评分方法。
通用报告“两个厂商方向各 3 episode”的 CPU 建议不自动套用本任务。
若直接照搬，将变成 6 × 18 = **108 attempts、9 小时名义训练**，还未计实际开销。
一次 GPU episode 只支持该任务和厂商组合的场景证据，不支持广泛可靠性或显著收益结论。
随后可冻结真实实验产物，做两个厂商方向的无历史取回、解释、Skill 调用和再发布轻量回归。
轻量回归与重新训练的完整 GPU 闭环分别计数；不能把复用旧结果写成新训练成功。

产品可用后再做收益对照：普通文件共享组也获得相同文件、获准研究记忆、完整 Skill 和表达父关系的清单。
两组固定模型、任务、GPU/时间预算、可见材料和独立评分；比较正确接续、约束遗漏、时间与人工补充次数。
Sharey 的价值应来自研究节点组织、导航、不可变发布与接续，而不是给它更多上下文或更高实验预算。
目前只完成来源核查与方案设计；未运行训练、Agent、Docker、评分器或任何正式验收。
