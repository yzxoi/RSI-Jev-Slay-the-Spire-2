# CLI 资源决策接口

E093 新增可选策略 `retaliate_resources`。它在原有战斗规划器上，复用真实游戏控制器的药水询问：每回合最多一次，让 Jev 在当前规划动作与合法药水/目标之间选择；每个真实动作执行后重新读取状态。它不是 E088/E089 的威胁预算策略，也尚未证明更高胜率。

```sh
python3 -m rsi.full \
  --characters Ironclad,Silent,Defect,Regent,Necrobinder \
  --ascension 10 --seeds my_new_seed \
  --policies retaliate_resources --workers 4 \
  --max-calls 1000 --max-usd 0.50 \
  --output artifacts/runs/resources.json
```

须先提交代码，并建立符合 `dependencies.json` 的本地 SDK/引擎。原始 trace 位于忽略的 `artifacts/runs/`。结果中的 `policy` 明确标识是否开启资源模式；默认策略没有切换。

## 能力与边界

| 场景 | 资源模式 |
| --- | --- |
| 战斗 | 手动可用药水与具体目标；Automatic 药水不进入手动候选 |
| 商店 | 有空槽、金币足够且允许获得时可购买；满槽时可先丢弃，再从新状态购买 |
| 战后药水 | 显式 `potion_reward`：领取、跳过；满槽可丢弃腾位。空槽时控制器自动领取免费奖励 |
| 选牌型药水 | 正常转入 `card_select` / `card_reward`，完成选择后继续 |
| 战斗外 | 在地图、商店、营火与奖励场景提供当前合法的 AnyTime 药水 |
| 金币、遗物奖励 | 仍由 CLI 自动领取；没有声称与所有原生奖励交互完全一致 |

引擎模式由 `Headless(..., resource_decisions=True)` 显式设置。底层环境变量是 `RSI_RESOURCE_DECISIONS=1`，但 Python 运行器会显式覆盖它，避免外部环境意外污染旧实验。

`player` 增加 `potion_capacity`、`has_open_potion_slots`、`can_use_or_remove_potions`。持有药水增加 `id`、`slot_index`、`usage`、`can_use`、`can_discard`；商店药水增加 `id` 和 `can_buy`。动作使用的 `potion_index` 仍是当前 CLI 导出的压缩列表索引，**不是**物理 `slot_index`。任何使用、丢弃或领取后都必须重新读取索引。

购买调用真实商店采购逻辑并核对物品进入库存；异常明确返回。领取调用真实奖励逻辑；容量不足时不会偷偷丢弃库存。`legacy_projection()` 只剥离新观察字段，用于核对历史状态，绝不删除 HP、库存、卡牌或敌人差异。

完整局 trace 增加 `resource_check` 和 `resource_transition`。使用药水后可能先出现选牌边界，不能将该中间态直接解释成“药水未生效”。反事实实验应分别报告资源消耗、效果、战斗结果与整局结果。

## 版本限制

截至 2026-09-26，历史实验使用的原始游戏 DLL SHA-256 为 `9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4`（v0.111.0）。本机 Steam DLL 已变为 `e7ceb80669bfaf5c8fccabaa126ae2bb283aba514be5b5b55612579cfd285f18`，直接重建旧 CLI 出现接口编译错误。[E094 / #182](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/182) 独立跟踪当前版本适配。

E093 在保留的历史 DLL 上验证；不能据此宣称当前 Steam 游戏的机制或原生对局已经完全对应。复现时使用明确的 `STS2_GAME_DIR` 指向已核对哈希的原始 DLL 副本；不要让构建脚本默默采用更新后的 Steam 文件。测试证据与失败迭代见 [E093](../experiments/E093/README.md)。
