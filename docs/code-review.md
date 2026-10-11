# MVP 实现审查

日期：2026-10-12。固定基线 `d60f5359545c3c9ffe62fc587ffc952b276158c0`；初始实现审查快照 `0301c6dd9e071c28c2c865c603e5cb25e42d6888`。按 code-review Skill 由两个独立只读审查者分别执行 Standards 与 Spec 轴，随后复核修复。自动检查由主执行者运行，审查者不重复执行。

## Standards

可操作发现：**0**。仓库 AGENTS.md 为空，工程自动检查配置来自 pyproject.toml。本地 tracker 的票据、依赖、状态和行为验证字段满足已记载约定。核心 HTTP、CLI、归档和 Git 存储职责清晰；未发现对本次实现有实际影响的基线代码气味。

## Spec

初审发现 **2 项 P2**，均已关闭，无未解决发现。

1. 合法快照下载受默认上传限制再次拦截。500 个 `files/dN/f.txt` 的上传包只有 502 条目，服务返回 201；Git 隐含目录进入下载后变成 1003 条目，CLI 默认限制错误拒绝。服务允许放宽大小限制时，17 MiB 合法节点也被 CLI 拒绝。修复为服务声明实际下载 ZIP 的展开字节数与条目数，CLI 以声明值校验下载，保留结构、路径、类型及写盘检查。两个真实 HTTP/CLI 回归先失败后通过。
2. 损坏压缩数据未统一转为归档校验错误。原 DEFLATE 损坏触发 zlib.error 并返回 500；复核进一步发现 BZIP2 和 LZMA 的同类异常。修复在归档解压边界转换为 ValueError，由发布接口返回 422 JSON。三格式回归先观察失败，再实现通过。独立审查者通过公开 HTTP 重放损坏 BZIP2/LZMA，均得到 422 `application/json`、`{"detail":"Invalid publication archive"}`，节点列表仍为空。合法压缩格式继续接受。

## 修复后验证

- 下载修复的 500 嵌套文件、17 MiB 两项，以及原下载危险归档三项：**5 passed**。
- DEFLATE/BZIP2/LZMA 损坏归档：**3 passed**；独立公开 HTTP 复核通过。
- 实际安装包完整测试：**52 passed，0 failed，0 skipped，1 warning**，71.26 秒。
- Ruff lint、Ruff format check、Mypy 均通过。

完整测试输出见 [pytest.txt](evidence/2026-10-12/pytest.txt)，逐轮 RED/GREEN 见 [.scratch/sharey-mvp/tdd.log](../.scratch/sharey-mvp/tdd.log)。大文件回归首次只放宽展开上限却使用未压缩上传包，触发正确的上传 413；随后修正夹具同时放宽上传/展开限制，重新观察下载 RED。未删除、跳过或降低产品断言。
