# HTTP、清单与归档契约

前缀为 `/projects/{project}`。项目成员持有对应共享 token，使用 `Authorization: Bearer <token>`。来源、Skill 与节点使用同一项目访问范围。缺失、错误、其他项目或未知项目的凭证请求返回 401，响应不包含项目目标或内容。

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| GET | `/overview` | 项目标识、目标、节点摘要与父关系、来源与 Skill 索引 |
| GET | `/index` | 同一已发布信息生成的 Markdown 导航 |
| GET | `/nodes`、`/sources`、`/skills` | 已发布对象列表 |
| GET | `/nodes/{id}` | 元数据、真实 parents、研究记忆、文件清单 |
| GET | `/sources/{id}`、`/skills/{id}` | 元数据与完整文件清单 |
| GET | `/nodes/{id}/files/{path}` | 原始选定文件字节，path 相对 files 目录 |
| GET | `/nodes/{id}/archive` | metadata.json、memory.md、files 下的快照 ZIP |
| GET | `/sources/{id}/file` | 原始来源文件字节 |
| GET | `/skills/{id}/archive` | SKILL.md 和完整相对资源目录 ZIP |
| POST | `/nodes`、`/sources`、`/skills` | `application/zip` 发布包；必须提供 `Idempotency-Key` |

发布与重试成功均返回 201 和同样的对象 JSON，ID 是 40 位 Git SHA-1 commit OID。不存在的已发布对象/文件返回 404，坏输入/引用/归档返回 422，同键不同内容返回 409，超过配置限制返回 413，错误 Content-Type 返回 415。错误 JSON 为 `detail`；框架自身的请求字段错误也返回 422。没有修改或删除已发布对象的 API。

## 元数据与 ZIP

发布 ZIP 的 `metadata.json` 是 UTF-8 JSON。共同字段：`schema_version: 1`、`title`（1–240 字符）、`summary`（最多 2000 字符）、`contributor`（1–100 字符）。未知字段或错误类型拒绝。节点可带 `parents`、`sources`、`skills`（默认空数组）和逐文件 `provenance`。贡献者是发布者署名，不是经过认证的成员账号。

节点 ZIP 另含 UTF-8 `memory.md`，以及 `files/<relative-path>` 下的明确选定文件。节点的父/资产引用只接受同项目已发布的对应类型 ID；重复引用拒绝。快照不隐式继承父节点文件，合并内容由发布者提供。

来源材料元数据另含 `filename`，ZIP 中只有对应的 `files/<filename>` 文件。完整 Skill ZIP 另含 `skill/SKILL.md` 和 `skill/` 下的全部文件与目录；根指令为 UTF-8。Skill 下载去掉传输用的 `skill/` 前缀，保留原目录和相对引用。

文件路径为规范 POSIX 相对路径。绝对路径、空/点/父组件、反斜杠、冒号、控制字符、重复路径、文件/目录冲突、大小写或 Unicode 规范化后碰撞的路径拒绝。仅接受普通文件和目录，拒绝链接和特殊文件。ZIP 的 Unix mode 表示执行位；读回文件保持原字节，下载恢复 644/755 权限，空目录也保留。默认上传和展开各 16 MiB、1000 条目（含元数据/目录），可在服务配置的 `limits` 中修改。

CLI 节点清单通过 `memory` 和 `files: [{source, path}]` 指定本地文件。CLI 将清单编译为上述传输包，并产生与实际文件 SHA-256 一致的出处信息；服务端检查所提供出处摘要与快照一致。原工作仓库和 Sharey 仓库互相独立。

## 持久发布与恢复

每个项目独立 bare Git 仓库，节点 commit 的 parents 是真实研究父节点。对象类型分别使用 `refs/sharey/nodes/`、`refs/sharey/sources/` 和 `refs/sharey/skills/`；后缀是请求键的 SHA-256，ref 仅创建、不覆盖。单个 ref 同时保留完整 commit 和幂等身份。未公开对象不进入列表，也不接受按原始 Git OID 绕过已发布 ref 的读取。

同项目、同类型、同键的重试按规范化元数据、文件内容/执行位和目录结构判定，ZIP 顺序、时间戳或压缩方式不改变请求含义。相同语义返回原发布，不同语义冲突。项目概览从已发布 refs 生成，不维护另一份研究历史。

服务独占持久目录；另一个服务使用同一目录时启动失败。启动时在持有独占锁的前提下清理被终止进程留下的 Sharey ref 锁。对象先写入，最后原子创建一个 ref；进程在此前终止只留下不可见孤立对象，在此后终止仍保留完整可重试发布。服务不执行垃圾回收或后台删除已发布节点。

原始文件响应通过 `X-Sharey-Executable: true|false` 表示执行标记，CLI 据此恢复权限。项目标识使用 1–64 位 ASCII 字母、数字、下划线或连字符，首位为字母或数字；大小写不敏感后重名的项目配置拒绝。

归档下载通过 `X-Sharey-Archive-Unpacked-Bytes` 与 `X-Sharey-Archive-Entries` 声明所生成 ZIP 的精确展开字节数和条目数。CLI 用它们作为下载校验上限，同时验证所有路径、类型和冲突后才写盘。下载包含 Git 的隐含目录和扩展后的读取元数据，可能超过原上传条目数或字节数；下载上限不重复套用默认上传限制。HTTP 服务是凭证持有者选定的信任来源；缺少这些响应头时 CLI 使用默认 16 MiB / 1000 条目的兼容上限。
