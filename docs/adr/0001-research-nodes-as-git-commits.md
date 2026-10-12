# 研究节点直接采用 Git commit 与父关系

Sharey 的研究节点是发布后只读的材料与研究记忆快照，允许基于多个已有节点形成新进展。首版将每个研究节点保存为一个 Git commit，commit tree 保存该节点的内容，commit parents 精确指向其研究父节点，并由 Sharey 为节点维护独立、不可变的 ref。这样直接复用 Git 的快照与 DAG；项目概览从节点集合生成，发布时的汇合内容由发布者的 Agent 整理。原代码仓库的提交历史不自动成为研究派生关系；工作仓库与发布快照的边界见 [ADR-0002](0002-independent-working-repositories-and-publication-snapshots.md)。
