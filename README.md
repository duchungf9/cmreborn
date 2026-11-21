# CM Reborn research

Static reverse-engineering notes and a small, independent match-view prototype for Championship Manager 03/04, plus the Shadow Fight 2 asset-analysis scripts and manifests produced during the same research session.

## Match demo

Open [`demo.html`](demo.html) directly in a browser. PixiJS 8.23.0 is bundled into the HTML, so the renderer does not need a CDN, a localhost server, or a network connection. The prototype animates 22 players and the ball, including team movement during passes and shots.

The bundled renderer's MIT license is in [`third_party/PixiJS-LICENSE.txt`](third_party/PixiJS-LICENSE.txt).

The demo is illustrative. Its receiver scoring, tactical movement targets, match outcomes, and shot probabilities are inferred. It is not a faithful replacement for the original match engine.

## Reverse notes

- [`reverse/cm0304-static-analysis.md`](reverse/cm0304-static-analysis.md) records observed native-code paths, action-state branches, and unknowns.
- [`reverse/action-state-name-map.csv`](reverse/action-state-name-map.csv) lists 210 action IDs mapped to embedded `ME_*` labels; [`reverse/extract_action_names.py`](reverse/extract_action_names.py) regenerates it from the matching `cm0304.exe`.
- [`sources/source-manifest.csv`](sources/source-manifest.csv) lists original archives and the extracted executable by size and SHA-256. The source binaries are not stored in this public repository.

## Shadow Fight 2 research

[`shadowfight/README.md`](shadowfight/README.md) describes the conversion outputs. This repository includes scripts, manifests, and the upstream tool license. Generated meshes, animation clips, previews, and original game archives remain local; [`shadowfight/artifact-manifest.csv`](shadowfight/artifact-manifest.csv) records their filenames, sizes, and hashes.

The repository is public. The game archives and extracted/converted game content were left out to avoid republishing material owned by the game rights holders. The CM 03/04 archive is also larger than GitHub's 100 MiB regular Git file limit; Git LFS is not configured here.

## Included tools

The scripts in `shadowfight/tools/` were used with Blender, NumPy, Pillow, and the community Gymnast Tool Suite. They expect the original archive and upstream rig/tool files to be supplied locally. Upstream tool source: [Gymnast Tool Suite](https://github.com/FlipThoseTitle/Gymnast-Tool-Suite) and [ShadowFightAnimationTool](https://github.com/UAETeams/ShadowFightAnimationTool).
