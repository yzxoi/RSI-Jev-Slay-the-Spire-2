# 实验记录与复现索引

## 约定

每个实验先 issue 固定假设/样本/预算/门槛，然后 implementation commit，后 evaluation，后结果 commit/PR comment，最后合并或关闭。失败尝试不 amend，测试 seed 不替换，cap 是未完成而非死亡。原始 trace 与权重不提交，公开结果保留哈希。重复 learner 共享同批 test seed，不增大独立 seed 数。

## 当前轮次

- [E147](../../../experiments/E147/README.md)：已完成只读trace与AlphaZero训练目标诊断；全量1,152训练轨迹、180 DEV，审计1,350bundle/51checkpoint。任务进度输入缺失、末端领奖目标与后续价值脱节；记录具体动作序列避免错误归因。无新训练或游戏动作。[E147 详细诊断与 AlphaZero 对照](2026-10-03-credit-and-search.md)。E148/#279、E149/#280、E150/#281仅登记提案。

- [E146](../../../experiments/E146/README.md)：已完成；两份模型1,152条六战on-policy轨迹、103,127次新决策。30新seed六战成功7→7/4，完整幕均0；18独立重放、1,350份审计通过。扩训门槛失败。[曲线与结论](2026-10-03-onpolicy-pilot.md)。

- [E138](../../../experiments/E138/README.md)：已完成M3 Max CPU/MPS实测；CPU默认保留。
- [E139](../../../experiments/E139/README.md)：已完成126次五英雄/三控制臂完整自然尝试与15整局重放；全部战败，第三幕覆盖为零。
- [E140](../../../experiments/E140/README.md)：已完成BC/AWR/PPO比较，1024新增训练战斗、176新seed整局与288次级验证；未通过继续扩张门槛，原错误/权重/曲线/trace保留。
- [E141](../../../experiments/E141/README.md)：已完成；45次全程重放、7386旧状态一致，4894新观测稳定；可选接口与编码器合入。
- [E142](../../../experiments/E142/README.md)：已完成；30训练根局面胜场6→11，8个有意义改善均重放一致，452条路径审计；局部教师门槛通过。
- [E143](../../../experiments/E143/README.md)：已完成；匹配教师蒸馏不及自模仿（已见入口7/30对8/30），110新seed整局全败，停止此配方扩训。
- [E144](../../../experiments/E144/README.md)：已完成；60个自然对照全败，取消精英优先后第二幕1→2/30；门槛失败。
- [E145 #273](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/273)：已完成；120条自然路径全败、零Boss遭遇，门槛失败；派生六战前缀15/120成功，支持单独检验较短课程。

- [E133 #250](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/250) / [PR #251](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/251)：已完成。575个训练入口含151精英，两个S各6144场；恢复训练SHA `ee3f06f`，权重选择提交 `efa2ed5`，测试SHA `1dfa565`。48个未见seed困难入口：旧S18/18，新短训20/23，新长训24/25，规划器25；A10仍2/16、3/16。768场对照与384次新模型重放全部成功，两个强度门槛失败。包括原中断尝试的17466份bundle汇总审计通过。[结果、完整失败历史和图表](../../../experiments/E133/README.md)。
- E134 [PR #254](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/254)：训练/验证固定612原生+11完整重放，测试94+2；保留原生偏差。E135 [PR #255](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/255)：原版Rolling Boulder机制通过，264准备历史完全一致。
- E136 [PR #258](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/258)：完整191项合法菜单、原模型/随机种子/18步前缀一致、三次终局重放。E137 [PR #259](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/259)：模型/Adam/shuffle RNG精确恢复，仅训练出牌前加载超时允许一次留痕重试；29项相关测试通过，v2实际未触发重试。

- [E132 #248](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/248) / [PR #249](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/249)：多难度精英入口存档。准备 SHA `63c45db`，冻结路径 SHA `001d7db`，验证 SHA `b1b6601`；5/6 精英可用，40/40 续演一致，111 份 trace 审计通过。恢复中位数 4.507→1.172 秒；精确性/速度通过，入口完整性失败。共 218.956 秒，无模型 API；[全部结果与复用示例](../../../experiments/E132/README.md)。

- [E127 预注册](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/241)，[PR #242](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/242)，[完整记录](../../../experiments/E127/README.md)。
- 实现 b928d4d；104 个 seed 全部准备成功，312 入口，无替换。冻结 a958d71。32 条 preflight/独立 replay 一致；规划器验证集 15胜/1负。
- 训练 SHA 803d841c83f37da955478a741b944b796b781a24；4 个模型各完成 1,536 场，共 100,932 个动作。测试 SHA c076f4bcb5f75eecff6f7fe1b8a6ea874bbd9bba。S各23/24，L各22/24，规划器23/24，两个门槛失败；96条模型方案独立重放一致，6,888份trace bundle审计通过。实际优化器28.99秒，训练含验证1,942.51秒。
- [E128 预注册](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/243)：在 E127 test 结果前登记。所选权重已冻结；两种搜索在两个固定验证入口上全部成功并精确重放，207份trace审计通过。24-seed正式对照已完成，测试SHA be4b791a4f066379ecf74996543c6bfa71b2f92c：96场，86胜/4负/6超时，90条终局方案独立重放一致，5,880份trace审计通过；两项推广门槛失败。预算传递修复后，在干净SHA 0bd335eb52202fd9b251bb1767e41e8c375f39d7复测原固定验证入口：4场全胜、4条方案与原v1全部转移/探测哈希一致，207份trace通过；不替换test结果。[结果与图表](../../../experiments/E128/README.md)。

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
