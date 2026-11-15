# Visual showcase sources

14 November 2026. These derived preview assets are recreated by
`scripts/t4_prepare_visual_showcase.py` and `scripts/t4_prepare_atmosphere.py`.

The rover uses the existing NASA/JPL-Caltech package in
`assets/incoming/rover_1`, preserving its source metadata, original atlas and
material bindings. See `assets/incoming/rover_1/asset.json`,
`assets/incoming/rover_1/SOURCE.md`,
`assets/incoming/curiosity_reference/download.json` and
`docs/3D_ASSET_DELIVERY.md` for source notices.
The source master is not edited. Body and wheel FBX derivatives live under
`data/engines/rover-live-parts-v1`; their export and import reports record scale
and source hashes. This is a visual rover model, not flight hardware CAD.

Terrain/atlas dependencies retain the BXW product provenance recorded in
`docs/DATA_SOURCES.md` and the T4 fixture manifest. Procedural micro normals,
wheel depressions/tread decals, dust atmosphere, diffuse fill and test boxes
are SCENARIO art parameters, not new NASA observations. Original data and
derived geometry must not be relabelled as AI-generated or measured sand detail.

SkyAtmosphere, shape meshes and the sunset reflection cube reference installed
Unreal Engine content, including `/Engine/MapTemplates/Sky/SunsetAmbientCubemap`.
Those engine resources retain Epic's applicable terms; this file grants no
new licence. No models were generated and no generation credits were spent
for this lighting correction.

Robot collision, control and physics remain in ROS/Gazebo. Unreal assets are
presentation-only. Final reference matching, close-range rock dressing and
granular soil simulation have not been accepted.
