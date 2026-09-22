# E026 delayed scaling

Issue47. Baseline E030 triggered current-hand planner, unchanged Jev macro. Existing planner incorrectly adds Demon Form Strength immediately and gives Rolling Boulder only generic Power utility. Hypothesis: explicit future-only effects plus bounded discounted future utility improve setup choices without more model calls.

Mechanic support: Rolling Boulder damage at next player turn, then damage increases by exported IncrementAmount; this is unpowered damage, not amplified by Vulnerable. Demon Form grants its exported Strength each subsequent player turn, none immediately. Forecast three future turns, discount0.8 each turn. Convert future Strength to damage using1 expected future attack per turn; report this as an assumption. Cap forecast damage value by enemies' remainingHP; future gains do not count as current kills or prevention of incoming attacks. Unsupported future mechanics remain unknown. Do not install setup on a predicted-lethal turn just to increase future score.

Freeze native attempt5 RollingBoulder observations and attempt4 DemonForm observations before evaluating. Audit increments and immediate Strength timing from actual stable snapshots; future utility is a heuristic, not an engine clone. Tests include no current-turn damage/Strength, upgrade stats, safe setup preference and lethal-now defense. Gate arithmetic separately from win rates.

Exploratory matched Ironclad A0: seeds a0_e026_dev_001,002,003, triggered vs horizon, all6 reported,200modelcalls/$0.50/1500actions/300s per run, global1200calls/$3. Promote policy only with more wins or at least2 better paired progress and no regressions/errors; otherwise close policy experiment retaining arithmetic findings. No native policy switch mid-E038 run.
