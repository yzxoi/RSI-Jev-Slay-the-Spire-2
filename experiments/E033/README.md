## Hypothesis
The assisted A0 victory depended on choosing complementary draw/energy/block/scaling and recognizing when a current-hand planner undervalues setup or exhaust effects. A small state-triggered strategy pack, deck capability counts and computed turn proposal supplied to Jev will transfer these decisions without Astra choosing ordinary cards/rewards. This changes decision support, not model weights.

## Baseline and scope
Main9a1e797: planned combat + existing Jev macro decisions. Treatment `guided`: same legal candidates and engine, Jev receives retrieved mechanic lessons and a numerical proposal on strategic combat states; simple combat uses the existing planner. Native and CLI share the lesson builder. Retain failure routing; no HP/reward/state edits.

The user now prioritizes fast stable A0 with few Astra calls. Develop first on Ironclad A0; no claim of cross-character strength from that sample.

## Preregistered evaluation
Development: Ironclad A0 seeds a0_e033_dev_001,002,003, baseline planned vs guided, maximum4000 actions/run,6000 Jev requests/$2 total,3 workers, matched identical decisions. Report victory/act-aware progress, execution errors, wall time, Jev usage and strategic-router frequency. No Astra intervention in CLI evaluation.
If treatment produces more wins or improves at least2/3 pairs without lower mean act-aware progress, test fresh held-out seeds a0_e033_hold_001,002 across all five characters, same caps. Do not label stable until a separate fresh10-run Ironclad A0 sample achieves at least8 wins plus visible validation with <=3 strategic Astra interventions/run. Infrastructure repair calls counted separately, never hidden.

## Decision
Keep as optional experiment unless held-out results improve wins or paired progress with no extra execution errors. Negative/mixed results remain committed/commented and closed. Separate causal improvement from offline imitation agreement; don't optimize reward choices on held-out seeds.

Implementation v1: shared native/headless retrieval module provides observed mechanic lessons, explicit capability counts and limitations. Guided combat asks Jev only for playable setup/specific draw-exhaust cards or active unmodeled trigger mechanics; ordinary current-hand planning stays unchanged. Macro choices receive the same contextual lesson pack. No confidence-to-win conversion, policy mutation mid-run, additional Astra or forced winning archetype. Baseline remains unchanged. This is a bundled decision-support policy experiment; it cannot attribute effects to an individual lesson.

Development v1 tested b7039d4:6 runs,0 victories,5 normal defeats and1 baseline execution error (Amalgamator repeat after asynchronous card selection). Two valid pairs:1 treatment improvement (Act1 floor17→Act2 floor5),1 tie; third pair is incomplete/error, not ranked.345 Jev calls,$0.064712004. Guided strategic calls0/29/132 across seeds. Gate for held-out is not met. Preserve this contaminated development result, repair the distinct simulator boundary in a separate issue/PR, then rerun preregistered development with the repair on both arms. No policy changed based on these seeds yet.34 checks passed.
