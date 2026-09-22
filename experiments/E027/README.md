# E027 — Native turn-boundary settling

Issue #48. Baseline main9a1e797 can regard a partial new-turn hand as actionable; E013 attempt5 s205 returned turn7 with1 card/Boulder20/Queen50, a later observation had5 cards/Boulder25/Queen30. This directly undermines strategy decisions.

Hypothesis: read-only semantic stability probing on combat entry/turn changes avoids these transient decisions without adding delay to each ordinary action. Require action readiness and an unchanged semantic snapshot for0.6s, at least0.75s total, poll0.15s, hard timeout8s. Include available actions and selection. No action retry. This is a bounded compatibility heuristic, not proof that every future asynchronous effect has completed.

Fixed validation: captured s205 before the next s206 settled state, synthetic paused/selection/continuous-change/identity-change controls, unit checks, then the next live A0 run's first3 turn transitions. Never resume from old indexes. A fresh expert proposal is invalidated if settling changes its bound state. Decision: merge only if captured/control cases pass and live transitions retain full readiness, preserve probe log/latency; timeout rather than force an action. The new user priority is A0, so the native validation uses that difficulty.
