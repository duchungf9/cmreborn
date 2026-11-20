# Championship Manager 03/04: static match-engine notes

## Scope and target

These are partial static observations from the user-provided Windows release. The inspected executable is PE32 x86, version 4.1.0.0, SHA-256 `f5963ebd6c9df918b9e630402a3bed6a64357f7ff62b9a6d2a6b5d5234bd9b7a`. Addresses below are virtual addresses from the executable image. They have not been validated against other releases.

This is not a 100% reconstruction. Decision weights, most attribute effects, several helper predicates, and the full ball/shot model remain unresolved. The HTML demo deliberately labels inferred behavior.

## Observed action-state flow

- The selection routine beginning at `0x9234A0` writes an action identifier into `[object + 0x8CC]`. An action-processing routine begins near `0x92DF20`.
- In the run-with-ball path, the code compares the absolute x and y target deltas with `10`. It selects action `201` when both are strictly below `10`; otherwise it selects `200`. The source field units have not been mapped to metres.
- A nearby helper path calls `0x8FE890`; when that predicate succeeds, the selector writes action `205`. The helper's complete semantics have not been recovered.
- The observed shot path is `0x93181B → 0x94C0D0 → 0x94E980 → 0x94CBB0`. The last routine samples/plans a ball trajectory. Inspected arithmetic uses elapsed time as a percentage of duration and caps plotted samples at 1000; coordinate scaling is fixed-point in the inspected path.
- The normal-pass action `100` routes through a branch around `0x92EF36` and calls `0x903840`. That routine copies a 17-word context record from offset `+0x15C` to `+0x118` before related match-context updates.

## Action families identified from embedded names

The executable contains action-name strings covering pass/cross/clearance/set pieces (`100–124`), on-ball control and movement (`200–214`), shots (`300–316`), off-ball positioning/marking/interception (`400+`), ball contests (`700+`), goalkeeper saves (`800+`), tackling (`900+`), and keeper/set-piece actions (`1000+`). These ranges summarize mapped examples, not every value in each range.

## Tactical inputs

The game data includes team instructions for passing style, passing focus, tackling, closing down, mentality, offside trap, zonal marking, counter-attacking, and men behind the ball. Player instructions can override individual behaviors, including run-with-ball and hold-up behavior. The existence of an instruction is confirmed; its exact contribution to action scores is not.

## Demo boundary

`demo.html` uses the observed action names and the confirmed `200/201` target check as anchors. Receiver selection, player motion during ball flight, pressing targets, shot choice probabilities, and outcomes are independent prototype rules. They should not be read as recovered source behavior.

## Reproduction inputs

The exact source archive and extracted executable hashes are in [`../sources/source-manifest.csv`](../sources/source-manifest.csv). The game binaries are intentionally not included in this public repository.
