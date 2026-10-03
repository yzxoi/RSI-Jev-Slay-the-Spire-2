# STS2 学习与搜索研究

目标是高胜率、可泛化的整局决策，逐步降低强模型参与成本。Jev、规则、搜索和神经网络都是可替换手段。当前可训练环境仍是历史 v0.111.0 的官方游戏逻辑加 headless 适配层；研究与当前 Steam 实战的兼容性分别验证。

最新：[E151物品覆盖审计](2026-10-03-item-novelty.md)：DEV药水全部已见，约94.5%的critic误差来自已知物品状态；陌生物品不足以解释泛化差距。无新训练。

此前：[E148固定策略下的任务状态实验](2026-10-03-task-value-pilot.md)已完成：输入小幅改善，但critic泛化失败，停止同配方扩量；E149/E150未执行。

此前：[E147 详细诊断与 AlphaZero 对照](2026-10-03-credit-and-search.md)，区分真实终局回报、搜索目标与动作因果归因；三项后续提案尚未执行。

文档按用户 Notion 中 reasoning research 的组织方式分成三层：

- [进展与决策](decisions.md)：最新在前，记录问题、证据、替代方案、选择与改变决定的条件。
- [实验记录](experiments.md)：实验输入、代码版本、预算、指标、失败与复现入口。
- [学习＋搜索方案](proposal.md)：算法、因果对照、适用边界和后续阶段。

GitHub 的实验 README、提交和 PR 是不可回写的证据来源；这里和 Notion 是面向阅读的索引。旧结论被修订时说明原因，不用新结果覆盖旧失败。原始决策与 wire trace、模型权重存于本机 `artifacts/runs/`，公开报告给出哈希。

Notion：按用户指定发布在私人区域。工作记录库只有读权限，未改动该库。

- [研究主页](https://app.notion.com/p/3edd59e86a7481109f71feb47a8286e4)
- [研究进展与决策](https://app.notion.com/p/3edd59e86a74817493b6c8af2a1f64ae)
- [实验记录](https://app.notion.com/p/3edd59e86a7481a0b815ea69ab35bdaa)
- [方案](https://app.notion.com/p/3edd59e86a74812384ffd952d87412da)
