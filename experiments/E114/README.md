# E114 — sts2core source and trace compatibility audit

Issue: https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/218

Status: audit completed, 2026-09-29. No solver integrated or gameplay policy promoted. This is an offline audit, not a win-rate experiment.

## Question and fixed scope

Can sts2core supply a useful combat kernel for our recorded states? Distinguish potion mechanics, legal actions, local valuation, rollout policy and cross-room inventory. The practical baseline is our approximate planner plus preserved real-engine observations.

Upstream: `lain-wood/sts2core` at `3b2d969d025b9e64bc96b9a15928bd2a0d824bf2`, targeting game v0.107.1. Metadata: our `b7de162` commit. Inputs are all 30 E113 frozen combat entries (six seeds, five characters, A10, CLI v0.111.0), all 71 E092 native continuation segments, all four E102 historical Boss continuations, and E110 segment 1 for co-op scope. Missing/unsupported inputs remain reported. E102 repeats two entries and E092 is one continuation: these are not independent full-run samples.

Before evaluation, commit the audit code. Verify raw trace hashes, count identity coverage with the upstream's actual lookup functions, and inspect information lost at the state boundary. Identity coverage is only an upper bound on compatibility. No copied game binaries, live writes or paid model calls. Synthetic potion probes and upstream unit tests are separate from actual game evidence.

Decision rule: no automatic integration. Recommend a separate adapter experiment only for an explicitly supported subset; report game-version, character, state-import, mechanics and potion-policy limitations independently. A partial name match or a green unit test cannot establish full-state correctness or playing strength.

## Reproduction

Keep the pinned upstream checkout at ignored `vendor/sts2core-audit` and retain the historical raw trace directories. Review upstream Cargo.toml (no dependencies/build script), then:

```sh
cargo build --offline --release --lib --manifest-path vendor/sts2core-audit/Cargo.toml
rustc --edition=2021 -C panic=abort -C lto experiments/E114/probe.rs --extern sts2core=vendor/sts2core-audit/target/release/libsts2core.rlib -L dependency=vendor/sts2core-audit/target/release/deps -o artifacts/private/e114-probe
python3 scripts/audit_sts2core_e114.py
artifacts/private/e114-probe --synthetic
cargo test --offline --lib --manifest-path vendor/sts2core-audit/Cargo.toml
```

The Python audit reads historical committed manifests via `git show b7de162:...`; it does not require merging E113. Raw observations remain ignored. Results and source findings will be committed after execution.

## Iteration log

- `7509f1c`: upstream release library built offline in 5.70 seconds. The audit probe did not compile: upstream uses `panic=abort`, while standalone rustc defaults to unwind. The concurrent Python attempt stopped earlier on E110's wrapped result schema (`KeyError: run_id`), before invoking any probe. Neither attempt produced a capability result. No game or model execution occurred.
- `98c46dd`: matching panic strategy exposed an Apple linker/Rust LLVM bitcode mismatch (Rust LLVM 22, Apple LLVM 21). Add rustc `-C lto` so Rust performs LTO itself, and unwrap the E110 result before locating its trace. These are harness fixes, with the fixed cohort and upstream SHA unchanged.
- `4b46b9e`: lookup audit completed with all 106 trace hashes matching; 504 upstream library tests passed in 6.879 seconds including build. Four synthetic probes confirmed immediate block-potion valuation/consumption, dexterity rules with `CrossTurn` valuation, potion-free rollout policy and missing Blood Potion. Initial inspection found two audit normalization omissions: native potion actions use `option_index`, and upstream's stale discovery catalog omits the implemented Drum of Battle. Preserve the initial results, then correct these before final interpretation. No upstream source change is involved.
- `826580a`: final lookup/trace audit. All 106 trace files available and hashes match. Corrected native use-potion identities and mapped Drum of Battle through its exact Rust constant and compiled table. No hand-card alias guessing. The unchanged upstream unit/mechanic tests were not repeated; their code SHA remains `4b46b9e`. Results in `results.json`; build/test environment and synthetic checks in `checks.json`.

## 结论

**值得借鉴规则内核、搜索与校验方法；暂不适合直接替换我们的控制器，也不能当作五角色整局模拟器。** 本次没有对我们的轨迹做完整状态转移重放，没有测它的战斗胜率或与现有规划器的速度差异。下面的识别率只是名称/ID 对接检查。

“没有药水”需要纠正成五件不同的事：

| 层 | 固定 SHA 的实际实现 | 对我们的含义 |
| --- | --- | --- |
| 规则 L1 | `ops::POTIONS` 有 24 个表项，包含空槽，即 23 种药；`step(UsePotion)` 应用效果并清空槽位 | 并非完全没有药水；有些药是近似实现 |
| 单回合搜索 L2 | `legal_actions` 枚举可用药，`allowed_potions` 位掩码控制本次搜索能用哪几瓶 | 可以搜索喝药与出牌的先后顺序 |
| 单回合定价 | 不喝药搜一次，再逐瓶开放各搜一次；比较结算敌人回合后的自身 HP | 主要衡量本回合收益，不是整场或整局价值 |
| 顾问默认策略 | 默认保留阈值 10 HP；救命可越过阈值；持续增益通常报 `CrossTurn` | 力量、敏捷、再生、鱼油、铁心仍需外部策略；救命判定优先于 `CrossTurn` |
| 整场/整幕 rollout | `solver_play_turn_rec` 明确传 `allowed_potions=0`，Fast 策略也不喝 | “整幕推演不用药”属实；不是把规则表打开就解决了 |

### 为什么禁用药水

作者在 `solver.rs` 和 `rollout.rs` 中记录的动机是：药水不消耗能量，短视目标只要看到正收益就倾向于喝光；同时希望 Fast 与 Solver 在同一个不喝药条件下比较。机会成本因此放在搜索外面，当前由固定阈值提供，将来才计划由长期顾问提供。

代码还有一项决定性的架构约束：`synth/act.rs::one_chain` 每场用 `FightSpec { hp, max_hp, enemies, after_rest, boss_room, seed, ..*spec }` 重建状态。跨战斗传递 HP/最大 HP 等，但药水仍来自原始 `spec`；`rollout::Outcome` 不返回剩余药水库存。**只把 0 改成全槽位开放，会让每场重新获得原始药水。** 这是基于代码数据流的推论，没有改代码或把这种重复使用作为实验成绩。

“不用药”也不完全等于“药水没有效果”：瓶中精灵有自动触发规则，不依赖主动 `UsePotion`，仍可能影响 rollout。由于跨场库存未传递，自动药同样需要单独审计，而不能仅统计主动用药次数。

补全用药至少涉及：战斗内用药策略、跨战斗剩余库存、未来获取/满槽换药，以及持续增益的多回合收益。当前 L3 冻结牌组和大部分资源，用遭遇链比较构筑候选；它没有完整模拟选牌、商店和奖励流程。

### 它怎样求解

1. **L1 纯函数规则内核。** 紧凑、可复制的 `State` 保存玩家、敌人、卡牌分区、状态与 RNG；卡牌/药水的操作表、事件钩子和伤害管线驱动 `step(state, action)`。非法动作通常返回原状态。它是游戏规则的独立重实现，不是调用我们 CLI 的真实游戏引擎。
2. **L2 单回合搜索。** DFS 枚举合法出牌、目标、子选择和允许的药水；用状态指纹去重，比较每个合法停止点的评分。默认预算 200,000 节点，动作线最长 24。达到预算/长度上限时 `complete=false`。穷尽也只指该内核和目标函数下的搜索，不能证明真实游戏全局最优。`SURVIVE_FIRST` 明确使用人工权重：自身 HP 100、敌人 HP 30、胜利 100,000、死亡 -1,000,000，另有状态项。它仍有估值偏差。
3. **跨回合和 L3。** `plan.rs` 用候选剪枝、抽牌机会节点和叶子估值/rollout 扩展视野；并非无截断的整场穷举。L3 用相同随机样本比较原构筑与拿牌/删牌/升级/路线候选。共同随机数降低比较噪声，**不会自动消除模型偏差，也不能保证候选排序正确**。
4. **校验。** `verify` 从每帧真实观测同步状态，然后检查一步或一段动作后的 HP、格挡、状态、牌区等。观测注入的敌人伤害与自主预测敌人 AI 是分开的验收口径。未知/随机分支可能只比较张数、报软差异或跳过；504 个单元测试通过不代表全部游戏机制已经对拍。

### 我们的固定轨迹暴露了什么

| 证据 | 本次检查范围 | 具体缺口 |
| --- | --- | --- |
| E113 | 30 个冻结 A10 战斗入口，五角色×六 seed；30 个来源 trace 哈希通过 | 保守身份桥接识别 115 种牌中的 21 种；未知包含其他角色的打击/防御别名，不能全部解释成缺少规则。但 Neutralize、Zap/Dualcast、星星、奥斯提等核心机制确实不能由当前结构完整承载。6 个铁甲入口也都有未映射的 Ascender's Bane，第 6 个还有 Prep Time |
| E092 | 全部 71 段 v0.111.0 铁甲 A1 实战续局；439 个 `before` 观测，其中 330 个战斗观测 | 309/330 的当前手牌名字可全部映射，仍不代表状态完整。出现 Thinking Ahead、Exterminate、Mayhem，以及未建的 Pael's Legion 等遗物；223 个观测带佩尔士兵宠物。42 个观测处于选牌界面 |
| E102 | 全部四条 Boss 续局：铁甲/猎手×静态/动态；116 个 `before` 观测 | 共 8 次真实 CLI 用药：敏捷 4、血药 2、毒药 2。敏捷有规则但一般拒绝本回合定价；血药、毒药映射为 UNKNOWN。两条铁甲续局的血药都将 HP 从 56 提升到 72（最大 HP 80） |
| E110 | 首段 co-op 的全部 6 个 `before` 观测 | 四人共享路线/等待/玩家目标不在其单玩家状态结构中；该段没有 AI 战斗，不据此评价战斗强度 |

E092 的 8 次实际用药分别为火焰、无色、能量、再生、易伤、固化、甲虫汁、无色。**4/8 次是当前内核不支持的药**（两次无色、固化、甲虫汁），再生属于跨回合定价缺口。因此用这个内核评价我们已有成功/失败对局，可能把真正起作用的资源直接排除。

所选决策观测均未携带完整抽牌堆、弃牌堆、消耗堆内容。E092 的 MCP 记录只包含 `health_check`、`get_raw_game_state`、`act` 和 `wait_until_actionable`，没有额外牌堆查询。不能用永久 deck 减当前 hand 去伪造当前牌堆：消耗、生成、升级、洗牌与费用修改都可能改变它。上游依赖自己的 STS2MCP 补丁传递牌序/附魔，以及回合内历史恢复私有计数；与 CharTyr 的 JSONL/动作协议不兼容。

E092/E102/E113 都来自 v0.111.0；上游固定 v0.107.1。E110 虽版本相同，却是多人局且本段没有战斗。**这批数据没有一个可直接用于“同版本、完整状态、机制全覆盖”的胜率对照群组。** 缺失字段数量不等于规则错误数量；未映射 CLI 状态名还包含本地化占位符 `SETUP_STRIKE_POWER.title`，不能误判成上游没有对应能力。

### 仍需特别注意的实现边界

- 单回合 `--live` 会对部分未知手牌/遗物/状态打印警告后继续输出建议；它是有人阅读警告的顾问，不能直接当作自动执行器的安全门。应把缺口转换成结构化拒绝条件。
- `Pending` 并非完全不支持：有同回合历史、能重放进入子选择时可以处理；单帧导入不能恢复子选择则拒绝。生成三选一等类型仍有缺口。
- 攻击/技能/能力药水使用随机生成一张的保守近似，不能完整模拟真实“三选一”。血药在其发现目录中有 ID，但没有规则文本，且没有进入当前映射/操作表；没有证据表明这个机制原则上做不了。
- 固定阈值由 `PotionPolicy` 输入。库支持 `last_fight`，但 `bin/solve --live` 当前直接采用 `HOUSE_RULE`，并未自动接上全局药水规划。可以借鉴“计算边际收益、外部给机会成本”的接口，不能把已实现接口当作已完成路由。
- 开放药水的单回合 API 支持联合用药；顾问正常报告主要逐瓶比较，确认当前回合会死时才另搜全开放救命线。非致命场景的药水组合价值仍可能漏掉。
- 缺失遭遇被跳过，以及对引擎构筑/药水的非均匀低估，会改变候选排序。作者标注的 caveat 很有帮助，但下游仍需决定何时拒绝。

## Source anchors (pinned upstream)

- [Rules and potion limitations](https://github.com/lain-wood/sts2core/blob/3b2d969d025b9e64bc96b9a15928bd2a0d824bf2/src/ops.rs#L1420)
- [Legal actions](https://github.com/lain-wood/sts2core/blob/3b2d969d025b9e64bc96b9a15928bd2a0d824bf2/src/step.rs#L198)
- [DFS and budget](https://github.com/lain-wood/sts2core/blob/3b2d969d025b9e64bc96b9a15928bd2a0d824bf2/src/solver.rs#L1302)
- [Potion opportunity cost and advice](https://github.com/lain-wood/sts2core/blob/3b2d969d025b9e64bc96b9a15928bd2a0d824bf2/src/solver.rs#L1552)
- [Rollout potion policy](https://github.com/lain-wood/sts2core/blob/3b2d969d025b9e64bc96b9a15928bd2a0d824bf2/src/rollout.rs#L392)
- [Cross-room state propagation](https://github.com/lain-wood/sts2core/blob/3b2d969d025b9e64bc96b9a15928bd2a0d824bf2/src/synth/act.rs#L657)
- [Live warnings and policy](https://github.com/lain-wood/sts2core/blob/3b2d969d025b9e64bc96b9a15928bd2a0d824bf2/src/bin/solve.rs#L510)
- [Observation contract](https://github.com/lain-wood/sts2core/blob/3b2d969d025b9e64bc96b9a15928bd2a0d824bf2/src/replay.rs#L86)

## Decision and next useful work

Merge this **audit and reproducibility tooling only**; keep gameplay defaults unchanged. Borrow the pure-state/transition tests, explicit search budgets, refusal reporting and marginal potion valuation. Do not replace our real-engine CLI with this partial engine for formal five-character evaluation.

The shortest next experiment would be a shadow adapter for **same-version, single-player Ironclad deterministic states**, with full piles/counters exported and unsupported states rejected. Compare one-step transitions before searching turns. In parallel with that design, our existing real-engine branch tool can already evaluate a small number of potion/turn-plan alternatives at Boss entries; it avoids taking on another rules engine's missing mechanics. Any strength or latency comparison needs its own issue, fixed inputs and exit conditions.
