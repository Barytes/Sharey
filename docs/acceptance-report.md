# Sharey MVP 验收报告

执行日期：2026-10-12（Asia/Shanghai）。审查基线 `d60f5359545c3c9ffe62fc587ffc952b276158c0`；初始实现快照 `0301c6dd9e071c28c2c865c603e5cb25e42d6888`，随后修复独立审查发现的两项问题。

**功能开发已完成，软件契约验收通过。实际跨厂商 Agent 产品验收待完成。** 当前实现包含服务端、CLI、完整 Sharey Skill、自动化测试、固定样例、完整路径 runner 和启动说明。真实科研实验与相对普通文件共享的收益对照按最新范围留到后续。

## 实际执行结果

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| Python 实际安装包全套 pytest | **52 passed，0 failed，0 skipped**，71.26 秒，1 条依赖弃用警告 | [完整输出](evidence/2026-10-12/pytest.txt) |
| Ruff lint / format check | 通过；21 个文件格式一致 | [实际检查输出](evidence/2026-10-12/checks.txt) |
| Mypy | 通过；10 个源文件 | [实际检查输出](evidence/2026-10-12/checks.txt) |
| Sharey Skill 结构校验 | `Skill is valid!` | skill-creator 的 quick_validate.py；[Skill 入口](../skills/sharey/SKILL.md) |
| Standards 独立审查 | 0 项可操作发现 | [审查记录](code-review.md) |
| Spec 独立审查及复核 | 2 项 P2，修复后全部关闭 | [审查记录](code-review.md) |
| 完成全部 tickets 后再次执行完整 CLI 路径 | **passed**，真实 HTTP / CLI 子进程，A/B 独立工作区 | [最终状态](evidence/2026-10-12/evidence.json)、[全部 CLI 请求结果](evidence/2026-10-12/cli.jsonl)、[实际 Skill 执行](evidence/2026-10-12/skill-execution.json) |
| 原生 Codex / Claude 登录检查 | 两者均报告已登录；这不代表模型任务执行成功 | [原生尝试记录](evidence/2026-10-12/native-agent-attempt.json) |
| 实际跨厂商 Agent | **待验**：Codex 在受限环境中初始化失败，扩大权限后的调用被自动批准审查拒绝；未取得模型执行证据 | [错误输出](evidence/2026-10-12/codex-initialization-error.txt)、[准备给发布 Agent 的任务](evidence/2026-10-12/a-prompt.txt) |

执行环境：macOS arm64；Python 3.12.12；uv 0.10.6；Git 2.50.1；依赖版本由 `uv.lock` 固定。主要运行依赖为 FastAPI 0.143.0、Uvicorn 0.54.0、HTTPX 0.28.1；pytest 9.1.1。开发时因当前 macOS 隐藏 `.pth` 行为使用 `PYTHONPATH=src`，最终全套测试使用 noneditable 实际安装包，未设置 PYTHONPATH。

唯一测试警告来自 Starlette TestClient 对 HTTPX 的弃用提示；所有相关请求均实际执行并通过。测试未使用 skip、xfail 或 mock Git。

## 要求与证据对应

以下测试均在完整 pytest 命令中实际执行。标为 TCP/CLI 的测试启动真实 Uvicorn 子进程，通过本机 TCP HTTP 和独立 CLI 子进程操作。其他服务测试使用 FastAPI TestClient；所有发布和持久化路径都创建真实临时 bare Git 仓库。

| 要求 | 自动化验证 | 独立最终状态检查 |
| --- | --- | --- |
| 部署、项目目标、查询、概览与列表 | `test_project.py`；`test_cli_reads_real_http_project_and_lists_objects`（TCP/CLI） | 未登录请求无内容；JSON 项目入口；INDEX 与对象读取一致 |
| 发布、节点记忆、获取文件和节点 | `test_publish_current_bytes_and_read_immutable_node`；`test_cli_publishes_selected_disk_snapshot_and_downloads_after_local_deletion`（TCP/CLI） | 文本/二进制字节、相对路径、可执行标记；已有目标失败 |
| 来源材料发布、列出、读取和下载 | `test_source_can_be_published_read_and_downloaded_with_cli`（TCP/CLI） | 原始二进制字节保持，节点引用已发布 source |
| 完整 Skill 与 Sharey Skill | `test_complete_skill_preserves_relative_resources_empty_dirs_and_executes`；`test_workflow.py`（TCP/CLI） | 指令、脚本、参考、模板、配置与空目录保留；接收端真实运行相对资源并核对固定输出；Sharey Skill 本身也经服务发布/获取 |
| 不可变快照 | `test_cli_publishes_selected_disk_snapshot_and_downloads_after_local_deletion`；`test_workflow.py` | 本地修改或删除后，旧节点记忆、文件字节和 commit ID 不变 |
| 分支、双父节点与完整 DAG | `test_branches_and_merge_use_exact_git_parents_and_shared_navigation`；`test_workflow.py` | 独立 `git rev-list --parents` 核对根、两分支及汇合；overview/INDEX/节点读取一致 |
| 无效父/来源/Skill 引用 | `test_invalid_references_never_publish_or_change_existing_navigation` | 缺失、跨项目、错误类型、重复引用均失败，既有导航不变 |
| 凭证与项目边界 | `test_project_routes_reject_missing_wrong_and_other_project_credentials`；`test_every_object_read_and_publish_requires_matching_project_credential` | 所有项目端点缺失、错误、另一项目凭证返回 401，不含项目内容 |
| 私人文件与原工作仓库独立 | `test_dirty_and_untracked_publication_preserves_original_git_and_truthful_provenance`（TCP/CLI） | 逐字节比较原工作区和 `.git`；HEAD、index、配置、remote 不变；未选 canary 未公开；脏/未跟踪字节真实发布 |
| Git 出处与无 Git 客户端 | `test_provenance_tracks_nested_clean_files_against_correct_git_base`；`test_client_without_git_publishes_explicit_files_and_keeps_private_content_local`（TCP/CLI） | SHA-256 对应实际字节；基线/路径/状态正确；`PATH=/nonexistent` 客户端可发布下载 |
| 非法文件、归档与限制 | `test_boundaries.py`；`test_cli_downloads_every_accepted_snapshot` | 拒绝遍历、链接、特殊文件、重复冲突、大小写/Unicode 别名、超限；写盘前完整验证；合法 500 嵌套文件及 17 MiB 配置用例可下载；损坏 DEFLATE/BZIP2/LZMA 返回 422 JSON |
| 并发 | `test_simultaneous_retries_and_distinct_branches_survive_real_http`；`test_concurrent_different_content_on_same_key_has_one_winner`（TCP） | 8 个同键请求一个 ID；6 个并发分支全部可读；同键异内容 1 成功、4 冲突 |
| 幂等 | `test_retry_returns_original_publication_and_changed_content_conflicts`；重启和中断测试 | 同键同语义返回原 ID/时间/元数据，同键异内容 409；顺序和压缩时间不参与语义 |
| 重启与持久性 | `test_real_process_restart_keeps_assets_dag_bytes_and_retry_identity`（TCP、SIGKILL） | 来源、Skill、父关系、字节与重试身份保留 |
| 发布中断 | `test_process_interruption_never_exposes_half_publication_and_retry_recovers` 的 3 个阶段（TCP、SIGKILL） | 写对象中、公开前、公开后响应前；无可见半成品，重试恢复且不重复，旧节点可读 |
| 残留锁与目录独占 | `test_startup_recovers_stale_git_ref_locks_after_process_exit`；`test_second_service_cannot_take_live_data_directory`（TCP） | 重启恢复管理 ref 锁；第二服务无法占用活跃数据目录，第一服务继续可用 |
| 两独立客户端完整路径 | `test_fixed_two_workspace_workflow_runs_downloaded_skill_and_records_full_dag` | 公开 HTTP/CLI 驱动发布、接收、运行、分支、汇合、快照及重启；runner 独立核对固定结果与真实 Git |

固定预期来自 [expected-result.json](../examples/pilot-latency/expected-result.json) 与产品契约。六条人工数据的 baseline 平均值为 12 ms，candidate 为 9 ms，差值为 -3 ms，每组 3 条，结论必须为 `pilot_only`。这些数据与产物检验软件闭环，不构成真实科研结论或效果收益证据。

全部七张票据完成后，另行执行 runner 到 `/private/tmp/sharey-acceptance-final-20261012`，退出 0。最终根节点为 `59bffc6e35c083dee9ec54c1221d3db628ca4a61`，两个分支为 `e8a533b0ca78c93631cfd45d899be39f55673ced` 与 `ed8d8e17493d2ae6c95d704f0fe84bc856f991af`，汇合为 `efb971239d1734823d45856a717ce5bd953803af`，真实 Git 两父节点与上述分支完全一致。Skill 实际运行退出 0，产物与固定预期完全相符；旧快照不变、私人 canary 缺席、重启后保留均为 true。完整本地数据保留以便复查，提交的证据只复制不含凭证的结果文件。

## 工作流与测试完整性

已按 to-spec 保存 [规格](mvp-spec.md)，按 to-tickets 保存 [七张本地票据](../.scratch/sharey-mvp/issues/)，依赖顺序实现并记录 [RED/GREEN 日志](../.scratch/sharey-mvp/tdd.log)。独立 code-review 后修复再运行全套验收。

未通过删断言、跳过测试或改变固定预期取得通过。首次 editable 导入失败属于环境问题，未计作有效行为 RED；审查大文件回归的初版夹具超出上传上限，正确得到 413，随后同时放宽上传/展开配置并重新验证下载 RED。相关原因保存在 [工作记录](../.scratch/sharey-mvp/progress.md)。日志仅移除行末空白以通过 diff 检查。

## 实际 Agent 验收与待验项

检测到 Codex CLI 0.153.4 使用 ChatGPT 登录，Claude Code 2.1.97 使用已有第一方 OAuth。准备了独立的临时成员工作区；只有 A 拿到人工研究样例，其余工作区只拿到 Sharey Skill、项目入口和临时凭证。计划依次运行 Codex 发布、Claude 新会话读取与实际 Skill 执行、Codex 新会话独立算术分支、Claude 无历史会话汇合。接收者不提供 A 的聊天、原始工作区或固定答案。

实际启动 Codex 后退出 1：状态数据库为只读，原生 in-process app-server 初始化报 `Operation not permitted`。随后调用扩大权限被自动批准审查拒绝，要求明确许可把本地合成样例和临时凭证提供给外部已登录模型进程；已向用户提出限定范围的确认。此后未绕过拒绝继续外部调用。记录中已发布节点/来源/Skill 均为 0，模型执行尚未确认。因此当前不能声称单 Agent 或跨厂商 Agent 验收通过。

待验：收到许可后，以仅含必要系统变量与临时 localhost 项目凭证的环境完成上述真实会话，并由服务状态与实际文件输出核对目标/进展/下一步、引用、Skill 执行和双父汇合。两个 CLI 工作区通过只计为软件功能证据。真实科研实验、相对普通文件共享的收益对照留到后续；Windows 与外部网络部署本次未验。

## 可复现命令

安装、启动、人工使用及测试完整命令见 [README](../README.md)。最终验收命令如下，输出目录必须尚不存在：

```sh
cd /Users/beiyanliu/Desktop/sharey
export UV_CACHE_DIR=/private/tmp/sharey-uv-cache
uv sync --frozen --no-editable --reinstall-package sharey --python 3.12
uv run --frozen --no-editable pytest -q
uv run --frozen --no-editable ruff check src tests scripts examples/pilot-latency/skill/scripts
uv run --frozen --no-editable ruff format --check src tests scripts examples/pilot-latency/skill/scripts
uv run --frozen --no-editable mypy src
uv run --frozen --no-editable python scripts/run_acceptance.py \
  --out /private/tmp/sharey-acceptance-new-run
```

服务启动命令：

```sh
uv run --frozen --no-editable sharey serve \
  --config examples/server.json --data-dir .sharey-data --port 8765
```

数据目录与配置用于服务重启；验收 runner 保留完整临时数据用于复查并自行停止服务。归档证据不包含服务配置、访问凭证或用户级认证文件。
