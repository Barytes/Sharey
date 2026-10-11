# 07: 交付 Sharey Skill、固定样例和可复现完整使用路径

**What to build:** 交付 Sharey Skill、固定样例和可复现完整使用路径，从成员的命令入口到可读取且可验证的最终状态。

**Blocked by:** 04: 研究 DAG；05: 共享边界；06: 持久发布

**Status:** done

- [x] Sharey Skill 指导明确选取、编译记忆、发布、引用、获取与运行完整 Skill 和接续。
- [x] 固定样例及真实 HTTP/两个 CLI 工作区完整路径可重复运行并独立检查预期。
- [x] 安装、启动、使用、完整测试命令可执行；逐项验收报告及实际跨厂商尝试记录保存。

验证：完整实际安装包测试 52 passed；Sharey Skill 结构校验通过。固定 runner 经真实 HTTP/CLI 子进程发布、获取并执行完整 Skill，检查固定结果与真实 Git parents。详见 docs/acceptance-report.md 与 docs/code-review.md。原生 Agent 尝试记录已保存：Codex 初始化受 sandbox 限制，扩大权限被自动批准审查拒绝，等待限定外部模型材料范围的许可。功能完成与实际跨厂商产品验收待验分开报告。票据完成后仍须单独再执行完整 runner。
