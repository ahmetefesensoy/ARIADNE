# ARIADNE — Space Apps 2026 project submission text (draft)

Team CRST · Ankara · Challenge: Interplanetary Survival Guide: Martian Map.
Replace the bracketed links before submitting. Every number below comes from the claim ledger
(`docs/verification/SPACE_APPS_CLAIMS.json`); do not add numbers that are not in it.

---

## Project name

ARIADNE — Mars EVA planning and rehearsal

## High-level project summary (≈150 words)

Mars maps work at regional scale. At the scale where an astronaut walks, they cannot say what they do not know. How far a crew can go depends on oxygen, terrain and radiation, and radiation can change within minutes. On 20 May 2024, Curiosity's radiation detector saw a 61-fold rise in 53 minutes. A question to Earth and its answer would have taken about 32 minutes.

ARIADNE turns every unknown on the map into minutes of return margin. It draws one line: the farthest the crew can go and still reach shelter in time. The line grows when a robot resolves an unknown and shrinks when a solar storm arrives.

We built the planning core on real NASA data, ran it in ROS 2 with Gazebo robots, and rehearse the walk in Unreal Engine. When we replayed the real 2024 storm, the shelter rule triggered in 0 s. The safe-return area shrank from 6.02 to 0.41 km².

## Links

- Project demo (30 s video): https://youtu.be/4aTVG5DYbDs
- Final project / repository: https://github.com/ahmetefesensoy/ARIADNE

## Detailed project description

**What it does**
- **Map product:** a map of one EVA site, Boxwork-West in Gale crater, built on a 1 m HiRISE-based terrain model. Each layer has a decision role and a data-status label: ARCHIVE, DERIVED, SIMULATED or SCENARIO.
- **Return margin:** a suited walking-cost model and a return-time field toward shelter give, for every cell, how many minutes of margin remain.
- **Red line:** the boundary of the area from which the crew can still get back to shelter in time. It is recomputed live as the mission clock, consumables and environment change.
- **Space weather:** real MSL RAD dose-rate data for sol 4190 is replayed. A rule based on Löwe et al. (2025) — an alarm on a 25% rise over background — triggers a flight rule: warning time must be at least the time needed to reach shelter.
- **Robots:** a rover (Nav2, LiDAR) and a drone (physics in Gazebo) are sent to the unknown that costs the most margin. Their observations update the plan.
- **Rehearsal:** a first-person Unreal Engine rehearsal of the same EVA. Robot physics and control stay in ROS 2 / Gazebo; Unreal only presents.

**Results (each backed by a recorded run or test)**
- **Real solar storm (20 May 2024, Curiosity RAD):** dose rate rose from 5.7 to 351 µGy/h (×61). The first alarm fired at 05:21:50 UTC and the peak came at 06:15:19 UTC, 53 minutes later.
- **Storm replay in ROS 2:** the shelter rule held at once. The safe-return area went from 6.02 to 0.41 km².
- **Real-time storm chapter:** the real alarm hits 11.8 min into the walk. The crew switches to shelter mode in 0 s and is home 8 min later, with no flight rule broken (simulated walker).
- **Robot scouting:** a simulated drone found 16 blocked cells on the planned route. The plan changed from v1 to v2 with no rule violations.
- **Suit leak:** caught from telemetry in 36 s. The whole crew was sent home with a lowest margin of +17 min.
- **Instrument finding from 690 archive APXS measurements:**
  - Counting 6× longer cuts major-oxide error by only 7–29%; counting statistics would predict 59%.
  - Each extra cm of standoff adds 6–24% error.
  - So station time is better spent on good placement than on longer measurements.
- **Sensitivity:** the storm-time safe area (0.38 km²) moves most with:
  - warning time: 0.25–0.82 km²;
  - walking speed over terrain no robot has seen: 0.31–0.54 km².

  This is why resolving unknowns first with robots matters.
- **Tests:** 700 automated core and data tests pass.

**Benefits and intended impact**
- One number (minutes) and one line instead of seven data layers.
- Every decision is logged and traceable to its data.
- The same pipeline can move to another site through a manifest, for example Jezero or the lunar south pole.
- Intended users: EVA planners, analog field teams and crew training.

**Tools and languages**
- Python 3.12: GDAL/rasterio, NumPy, SpiceyPy, pytest.
- ROS 2 Jazzy, Gazebo Harmonic, Nav2, rosbridge.
- Unreal Engine 5.8 (C++).
- STAC metadata.

**Limits (stated in the product)**
- Suit and metabolic parameters are scenario values.
- Drone observations and instrument chemistry are simulated and uncalibrated.
- RAD measures absorbed dose at the rover (Gy), not human effective dose (Sv).
- Only one site has been fully processed.
- The storm map in the video uses a recorded ROS run with a simulated walker and an edited alarm transition.

## NASA data

- **MRO HiRISE / USGS Gale DEM mosaic** (`MSL_Gale_DEM_Mosaic_1m_v3`): 1 m terrain, slope and walking time.
- **MRO HiRISE DTM** `DTEEC_019698_1750_019988_1750_U01`: second terrain model; the difference between the two is the terrain-uncertainty ("unknown") layer.
- **HiRISE colour mosaic of Gale** (`MSL_Gale_HiRISE-LRGB_78quads`): map and surface colour.
- **MSL RAD RDR, PDS PPI** (`RAD_RDR_2024_139_17_46_4189`, `…_140_18_30_4190`, `…_141_19_08_4191`): the real 20 May 2024 solar storm.
- **MSL APXS supplement, PDS Geosciences** (sols 0–2301, 690 measurements): instrument error model.
- **NAIF SPICE** (`naif0012.tls`, `pck00011.tpc`, `de440s.bsp`): Sun angle, daylight, local time, light time to Earth.
- **MSL MMGIS / PLACES**: rover positions and traverse.
- **NASA end-card image in the current video:** PIA19400 (NASA/JPL-Caltech/MSSS/Texas A&M University). HiRISE/USGS sources supply the site map.
- **NASA 3D Resources:** Curiosity model (visual only).

## Space agency partner and other data

- **ESA Mars Express HRSC** data is one of the inputs to the USGS Gale DEM mosaic. We therefore do not call the terrain "all NASA".
- **MSL APXS** was contributed by the Canadian Space Agency (CSA). [check]
- **MSL RAD** was developed by SwRI and Kiel University with NASA and DLR support. [check]
- **Literature used for parameters:**
  - NASA/TP-2009-214796, suited walking cost;
  - Löwe et al. 2025 (arXiv 2502.02469), alarm rule;
  - Berger et al. 2020, APXS.

## Use of artificial intelligence

- **Code:** written with AI coding assistants, Anthropic Claude Code and OpenAI Codex, under team direction and review.
  - Every result claim is checked automatically against a recorded run or test (claim ledger).
- **3D models:** some were generated with Tripo (AI). The video footer and end card disclose this as "Some 3D models: Tripo AI".
- **Music:** the video music was generated with Suno (AI). It is labelled on screen.
- **Not AI-generated:**
  - NASA images and science data;
  - the numbers shown, which come from NASA archive data and our own runs.
- No NASA logo or branding is used in AI-generated content.

## Pre-existing work

- Ideation and research notes from before the event are published in the repository's research folder, with their dates.
- Earlier prototype code was not reused.
- Third-party assets and tools keep their own licences.
