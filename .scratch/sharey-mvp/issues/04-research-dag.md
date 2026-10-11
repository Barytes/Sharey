# 04: 基于引用形成研究分支与双父汇合

**What to build:** 基于引用形成研究分支与双父汇合，从成员的命令入口到可读取且可验证的最终状态。

**Blocked by:** 02: 节点快照；03: 来源与 Skill

**Status:** done

- [x] 根、两个分支和双父汇合的 Git parents、节点读取、overview 和 INDEX 表达一致。
- [x] 不存在、跨项目、错误对象类型、缺失资产及重复父引用失败，无可见半成品。

验证：见 tdd.log 对应项目入口、节点、来源/Skill 与 DAG 的 red/green 记录；公开路径测试使用真实 Git，CLI 测试使用真实 TCP 服务。最终完整验收仍需执行。
