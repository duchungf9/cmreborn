# CM 03/04 match-engine reverse task

- Keep pursuing the native match-engine reverse across turns until the user cancels or the completion criteria below are met. Do not stop at a progress report or label a partial reconstruction complete.
- At each meaningful reverse milestone, add evidence and unresolved questions to `reverse/cm0304-static-analysis.md`, then update the playable `demo.html` to reflect newly verified behavior and sync it to `/home/testuser/Documents/Codex/2026-11-20/home-testuser-downloads-mygame-xapk/demo.html`.
- Treat static observations, dynamic validation, and prototype choices separately. Do not map an offset to a named player attribute or claim full fidelity without evidence. Keep inferred demo behavior visibly labeled.
- Completion requires coverage of the action decision/transition loop, player movement and off-ball decisions, pass/shot/set-piece execution, ball trajectory/contact/keeper outcomes, and relevant match/tactical state interactions. The demo must implement the verified rules in those areas, and remaining gaps must be explicitly enumerated; do not claim “100%” while material rules remain unresolved.
- The user previously authorized SSH pushes to `git@github.com:duchungf9/cmreborn.git`; continue pushing this task's commits. Stage only task files. Preserve unrelated user changes, including existing `shadowfight/` deletions.
