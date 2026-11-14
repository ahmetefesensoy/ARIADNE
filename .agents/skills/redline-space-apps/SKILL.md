---
name: redline-space-apps
description: Develop REDLINE Marswalk mission ideas, ROS–Unreal integration, planetary data workflows and Space Apps deliverables in this repository. Use for project architecture, campaign design, NASA data provenance, integration experiments and submission planning; not for unrelated repositories or general software questions.
metadata:
  project: REDLINE
  version: "1.1"
---

# REDLINE Space Apps

Use this project's actual state and the user's current direction. The design is
allowed to change. Read [README](../../../README.md) first. The current design is
[REDLINE v3](../../../research/proje-fikirleri/REDLINE_V3_KILAVUZU.md); implementation starts from
[the v3 spec](../../../research/proje-fikirleri/REDLINE_V3_UYGULAMA_SPEKI.md), sections 0–4 and 18.
Older guides and research notes are supporting history, not the current scope.
Consult only the relevant sections of
[source catalog](../../../research/proje-fikirleri/KAYNAK_VE_VARLIK_KATALOGU.md),
[site research](../../../research-notes/SAHA_VE_BILIM_ISTASYONU.md) or
[mission proof plan](../../../research-notes/GOREV_DEGERI_VE_KANIT_PLANI.md).
For a fresh repository, use [the handoff](../../../research/handoff/YENI_DEPO_AKTARIMI.md).

## Choose the specialist

Use the smallest useful combination. Installed entries are sibling folders.

| Work | Skill and use |
|---|---|
| ROS nodes, launch, QoS, TF, navigation, MoveIt and Gazebo | `ros2-engineering-skills`; inspect the actual Jazzy workspace and relevant reference |
| UE C++ and module/plugin wiring | `ue-cpp-foundations`, `ue-module-build-system` |
| Robot telemetry and commands in UE | `ue-blueprint-cpp-interop`, `ue-async-threading`; preserve ownership and game-thread lifetime |
| Habitat map, tablet, graphics and interaction | `ue-ui-umg-slate`; use common target/sample IDs |
| Current UE project inventory | `ue-project-context`; keep unknowns explicit |
| UE performance or regression | `ue-testing-debugging`; measure the relevant build/path |
| Planetary targets and product context | `planetary-geologist`; verify quantitative claims with NASA/PDS/USGS sources |
| DEM, raster/grid/CRS and vector operations | `geomaster`; replace terrestrial assumptions with verified planetary metadata |
| New research/mission directions | `scientific-brainstorming`; separate proposals from findings |
| Comparison, confounding, evidence or uncertainty | `scientific-critical-thinking`; use an appraisal appropriate to engineering, not an automatic clinical checklist |
| Scientific plots and notebooks | `scientific-visualization`, `jupyter-notebook` |
| Important alternatives and review | `quorum`; use its current capability limits and disclose actual mode/worker provenance |
| GitHub CI or review feedback | `gh-fix-ci`, `gh-address-comments`, within the requested repository/task |

3D work uses available user skills such as `blender-director`, `hard-surface`,
`vehicle-artist`, `environment-artist`, `asset-optimization`, `collision-proxy`,
`lod-pipeline` and `unreal-export`. Read their instructions when relevant. Check
actual Blender/MCP/export capabilities; installing instructions does not install
an editor connector, AI generation subscription, compiler or ROS package.

## Preserve the integration contract

- Inspect the existing demo or template before designing around it. There is no
  completed REDLINE Unreal project/bridge merely because the engine is installed.
- Retain a single physics/control owner for each robot. Do not independently
  simulate the same rover in Gazebo and Unreal and call the poses equivalent.
- Specify metres/right-handed ROS frames, centimetre/handedness conversion in UE,
  common origin and TF names. v3 distinguishes Gazebo physics `/clock` from the
  mission/PET clock; preserve measured, publication and freshness time semantics.
- UE's human needs the proposed Gazebo/ROS proxy when robot perception, escort
  and avoidance depend on that person. Distinguish permitted estimated state
  from hidden simulator truth.
- Async bridge callbacks must respect UObject lifetime and game-thread access.
  Distinguish command acceptance from execution/result; define manual/autonomous
  ownership, cancellation, timeout and recovery after reconnect.
- Keep unknown/stale/conflicting observations visible. Sensor simulation must not
  grant the planner an unseen world-object list.

For an integration change, name the input/output record, authority, success and
failure behavior and smallest observable check. A proposal, compilable code,
connected topics and a completed physical/simulated task are different evidence.

## Keep Mars data meaningful

- Record mission/product/version, observation time, coordinate convention, units,
  missing data, transformations and source/quality with the relevant target.
- Verify planetocentric/planetographic latitude, longitude direction/range,
  projection sphere/ellipsoid and vertical reference. Never silently use EPSG:4326
  for Mars. Numeric bbox containment is candidate coverage, not pixel/footprint
  or exact sample-location validation.
- v3 uses Boxwork-West (BXW) for the forward EVA and Yellowknife Bay (YKB) for
  calibration/consistency checks. Five phases belong to one EVA. Gobabeb is an
  older research profile, not the current default campaign. John Klein/Cumberland
  are nearby targets in the same Sheepbed unit. Historical holes, APXS record
  coordinates, sample origins and new scenario objects are distinct.
- Link sample origin/depth/time/container to preparation, instrument location,
  assay and quality. A laboratory coordinate does not replace collection origin.
- Gale pH/other new assay outputs are explicitly simulated unless an actual
  matched archive measurement is established. Phoenix WCL is a separate location
  and procedure reference. Do not infer pH from colour or mineral percentages.
- Bound claims to the observed sample/support/resolution. Archive measurements
  can guide interpretation and selection without every layer changing the route.

## Fresh implementation

Write the new application from scratch under the v3 spec. Do not copy the old
ROS demo, rover repository or previous application algorithms. Skills, research
notes and source/provenance records are prior materials; preserve their licences
and disclose prior use where required. Existing machine paths and the external
Blueprint template are inventory, not a completed new C++ project. Verify open
APIs/data semantics and record evidence rather than promoting a prior label to
a new validation result.

## Evolve missions and submission honestly

For a proposed feature, identify the astronaut's job, the information or robot
capability it adds, how the user acts, and a test that could show it unhelpful.
Let rover, drone and human have different access/resource profiles. A rejected
operation may be appropriate while the intended science remains incomplete.

Check current official challenge/event rules and asset/data licences for an
actual submission. Keep prior work, new work, sources and required AI disclosures
traceable. Do not infer a year's rules from an older event or publish a private
repository merely because a submission is planned.

Use [the skill plan](../../../research/proje-fikirleri/SKILL_PLANI.md) for installation/source details.
Update the relevant design or implementation artifact when the task calls for
work; a list of ideas alone is not completion of an implementation request.
