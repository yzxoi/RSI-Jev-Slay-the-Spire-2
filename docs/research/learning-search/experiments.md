# 实验记录与复现索引

## 约定

每个实验先 issue 固定假设/样本/预算/门槛，然后 implementation commit，后 evaluation，后结果 commit/PR comment，最后合并或关闭。失败尝试不 amend，测试 seed 不替换，cap 是未完成而非死亡。原始 trace 与权重不提交，公开结果保留哈希。重复 learner 共享同批 test seed，不增大独立 seed 数。

## 当前轮次

- [E127 预注册](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/241)，[PR #242](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/242)，[完整记录](../../../experiments/E127/README.md)。
- 实现 b928d4d；104 个 seed 全部准备成功，312 入口，无替换。冻结 a958d71。32 条 preflight/独立 replay 一致；规划器验证集 15胜/1负。
- 训练开始 SHA 803d841；4 个模型，各最多 1,536 场；结果待完成。其后图表与独立检查的提交不会改变已加载训练代码。
- [E128 预注册](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/243)：在 E127 test 结果前登记。待 E127 完成并冻结所选权重后做 value/rollout PUCT 对照。

## 已完成的重要证据

| 实验 | 范围与结果 | 决策 |
| --- | --- | --- |
| E120 | 10个 A0 精英入口；规划器8/10，MC/UCT9/10；恢复耗时大 | 搜索工具保留，默认不推广 |
| E121 | 真正地图边界恢复与继续流程精确；性能保守门槛两次失败 | 研究性 opt-in |
| E124 | 同24次约93→46秒；增加到64次上限仍9/10，收益中位数0 | 不自动增加搜索量 |
| E125 | 2×384训练；2×16未见首战全胜，均比规划器多损6HP | 保留 trainer，停止当时扩训 |
| E126 | 攻击优先与随机合法动作诊断 | 仅proposal；不能标记已执行 |

历史结果原文及版本： [E120](../../../experiments/E120/README.md)、[E121](../../../experiments/E121/README.md)、[E124](../../../experiments/E124/README.md)、[E125](../../../experiments/E125/README.md)。更多 LLM、药水、选牌、真实整局记录见仓库 [README](../../../README.md) 与 [milestone-03](../../milestone-03.md)。

## 当前环境

Apple M3 Max / CPU；Python 3.13.5，PyTorch 2.11.0，NumPy 2.3.2，.NET SDK 9.0.318；历史游戏 v0.111.0。每份报告记录实际 engine/DLL/依赖哈希。无需 Jev/OpenRouter/Astra API；Astra 编写研究代码与分析的会话成本未纳入游戏推理账单。
