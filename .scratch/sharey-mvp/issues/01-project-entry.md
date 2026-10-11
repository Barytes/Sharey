# 01: 部署并通过 CLI 查询受凭证保护的项目入口

**What to build:** 部署并通过 CLI 查询受凭证保护的项目入口，从成员的命令入口到可读取且可验证的最终状态。

**Blocked by:** None (can start immediately)

**Status:** done

- [x] 配置持久目录、项目目标和凭证启动真实 HTTP 服务，CLI overview/list 返回结构化项目入口。
- [x] 所有项目读取和发布路径拒绝缺失、错误及另一项目凭证，错误响应不泄露内容。

验证：见 tdd.log 对应项目入口、节点、来源/Skill 与 DAG 的 red/green 记录；公开路径测试使用真实 Git，CLI 测试使用真实 TCP 服务。最终完整验收仍需执行。
