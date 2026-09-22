# E031 — Native Crystal Sphere compatibility

Issue #52. Baseline492ed9c stops after the paid event because only proceed was offered, while the native scene requires spending its divinations first. Preserve E013 s128 as the compatibility failure; payment already happened once.

Enumerate exactly advertised hidden cells with atomic big/small tool actions and expose the board in pilot observations. Existing fingerprints already include crystal_sphere. Do not invent item identities: unrevealed kind/is_good remain null. No automatic strategic ranking or strength claim.

Evaluation: scene contract tests (coordinates, completion, absent actions, board mutation), then at most three clear actions in the existing attempt5 floor38 board. Accept only after each native divination decrease and normal scene completion, with full traces. No reset, replay or game-value modification.

Result at20e7743: all8 scene/board tests passed. Exactly3 native clears at(1,8),(3,8),(9,4), each big, continued the same paid board. Observed remaining counts3→2→1, and the last clear transitioned directly to REWARD. The first two revealed good CardReward/Gold items. Coordinate choices used occupied geometry plus an explicitly labeled inference from owned game creation order and MCP-preserved item order; the adapter itself never invents unrevealed kind/is_good. Full transition traces retained. Accept compatibility; no counterfactual or high-ascension strength claim.
