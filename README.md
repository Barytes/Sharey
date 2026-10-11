# Sharey

供研究组自行部署、以成员自己的 AI Agent 为入口的项目协作平台。成员的 Agent 将明确选定的文件和研究记忆发布为只读节点；队友通过概览找到依据、获取完整 Skill 并继续研究。节点直接对应 Git commit，支持分支和多父节点汇合。

服务端、CLI、Sharey Skill 和固定样例已实现。实际执行结果及产品验收状态见 [验收报告](docs/acceptance-report.md)。固定样例检验软件功能；真实科研实验与相对普通文件共享的收益对照留到后续。

## 安装与启动

需要 uv、Python 3.12 和服务端 Git。客户端使用同一个 Python 包，通过 HTTP 操作，无需 Git。当前运行入口适用于 macOS/Linux，服务使用一个 Uvicorn 进程和一个显式持久目录。

```sh
cd /Users/beiyanliu/Desktop/sharey
export UV_CACHE_DIR=/private/tmp/sharey-uv-cache
uv sync --frozen --no-editable --reinstall-package sharey --python 3.12
uv run --frozen --no-editable sharey serve \
  --config examples/server.json --data-dir .sharey-data --port 8765
```

默认监听 `127.0.0.1`。本地示例配置的项目为 `pilot`，凭证为 `local-demo-token`；部署给团队时复制配置、设置项目目标和团队凭证，并用 `--host` 指定监听地址。项目配置和凭证保存在服务端配置文件，研究内容保存在持久目录中的独立 bare Git 仓库。一个数据目录由一个服务独占；重启时使用相同配置和数据目录。

`--no-editable` 使用实际安装包，也避免当前 macOS 环境中隐藏 `.pth` 文件导致 editable 导入失败。修改代码后执行 `uv sync --frozen --no-editable --reinstall-package sharey` 重建安装包再运行。

## 使用

在另一个终端运行。激活环境后即可使用 `sharey`；其他机器安装本包后设置同样的连接变量。

```sh
cd /Users/beiyanliu/Desktop/sharey
source .venv/bin/activate
export SHAREY_URL=http://127.0.0.1:8765
export SHAREY_PROJECT=pilot
export SHAREY_TOKEN=local-demo-token
sharey overview
sharey list nodes
sharey list sources
sharey list skills
sharey publish source --file examples/pilot-latency/protocol.md \
  --title 'Pilot protocol' --contributor Alice --key example-protocol
sharey publish skill --dir examples/pilot-latency/skill \
  --title 'Pilot summarizer' --contributor Alice --key example-skill
sharey publish node --manifest examples/pilot-latency/node-manifest.json --key example-root
```

样例清单已经明确选择文件，默认没有父节点或资产引用。要关联刚发布的来源和 Skill，将返回的 ID 填入清单的 `sources` 和 `skills`，并使用新的请求键再次发布。下列命令中的 `NODE_ID`、`SOURCE_ID` 和 `SKILL_ID` 替换为实际发布结果。

```sh
sharey show node NODE_ID
sharey get file NODE_ID pilot.csv --out /private/tmp/sharey-pilot.csv
sharey get node NODE_ID --out /private/tmp/sharey-node
sharey show source SOURCE_ID
sharey get source SOURCE_ID --out /private/tmp/sharey-protocol.md
sharey show skill SKILL_ID
sharey get skill SKILL_ID --out /private/tmp/sharey-pilot-skill
python3 /private/tmp/sharey-pilot-skill/scripts/summarize.py \
  --input /private/tmp/sharey-node/files/pilot.csv --out /private/tmp/sharey-results
```

每个下载目标必须尚不存在。脚本产生 `results.json` 和 `report.md`，预期均值为 12 ms 和 9 ms，差值为 -3 ms，结论为 `pilot_only`。完整的自动演示包含资产引用、两个成员工作区、两个分支和双父汇合，见下方命令。

发布节点时，`memory` 和文件 `source` 相对清单目录解析；`path` 是节点内 `files/` 下的相对位置。文件按当前磁盘内容捕获，可以尚未提交或尚未跟踪。Sharey 不修改原工作仓库，不保存客户端 clone；来源信息记录基线和实际内容摘要，不自动公开 remote 地址。私人文件只有被明确选入清单，才进入节点。完整 Skill 发布选择整个目录，应包含全部配套资源。

请求键使用 1–128 个 ASCII 字母、数字、点、下划线或连字符。同一对象类型内，用同一键和相同内容重试会返回同一发布；同键换内容返回 409。保留原始清单和选定内容供不确定响应后重试；改动内容使用新键。成功输出 JSON；失败写 stderr 并返回非零退出码。

## 给 Agent 的 Skill

[skills/sharey/SKILL.md](skills/sharey/SKILL.md) 是完整的 Sharey Skill 目录入口，包含命令参考、清单说明和模板。将整个目录提供给能够执行本地命令的 Agent，或按所用 Agent 的本地 Skill 发现方式放入对应目录。CLI 不自动安装到全局目录。

Skill 指导 Agent 明确共享范围、编译可接续记忆、查询和引用节点、获取并实际运行配套资源，以及发布分支和汇合。成员的 Agent 完成研究内容编译与合并；服务端负责验证、快照、派生关系和持久读取。

## 测试与复现

```sh
cd /Users/beiyanliu/Desktop/sharey
export UV_CACHE_DIR=/private/tmp/sharey-uv-cache
uv sync --frozen --no-editable --reinstall-package sharey --python 3.12
uv run --frozen --no-editable pytest -q
uv run --frozen --no-editable ruff check src tests scripts examples/pilot-latency/skill/scripts
uv run --frozen --no-editable ruff format --check src tests scripts examples/pilot-latency/skill/scripts
uv run --frozen --no-editable mypy src/sharey
uv run --frozen --no-editable python scripts/run_acceptance.py \
  --out /private/tmp/sharey-acceptance-new-run
```

最后一个命令要求新的输出目录，自行启动并重启真实服务、建立 A/B 工作区、经 CLI 子进程执行完整路径、运行下载后的 Skill、检查真实 Git parents，然后停止服务。输出目录保留 `evidence.json`、`cli.jsonl`、`skill-execution.json`、服务器日志、数据仓库及工作区。其服务配置含本次随机项目凭证，复制证据时仅分享需要的结果文件。

测试覆盖公开 HTTP/CLI、真实 Git、不可变快照、完整 Skill 相对资源、多父节点、跨项目/错误类型引用、原仓库独立、无 Git 客户端、凭证、私人文件、归档校验、限额、并发、幂等、真实进程重启和三阶段发布中断。测试故障点使用显式 `SHAREY_TEST_FAULT_DIR`、`SHAREY_TEST_PAUSE_STAGE` 与 `SHAREY_TEST_PAUSE_KEY`；正常运行无需设置。中断证据验证进程故障恢复，不包含断电或磁盘损坏实验。

## HTTP 接口和数据契约

所有项目端点要求 `Authorization: Bearer <token>`。`GET /health` 只返回服务健康状态；`/docs` 和 `/openapi.json` 描述路由。发布传输格式、清单字段和错误行为见 [HTTP 与归档契约](docs/api.md)。

- [产品定义](docs/product-definition.md)
- [实现方案](docs/mvp-implementation-plan.md)
- [可执行规格](docs/mvp-spec.md)
- [本地 tracker](docs/agents/issue-tracker.md)
- [领域词汇](CONTEXT.md)
- [验收报告](docs/acceptance-report.md)
