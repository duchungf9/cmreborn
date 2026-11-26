# CM Reborn research

Static reverse-engineering notes and an independent match-view prototype for Championship Manager 03/04.

## Match demo

Open [`demo.html`](demo.html) directly in a browser. PixiJS 8.23.0 is bundled into the HTML, so the renderer does not need a CDN, a localhost server, or a network connection. The prototype animates 22 players and the ball, including team movement during passes and shots.

The bundled renderer's MIT license is in [`third_party/PixiJS-LICENSE.txt`](third_party/PixiJS-LICENSE.txt).

The demo is illustrative. Its receiver scoring, coordinated tactical movement targets, match outcomes, and shot probabilities are inferred. The movement update borrows general ideas from open 2D football simulations (team shape, pressing roles, marking, support runs, and steering); it does not copy or establish CM 03/04 behavior. It is not a faithful replacement for the original match engine.

## Reverse notes

- [`reverse/cm0304-static-analysis.md`](reverse/cm0304-static-analysis.md) records observed native-code paths, action-state branches, and unknowns.
- [`reverse/action-state-name-map.csv`](reverse/action-state-name-map.csv) lists 210 action IDs mapped to embedded `ME_*` labels; [`reverse/extract_action_names.py`](reverse/extract_action_names.py) regenerates it from the matching `cm0304.exe`.
- [`sources/source-manifest.csv`](sources/source-manifest.csv) lists original archives, the extracted executable, and inspected match/movement lookup tables by size and SHA-256. The game binaries and extracted tables remain local and are not stored in this public repository.

The repository contains no original game archives or extracted game assets. The CM 03/04 archive is larger than GitHub's 100 MiB regular Git file limit; Git LFS is not configured here.
