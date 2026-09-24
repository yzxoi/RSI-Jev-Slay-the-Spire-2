# E090 — state-bound Astra Boss room plans

Issue: [#172](https://github.com/yzxoi/RSI-Jev-Slay-the-Spire-2/issues/172). Source cohort: E089 held-out A10, tested SHA `4c64f8bf12dab89df102b4b3354188389724ec54`. Downstream baseline: merged `retaliate` at `b22c28ebed9342fa81a0c94109118024fb226d04`.

Hypothesis: an Astra-authored, exact-entry-bound Boss room plan can improve selected failed Boss fights by supplying a concrete long-horizon objective and potion budget, while Jev chooses the first legal action each turn and the deterministic planner handles the rest. The four cases were chosen **after observing E089's Boss defeats**: Ironclad `_004` vs Ceremonial Beast, Silent `_005` vs Vantom, Regent `_006` and Necrobinder `_006` vs Kin Priest. This is a mechanistic pilot and cannot estimate win rate or justify general deployment on its own.

[fixtures.json](fixtures.json) freezes each source trace/wire hash, command prefix and exact Boss entry hash. [plans.json](plans.json) contains four Astra plans authored from only the frozen **entry state** (current hand/deck, relics, potions, enemy powers/intents and known Boss) before any E090 replay. Each plan has one-room scope, explicit potion limit and concise guidance. Plans are user-visible data, not hidden model reasoning. A plan expires on leaving its Boss room. The controller will ask Jev once at the first action of each Boss turn, passing the plan, fresh state, legal card/potion choices and numerical planner proposal; a Duplicator potion gets one immediate follow-up Jev card choice so the doubled card is deliberate. The normal `retaliate` planner handles other combat actions. Macro behavior stays unchanged. No HP, reward, RNG or victory edits.

Frozen evaluation: baseline and treatment at each of four exact entries = eight A10 CLI continuations. Each stops at the first Boss-room exit: `boss_room_cleared` for a real clear or `normal_defeat` for a loss. Two workers; max 2,000 decisions/300 seconds each, shared Jev max 1,000 calls/$0.50 with exact-request matching. Game v0.111.0, sts2-cli `084d1aa3d8e118ca7ce8d8774ad16d6be9c92367`, Jev `typesafe/jev-1.13-20260917`. Raw traces remain ignored in `artifacts/runs/`; compact results and hashes will be committed.

Decision: all eight entry hashes and raw trace hashes must verify; all runs must end normally, and plan actions/potion limits must be legal and state-bound. The pilot needs at least two new Boss clears among treatment cases while baseline clears no more than one. A pass merges only opt-in plan/replay tooling for a separate held-out full-run test. Otherwise close without promotion. Selected failures, later RNG divergence and a four-case sample are explicit limits.

## Exact-entry evaluation result

The freezer, four frozen prefixes/plans, state-bound replay controller, evaluator and tests were committed as `98c64a909d27d6f8a8aff402438c2c0dc8f69de5` **before** game execution. `python3 -m unittest discover -s tests -q` passed 115 tests. Exact command: `python3 -m scripts.evaluate_boss_plan_e090 > artifacts/runs/e090-eval-stdout.log 2>&1`. Original game DLL SHA-256 `9cb4f1ad8c9f284aa8fec3122ffd6d780bbf543d875c817abdd12ff63fbf12b4`; exact headless assembly, patches, dependencies, fixture/plan hashes, configs and per-run raw trace hashes are in [result.json](result.json).

All **8/8** continuations reached their frozen exact Boss entry hash and then stopped at a real Boss-room boundary. All eight raw trace hashes, plan presence/absence, selected-action legality, plan-room scope and potion budgets verified. There were no execution errors or stalls. The treatment made 35 recorded Jev Boss decisions (including one controlled Duplicator follow-up), with 42 total attempted Jev calls across both arms and $0.009011016 provider-reported/budgeted spend; no uncertain calls. No HP, reward, RNG or victory edit occurred.

| Character, Boss | Baseline Boss result | Astra-plan Boss result | Last observed enemy HP, baseline → treatment |
| --- | --- | --- | --- |
| Ironclad, Ceremonial Beast | defeat, round 14 | **clear, round 10** | 63 → 4 before the final action |
| Silent, Vantom | defeat, round 7 | defeat, round 7 | 117 → 87 |
| Regent, Kin Priest | defeat, round 6 | defeat, round 6 | 248 → 248 |
| Necrobinder, Kin Priest | defeat, round 9 | defeat, round 7 | 142 → 199 |

Ironclad's plan caused a Strength Potion on turn 1 and Duplicator followed deliberately by an attack on turn 5, then a genuine Boss clear. Silent followed some multi-hit guidance but used neither of its two potions; Regent used Energy Potion but not Duplicator; Necrobinder used neither potion. Thus a free-text plan can be legally delivered yet not reliably turn its resource intention into action. The enemy-HP figures are sums at each arm's **last before-action state**, not matched-turn damage estimates, and the branches can diverge in RNG and later choices.

Decision: **close without merging**. The mechanistic pilot achieved one new Boss clear versus the preregistered minimum of two. One selected known failure becoming a clear is valuable evidence that a state-bound plan can change a real battle, but the other three losses and case selection prevent any general strength claim. The replay tooling and failed plan histories stay on this closed PR branch. The next atomic test should make Astra's opening resource/card action a typed, freshly validated directive rather than relying on Jev to infer it from free text; it needs a separate issue and result, not a post-hoc E090 retest.
