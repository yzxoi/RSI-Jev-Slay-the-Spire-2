# 仓库目录与本地 worktree 整理（2026-09-25）

仓库顶层保留 `rsi/`、`tests/`、`scripts/`、`experiments/`、`docs/`、`patches/` 等用途明确的目录。`rsi` 是可直接用 `python3 -m rsi...` 调用的包；`scripts` 和 `patches` 已被运行命令引用。为减少目录数量而移动这些源码，会破坏现有实验命令和历史复现路径，因此本次不改动它们。

`artifacts/runs/` 保存不入 Git 的原始 trace；`artifacts/private/` 保存本地存档、控制锁和本次整理清单。`vendor/` 是固定上游 headless checkout 与本地游戏 DLL，`.tools/` 是本地 SDK。它们被 `.gitignore` 排除，但现有运行代码按仓库根目录定位，不能当缓存随意删除。可再生成的 `.DS_Store`、`__pycache__` 与上述证据/依赖应区别对待。

## 已完成的本地整理

把位于仓库旁的 41 个 `~/RSI-Jev-Slay-the-Spire-2-e###` Git worktree，用 `git worktree move` 迁移至 `~/RSI-Jev-Slay-the-Spire-2-worktrees/RSI-Jev-Slay-the-Spire-2-e###`。这是同一文件系统内的目录移动，不是删除或重建。迁移前约占 7.56 GiB；其中有 1,922 个位于各自本地 `artifacts/runs/` 的 `decisions.jsonl`，另一些 worktree 通过符号链接共用主仓库的 trace。21 个指向旧 `e067/vendor` 绝对路径的跨 worktree 链接已更新。

逐个核对了 41 个 worktree 的分支 HEAD、`git status --porcelain` 和本地 trace 数量均与迁移前一致；Git 注册路径已全部指向新位置，原来的 41 个同级目录不再存在。另在新位置重新计算 E092 的全部 71 个原始 trace SHA-256，均与[公开汇总](../experiments/E092/final-summary.json)一致。本地详细迁移前清单、逐目录结果和链接映射分别保存在被忽略的 `artifacts/private/worktree-cleanup-2026-09-25.json`、`worktree-cleanup-moves-2026-09-25.json`、`worktree-cleanup-symlinks-2026-09-25.json`。

主工作目录内另清理了 8 个可再生成的 Finder `.DS_Store` 文件和 3 个 Python `__pycache__` 目录；没有删除依赖、存档或 trace。

这次只整理了用户指定的同级 `e###` 目录。`/private/tmp/rsi-sts2-*` 和 Codex 管理的 `.codex/worktrees/` 未移动。旧 Codex 任务若保存了原来的绝对路径，重新打开时可能需要指向新的 worktree 位置；Git 分支与数据仍在。以后建立实验 worktree 时，直接放到统一的 `~/RSI-Jev-Slay-the-Spire-2-worktrees/` 下。
