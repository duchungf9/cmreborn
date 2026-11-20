# Shadow Fight 2 asset-analysis outputs

This folder preserves the conversion notes, viewer source, scripts, manifests, and upstream license from the local asset study. `viewer.html` needs the local generated assets to display animations and models.

The original archive and generated game-derived content are not in this public repository. That excluded content includes the converted asset ZIP, Blender scenes, FBX/GLB files, raw animation sample, and GIF/PNG previews. `artifact-manifest.csv` records each local output's size and SHA-256 so local copies can be identified.

The study found 498 humanoid animation actions on a 32-bone rig, 62 generic effect/projectile point clips, and a library of 734 parsed static mesh assets. The converted mesh library is untextured and has no skin weights. These are research results, not rights to redistribute the game data.

Scripts in `tools/` require Blender and the original local archive. Some also use the community rig from Gymnast Tool Suite. They were authored for the original workspace layout and may need their input paths adjusted before reuse.

Attribution: decoder and rig template from [Gymnast Tool Suite](https://github.com/FlipThoseTitle/Gymnast-Tool-Suite), licensed under GPL-3.0; the game models and animation data remain the property of their respective rights holders. See [`LICENSE_GymnastToolSuite.txt`](LICENSE_GymnastToolSuite.txt).
