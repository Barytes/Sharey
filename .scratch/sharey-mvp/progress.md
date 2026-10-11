# Sharey MVP 工作记录

2026-10-11 开始。事实来源已读取。采用 to-spec、to-tickets、implement、tdd、code-review；用户授权替代工作流中的逐项确认及外部 tracker。审查基线 d60f5359545c3c9ffe62fc587ffc952b276158c0。

工程决定见规格。七张票按完整使用路径安排，后续票只依赖真正必需的前序能力。TDD 日志保存每轮失败与通过结果；测试期望由固定契约决定。功能验收完成后另行尝试真实跨厂商 Agent。

环境：系统 uv 缓存不可写，改用任务专用 `/private/tmp/sharey-uv-cache`；使用已安装的 Python 3.12.12。没有修改用户级缓存或 Python 配置。

启动环境修复：macOS 当前运行环境把 .venv 内的 .pth 标为 hidden；Python 3.12 明确跳过 hidden .pth，editable 包因此不可导入。开发测试使用绝对 PYTHONPATH=src；交付安装和最终验收使用 uv sync --no-editable 的实际安装包。之前 exit=2/4 是环境错误，不记作有效行为 red 或 green。

2026-10-12 审查修复：新增“已接受的快照可下载”回归。500 个隐含目录文件首先按预期因 CLI 条目限制失败。大文件分支的首轮夹具只提高展开上限，却用未压缩 ZIP 超过上传上限，413 是正确行为；改为同时配置上传/展开 32 MiB 后重新观察下载行为的 RED。未删除或降低任何产品断言。

独立审查：Standards 0 项；Spec 2 项 P2（合法归档下载上限、损坏压缩流错误转换），均经 RED/GREEN 和独立公开 HTTP 复核关闭。最终实际安装包完整测试 52 passed、0 failed、0 skipped、1 个 Starlette/HTTPX 弃用提示；Ruff lint/format、Mypy、Sharey Skill 校验均通过。七票全部 done 后又运行一次完整真实 HTTP/CLI 使用路径，退出 0，固定结果、双父 Git、快照、隐私与重启全部通过。报告与证据在 docs/acceptance-report.md 和 docs/evidence/2026-10-12/。

实际跨厂商尝试：Codex/Claude 均报告已登录。Codex 原生任务在 restricted sandbox 中因自身状态数据库只读及 IPC 初始化 Operation not permitted 退出 1；扩大权限后的调用被自动批准审查拒绝，要求明确允许向外部模型提供本地合成样例及临时项目凭证。已请求限定范围许可，尚未绕过拒绝调用。实际跨厂商验收单独标为待验，不以两个 CLI 工作区替代。
