# 实验记录与复现索引

## 2026-10-03 · D023 · 后续控制器是局部瓶颈，分开验证战斗与宏观

[E159](../../../experiments/E159/README.md)固定15TRAIN seed的30根状态，做首步×后续2×2，共120完整续局。相同原网络首步下，程序后续下一战2→17/30，15败转胜、零胜转败；11/15seed获益，效用增量1.03807，聚类95%区间[0.62261,1.45141]。全部诊断门槛通过。四组局部通过2/3/17/17，Act2到达0/0/0/1，最终全败。

固定战斗入口1→6/15；准备入口1→11/15，其中4条改打其他普通怪、另1条同名怪入场楼层/准备改变，不能把全部收益算作出牌能力。E149全败发现根中6个被救回，但不能据此证明原定精英都可打赢。97.816秒墙钟，60网络完整/首战路径等价、6程序重放、126bundle和120首战wire重建全部通过。

决定：合入可选诊断与证据，不推广权重/默认策略，不启动E150。新搜索教师需要强程序基线；优先现有[#298](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/298)新seed自然整局的战斗×局外控制器对照，尚未执行。最终330seed未用。[报告与图表](2026-10-03-continuation.md)。

## 2026-10-03 · D022 · 教师有局部收益，覆盖门槛失败；恢复修复可复用

[E149](../../../experiments/E149/README.md)完整评测15个TRAIN seed的30根状态/936续演：独立验证下一战25→31/180，贪心下一战2→3/30；两臂完整续局均0Act2/0胜。平均回报增量0.06824，seed聚类95%区间[0.000069,0.159086]，仅4/15seed正收益，未达>=5门槛。18/30根所有发现续演全败；收益主要来自A5，A10无增益。小样本探索，不是未见seed胜率或不可恢复证明。

E157发现加载地图会丢失未知房间累积概率，8/120续演分歧，拒绝原证书。E158修复适配器：60正常/120加载/120计时路径全部通过，配对恢复中位加速2.118倍。E149 v3在586.240秒完成，搜索p9547.330秒；936份trace及729条旧路径等价检查全通过。游戏DLL未变，证书仅覆盖当前30根/runtime；旧失败不覆盖。

决定：合入可选工具、修复和正负证据；不推广策略、不启动E150。下一步[E159/#306](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/306)固定首步×后续控制器诊断，已登记未执行。无梯度/模型API请求，最终330seed未用。[完整结果、图表与下一步](2026-10-03-root-teacher.md)。

## 2026-10-03 · D020 · 自然课程出现单学习器收益，保留完整局门槛

[E153](../../../experiments/E153/README.md)完成普通→精英→Boss和此前准备课程；两份115,778参数模型，共288新路径、5,430决策。每阶段同9seed完整局监测，最终冻结后33新seed覆盖A0～A10。2302精英6→9/12、Boss2→3/12、准备＋Boss1→4/12，完整局进入Act2由0→2/33（A2/A4）；2301无对应收益，三者整局均0胜。局部小样本只提供信号，不能判定稳定提升。

程序对照32败＋1引擎错误，不能把未完成算败。E154发现并修复Kaiser Crab被错误跳过；两个游戏DLL未改，88条历史完全一致，两条修正路径重放通过。Trial/Crystal Sphere仍有已登记兼容缺口。完整性和双学习器扩训门槛未通过，合入可选课程/证据/修复，不推广权重或扩大此配方。830份学习/评测trace审计通过，checkpoint失败与完全一致的重启保留；最终330seed未用。[结果、图与限制](2026-10-03-real-curriculum.md)。

## 约定

每个实验先 issue 固定假设/样本/预算/门槛，然后 implementation commit，后 evaluation，后结果 commit/PR comment，最后合并或关闭。失败尝试不 amend，测试 seed 不替换，cap 是未完成而非死亡。原始 trace 与权重不提交，公开结果保留哈希。重复 learner 共享同批 test seed，不增大独立 seed 数。

## 当前轮次

- [E152](../../../experiments/E152/README.md)：共享属性与旧哈希同参数/同训练预算对照；新72seed/144路径上MSE降12.49%/16.06%，仍输给ridge，A5与终点门槛失败。3重放、147bundle、237行预选特征重建一致；3项合成测试通过，116.49s。[结果与曲线](2026-10-03-shared-value.md)。

- [E151](../../../experiments/E151/README.md)：只读审计E148全部576路径；1,152原始文件与51,343行决策对齐。DEV未见卡/药/遗物21/0/2种，仅影响5.96%决策；约94.5%critic平方误差在已知物品状态，整条已知的130路径仍输给简单基线。[报告](2026-10-03-item-novelty.md)。

- [E148](../../../experiments/E148/README.md)：已完成。固定actor采集576路径/288seed；四个critic，补任务DEV误差仅降4.40%/3.51%，均输给简单进度ridge；门槛失败。6重放、582bundle、全部51,343张量行重建通过。原汇总路径异常保留，无换seed或重跑。[结果与图](2026-10-03-task-value-pilot.md)。

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
