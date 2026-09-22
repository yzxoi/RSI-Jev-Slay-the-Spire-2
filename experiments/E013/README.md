# E013 — Real full-run MCP campaign

Issue #19. User authorized continued gameplay through all rewards, selections and rooms until a genuine complete victory. Start from existing Ironclad A0 run `9JKXVG5BK1D8`, floor 3, 74 HP. This continuation is not an A10 validation run and its opening was played before this experiment.

Iteration 1 adds an all-scene native adapter and a budgeted single-writer complete-run controller. Jev chooses combat and macro actions, using E011 macro guidance; forced scene progression does not call the model. It records each response/state and stops on death, victory, expert-needed lethal end turn, unclear delivery, unsupported scenes, or budget. No resets, HP edits, rewards injection or debug victory flags. First segment cap 150 actions / 3,600 seconds / $3; inspect trace before further segments. Subsequent strategy versions are recorded per segment, never advertised as one fixed-policy benchmark.

PR is stacked on E011 for the shared macro instruction. Promotion requires a real complete victory plus trace/native-state corroboration and scene adapter checks; failures remain part of the report. Different strategies or character restarts must be reported explicitly.
