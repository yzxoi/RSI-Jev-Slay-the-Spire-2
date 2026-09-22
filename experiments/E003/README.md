# E003 — Does computed context improve Jev combat choices?

Issue #4. Motivation: E002 raw Jev finished faster but lost 4 more HP than first-playable in one Ironclad battle. Test arithmetic support rather than assuming more model calls improve play.

Hypothesis: static arithmetic on current card/target previews helps Jev avoid avoidable incoming damage. This is not a full simulator or turn search.

Predeclared exploratory sample: seeds `eval_001`, `eval_002`; all five characters; ascension 10; first natural combat; same fixed opening choices. Four arms: first-playable, numerical greedy, raw Jev, Jev with computed candidates. Forty episodes total. Shared Jev budget: 800 calls / $1.50; 3 independent workers. No Astra gameplay interventions.

Metrics: completion/failure, post-combat HP (including ordinary post-combat healing), paired net HP lost, action count, latency and API cost. Confirm initial state hashes agree within every seed/character. Report per-character results and ties.

Decision rule: keep computed context as the preferred experimental arm only if it improves paired mean HP versus raw Jev, wins more comparisons than it loses, and introduces no execution failure. A negative result keeps it available for study but does not promote it. Compare against greedy to assess whether a model adds value at all. Ten pairs cannot establish general high-ascension or full-run strength.

Iteration 1: add target-specific damage/kill previews, useful block, visible incoming damage and energy arithmetic. Include explicit limitations for changing modifiers, triggers, orbs, minions and end-turn powers. Add a fixed numerical baseline and tests against double-counting multi-hit damage.

```sh
python3 -m unittest discover -s tests -v
python3 -m rsi.run --seeds eval_001,eval_002 --policies first,greedy,jev,jev_features --workers 3 --max-calls 800 --max-usd 1.5 --output experiments/E003/results-v1.json
```

Results on implementation `0f2b0d1`: 5 runtime/computation tests passed; 40/40 first battles completed with no execution errors; all paired initial state hashes matched. Mean net HP lost: first 11.1, numerical greedy 5.6, raw Jev 8.5, computed Jev 7.3. Computed vs raw: +1.2 HP mean, but only 1 win / 7 ties / 2 losses. Total 358 Jev requests, $0.042865368.

Decision: close without merging. The predeclared pairwise criterion failed; the mean gain is driven by one Silent case. No claim of general improvement. Full sanitized compressed traces and per-case outcomes remain on this PR branch. A follow-up should test selective code/Jev allocation and candidate equivalence; full-turn search remains open as E005.
