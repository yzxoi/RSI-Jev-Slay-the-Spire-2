# RSI Jev — Slay the Spire 2

这是一个公开的、以证据驱动的《杀戮尖塔 2》智能体实验仓库。目标是用确定性计算处理规则与风险，让廉价的 Jev 做大量选择，只在关键且不确定的局面调用 Astra，最终提高多角色、高进阶的整局胜率。

**截至 2026-09-26：系统能控制真实游戏并完成过一局 A0，但还不是稳定通关的低 Astra 成本策略。** 请按下面的证据边界理解结果。

| 验证范围 | 已观察到的结果 | 不能据此声称 |
| --- | --- | --- |
| [E013 原生铁甲战士 A0](experiments/E013/README.md) | 从开局到第 48 层正常胜利；奖励、选牌、商店、事件和三个 Boss 均经过真实游戏流程。[终局证据](experiments/E013/attempt5/terminal-save.json)已验证。 | 该局有 213 条显式 Astra 决策，不能代表 Jev 独立或低成本稳定通关。 |
| [E092 原生铁甲战士 A1](experiments/E092/README.md) | 从第 11 层旧存档继续，至第 33 层第二幕 Boss 正常战败；433 个已接受动作、83 次 Jev 请求、71 段 trace 哈希核对通过。[汇总](experiments/E092/final-summary.json)。 | 这是单条**存档续局**，不是从第 1 层的新局，也不是胜率样本。 |
| [五角色 A10 CLI 评估](docs/milestone-02.md) | 已跑通多角色整局仿真与固定输入对照；已记录的评估尚无完整 A10 胜利。 | 局部战斗、执行兼容或离线排序改善不等于整局胜率提升。 |

系统目前分为三层：`rsi/` 中的计算与控制器负责合法动作、战斗预算和边界检查；Jev (`typesafe/jev-1.13`) 在候选间做结构化选择；Astra 可在低血量、商店等显式审核边界给出绑定新鲜状态哈希的单步决定。CLI 仿真与原生 MCP 实战分别评估，所有动作、模型输入输出和状态转移保留在 trace 中。设计动机见 [设计讨论](docs/design-discussion.md)，阶段结果见 [里程碑 1](docs/milestone-01.md)、[里程碑 2](docs/milestone-02.md)及[阶段 3 历史记录](docs/milestone-03.md)。

已经实现的能力包括：真实 MCP 的战斗与局外流程控制、五角色 headless 整局评估、固定状态重放与候选分支工具、药水/奖励/商店的审核边界，以及按代码 SHA 和原始 trace 哈希追溯每次实验。[E005](experiments/E005/README.md)验证了限定输入下的真实状态重放；[E085](experiments/E085/README.md)验证了奖励选择后的精确续局。它们是实验工具，尚未证明通用策略的胜率提升。

[E093](experiments/E093/README.md)提供可选的 `retaliate_resources` CLI 策略：战斗用药、商店买药、战后药水领取/跳过，以及满槽时丢弃腾位。药水选择复用原生控制器的每回合询问，仍需独立检验强度。接口、运行方式和覆盖边界见[CLI 资源决策](docs/cli-resources.md)。

[E096](experiments/E096/README.md)先验证老师再做成本压缩：六个固定 A10 Boss 失败入口中，原规划器 0 个可胜，提前用药基线 2 个，真实引擎搜索找到 4 个可胜；四份策略各重放三次，12/12 胜利且轨迹完全一致。两个 Silent 局面仍失败。这是旧版、已见局面的 Boss 实验，不是整局胜率或泛化证明。

## 运行与验证

需要本地合法安装的游戏，以及 `dependencies.json` 固定的 headless 依赖和 .NET SDK。原生实战另需已运行的 [STS2-Agent MCP](https://github.com/CharTyr/STS2-Agent)。脚本会从本地游戏安装读取专有文件；仓库不包含游戏二进制。Jev 调用使用环境变量 `OPENROUTER_RSI_JEV_KEY`，也可放在被 Git 忽略的 `.env` 中；不要提交或打印密钥。

当前 CLI 补丁针对历史 **v0.111.0**。本机 Steam DLL 已更新，直接自动读取新版会出现接口编译错误；当前版本适配由 [E094 / #182](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/182)跟踪。复现历史实验时先将 `STS2_GAME_DIR` 指向已核对哈希的旧版原始 DLL 本地目录，再运行构建；具体哈希见[版本说明](docs/cli-resources.md#版本限制)。

```bash
python3 scripts/setup_headless.py
python3 -m unittest discover -s tests -q
python3 -m rsi.full --characters Ironclad --seeds smoke_001 --ascension 10 \
  --policies first,greedy --output artifacts/runs/smoke.json
```

上面的 CLI 示例是两个简单基线，不调用 Jev。原生控制器默认只读；以下命令核对已存在的真实局面，不发送游戏动作。只有显式加 `--execute` 才会写入游戏，且必须使用当下实际的 run ID 和单一写入者。

```bash
python3 -m rsi.campaign --expected-run-id RUN_ID_FROM_MCP \
  --max-actions 1 --output artifacts/runs/native-inspect.json
```

## 仓库与证据

| 路径 | 用途 |
| --- | --- |
| `rsi/` | 控制器、Jev 接口、计算策略、MCP 适配与 trace。 |
| `tests/`、`scripts/` | 单元测试和可复现实验/依赖准备命令。 |
| `experiments/E###/` | 按 issue 与 PR 留下的预注册方案、代码 SHA、紧凑结果和失败记录。 |
| `docs/` | 设计、里程碑及[目录与本地 worktree 整理说明](docs/repository-layout.md)。 |
| `patches/`、`dependencies.json` | 固定的 headless 上游版本及本地补丁。 |
| `artifacts/`、`vendor/`、`.tools/` | 本地 trace、专有/第三方依赖与 SDK；已忽略，**不是待清除的源码杂物**。 |

每个策略实验先固定假设、基线与输入，再按 [实验流程](.agents/skills/sts2-experiment/SKILL.md)记录实现、测试、原始 trace 哈希、结果与合入/关闭理由。原始 trace 留在被忽略的 `artifacts/runs/`；公开仓库只提交可审查的紧凑证据。2026-09-25 已把 41 个散落在仓库旁的旧实验 worktree 归入一个本地目录，未删除其原始轨迹；见[整理记录](docs/repository-layout.md)。

半透明 overlay 的原型仍在 [E050 PR #94](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/pull/94)，**尚未合入 `main`**；E092 可见实战曾从该实验分支运行它，当前已关闭。下一步需要针对 Boss 朝向改变后的伤害重算、首幕资源与 Boss 准备做独立实验，并用新种子整局结果验证，而不是把一次局部改善写成通关能力。
