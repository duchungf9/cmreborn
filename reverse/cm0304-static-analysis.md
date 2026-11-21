# Championship Manager 03/04: static match-engine notes

## Scope and target

These are partial static observations from the user-provided Windows release. The inspected executable is PE32 x86, version 4.1.0.0, SHA-256 `f5963ebd6c9df918b9e630402a3bed6a64357f7ff62b9a6d2a6b5d5234bd9b7a`. Addresses below are virtual addresses from the executable image. They have not been validated against other releases.

This is not a 100% reconstruction. Decision weights, most attribute effects, several helper predicates, and the full ball/shot model remain unresolved. The HTML demo deliberately labels inferred behavior.

## Observed action-state flow

- The selection routine beginning at `0x9234A0` writes an action identifier into `[object + 0x8CC]`. An action-processing routine begins near `0x92DF20`.
- In the run-with-ball path, the code compares the absolute x and y target deltas with `10`. It selects action `201` when both are strictly below `10`; otherwise it selects `200`. The source field units have not been mapped to metres.
- Other constant writes in the same selector confirm branches for `204` (`ME_WAIT_TO_FIND_SET_PIECE_ACTION`), `208` (`ME_TAKE_A_DIVE`), `212` (`ME_GK_DROP_BALL_FOR_DISTRIBUTION`), `213` (`ME_ATTEMPT_TO_ROUND_KEEPER`), and `1000` (`ME_GK_USE_SIX_SECONDS`). Their exact predicates are still being mapped.
- The run selector also calls shared helper `0x8FE890` (26 direct call sites in the executable). It scans candidate objects under a match context and uses geometry helpers. Its observed return paths produce byte values `0`, `1`, and `2`; the two run-selector branches use opposite zero/nonzero tests before choosing action `205`. Treat it as a tri-state helper whose exact meaning depends on the caller, not a global boolean “success” flag.
- The action processor at `0x92DF20` calls `0x8EB4E0` with the current action ID. That helper special-cases IDs `501–510`, writes one of ten associated constants to an output slot, and returns true; other IDs write `100` and return false. These action IDs are named as foul/violent-play events in the resolver, but the meaning of the secondary constants has not been identified.
- The observed shot path is `0x93181B → 0x94C0D0 → 0x94E980 → 0x94CBB0`. `0x94E980` repeatedly asks `0x94CBB0` for trajectory samples, increments a sample count at `+0x3EE8`, and stores values from `+0x3ED8`. A comparison against `999` bounds the loop to about 1000 samples (indices 0–999). A coefficient helper uses `0x4000` (16384) as a fixed-point scale; the coordinate units and complete trajectory equations are still unresolved.
- The normal-pass action `100` routes through a branch around `0x92EF36` and calls `0x903840`. That routine copies a 17-word context record from offset `+0x15C` to `+0x118` before related match-context updates.

## Recovered action labels

The name resolver at `0x8F5BF0` maps action IDs to embedded `ME_*` labels through jump tables and compact byte remaps. The reproducible extraction in [`action-state-name-map.csv`](action-state-name-map.csv) contains 210 named ID/label pairs; [`extract_action_names.py`](extract_action_names.py) regenerates it from the matching executable. The resolver's fallback text is `UNKNOWN ACTION`. An absent ID in the CSV therefore means “no named label recovered from this resolver,” not proof that the number can never occur internally.

The map now gives exact examples across the engine: passes and clearances (`100`, `102–124`), on-ball states (`200–214`), shot types (`300–316`), player movement/marking/interception (`400+` selected IDs), contests and ball control (`600–709` selected IDs), goalkeeper actions (`800–809` and `1000+`), tackling/fouls (`900+` selected IDs), and set-piece positioning (`1100+` selected IDs). IDs are sparse; do not treat the displayed spans as continuous enums. These are formatter labels, not evidence that each state is reachable in every match situation.

## Geometry helpers

- `0x8BC550` derives a bearing from an object's x/y at `+0x48/+0x4C` toward a target. If both coordinates match, it returns the object's heading at `+0x50`; otherwise it quantizes the deltas and looks up a heading in a table. This is the direction helper used in the run selector, not a distance result.
- `0x8C7610` computes the shortest circular difference between two 16-bit headings: absolute difference, folded around `360`, yielding a value up to `180`. Its callers compare against values such as `40` (`0x28`), confirming degree-like heading units.
- `0x8C65E0` subtracts two coordinate pairs and calls `0x8C64D0`, which computes an integer square root of `dx² + dy²`. This confirms Euclidean-distance arithmetic, but not what one coordinate unit means in metres. A separate object-distance wrapper has an optional mode that remains unmapped.

## Randomness and conditional actions

- The random-state code at `0x9747A0` / `0x974850` uses a 624-word state, the `0x6C078965` seed recurrence, the `0x9908B0DF` twist constant, and the standard MT tempering masks. This is an MT19937-family generator. Wrapper `0x8BCA20` requests a bounded draw; the multiply-high scaling maps a positive bound `n` to an integer in `[0, n-1]`. A match-context callback can intercept the generated value, so the exact stream also depends on runtime setup.
- In one branch of the selector, `0x927B06` requests `Random(100)` and compares the result with a local threshold before selecting `208` (`ME_TAKE_A_DIVE`). This confirms a percentage-sized random gate in that branch, but the threshold's meaning and the other gates around it are not decoded.
- The demo now uses an MT19937 implementation and the same bounded-integer scaling as its random source. Its seed, random-call order, thresholds, and outcomes remain prototype choices; this does not reproduce the game's match sequence.

## Tactical inputs

The game data includes team instructions for passing style, passing focus, tackling, closing down, mentality, offside trap, zonal marking, counter-attacking, and men behind the ball. Player instructions can override individual behaviors, including run-with-ball and hold-up behavior. The existence of an instruction is confirmed; its exact contribution to action scores is not.

## Demo boundary

`demo.html` uses the confirmed `200/201` target check as an anchor. Receiver selection, player motion during ball flight, pressing targets, shot choice probabilities, and outcomes are independent prototype rules. The new CSV documents the game's state labels; it does not make those prototype rules recovered engine behavior.

## Reproduction inputs

The exact source archive and extracted executable hashes are in [`../sources/source-manifest.csv`](../sources/source-manifest.csv). The game binaries are intentionally not included in this public repository.
