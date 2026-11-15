# REDLINE v8 — sources, data status and AI disclosure

15 November 2026 · `REDLINE_30s_v8.mp4` · 30.000 s · 1920×1080 · 30 fps · H.264 / AAC stereo.
Rebuild: `render/render_v8.py`. Earlier video edits and raw takes are preserved.
The original first-edit credits are archived in `CREDITS_AND_AI_v1.md`.

| Time | Source | Status / transformation |
|---|---|---|
| 0–2.8 s | `outputs/feature-videos/01_acilis.mp4`, source 2–4.8 s | Scripted Unreal arrival; cropped and scaled; some Tripo AI models |
| 2.8–6.8 s | `data/engines/BXW/tablet-atlas-v1` imagery/hillshade; `render/run_compact.json` | HiRISE/USGS site imagery and derived terrain; recorded ROS return boundary and simulated walker. Existing imagery/hillshade composite retained. Rendered overlays use muted colours; no terrain data changed. |
| 6.8–10.8 s | `outputs/raw-takes/09_gazebo_kayalar.mp4` 12–16 s; `09_rviz_kayalar.mp4` 95–99 s; `09_rover_kayalar.mp4` 0–4 s | Three actual, separately recorded views. Cropped/scaled and composed. This is not simultaneous recording, a new navigation test, proof of completed avoidance or goal arrival. RViz colours are unchanged. |
| 10.8–13 s | `outputs/raw-takes/02_drone_ilk_ucus.mp4`, source 56–58.2 s | Actual prior Gazebo-controlled scout shown in Unreal, during SURVEY. Observations are SIMULATED truth-adapter data, not camera reconstruction. Pre-stabilization recording; not a new stabilized-flight acceptance. No claim that this flight selected the highest-value unknown. |
| 13–15.5 s | `outputs/feature-videos/06_sondaj_v2.mp4`, source 9–11.5 s | Scripted Unreal rover/drill demonstration. Simulated operation, not measured physical drilling. |
| 15.5–19 s | `assets/video/clips/task_lab.mp4`, source 14–17.5 s; `outputs/feature-videos/results/data/laboratuvar_ph_ec.csv` | Scripted habitat lab and exact recorded simulated assay values. All 31 rows plotted; no filtering, normalization or smoothing. Connecting lines describe model samples. Not a measured Gale or Phoenix assay. Final pH 7.805617…; conductivity 1.217316… mS/cm. Figure, SVG and provenance: `render/v8-assets/lab-result.*`. |
| 19–26.5 s | `render/run_compact.json` from `runs/20261115T101234Z-C1_SOL4190_CHAPTER-42/ue_feed.jsonl`; `data/env/rad_4190.csv` | Recorded ROS scenario, simulated walker, real 20 May 2024 Curiosity RAD detector-E absorbed dose. Before/after recorded boundary endpoints crossfade at their original coordinates. Edited time compression is not live screen recording or per-frame replay. RAD points are connected; the moving tip uses linear interpolation. |
| 26.5–30 s | `render/nasa/PIA19400.jpg` | Gale sunset: NASA/JPL-Caltech/MSSS/Texas A&M University. Dimmed and reframed for the end card. |

## Data claims

- Radiation rise ×61: source `docs/verification/SPACE_APPS_CLAIMS.json`, `rad_spike`; alarm 05:21:50 UTC, peak 06:15:19 UTC. The approximately 53 minutes is alarm-to-peak, not the length of the edited scene.
- Communication: source `light_time` in the same ledger. 15.84 min one way, 31.67 min round trip. V8 explicitly describes a question and answer.
- V8 removes the unqualified zero-second latency claim, the claim that the shown drone selected the costliest unknown and the false `same run` Unreal inset.
- Recorded map geometry is not newly measured by this edit. No scientific values are generated to match the footage.

## Models, software and images

Some models were made with Tripo AI. The NASA Curiosity visual and other pre-existing assets retain their project source notices. The rocks are **Poly Haven `rock_07`, Jenelle van Heerden, CC0**, not Tripo models: `assets/incoming/rock_07/SOURCE.md`. Positions and sizes are SCENARIO.

Map sources: MRO HiRISE imagery and the USGS Gale terrain mosaic, including the inputs recorded in the repository's data manifests. This is not a claim that every terrain input comes only from NASA. Science data and NASA images are not AI-generated.

Code/editing assistance: OpenAI Codex and earlier project AI-assisted work, as recorded in `docs/AI_DISCLOSURE.md`. Existing source, licence and prior-work notices remain applicable. This document does not assert event-rule compliance.

## Audio

- Music: `assets/audio/incoming/redline_sessiz_yorunge/redline_sessiz_yorunge_take_02.mp3`, generated with Suno under team direction; credit remains on screen.
- Opening Foley: existing `assets/narrative/prologue_v1/landing_thrust.wav`, deterministic local procedural synthesis, not an external recording.
- At 21.2 s: existing `ready_chime.wav`, used as an explicitly edited warning cue, not claimed as an actual recorded alarm from that ROS run.
- Mix: 48 kHz stereo. No voiceover, no new generated sound, no microphone capture. Source hashes and gains are recorded by `render_v8.py` and `render/v8-assets/edit-manifest.json`.

On-screen AI/source notes use plain, muted text in the footer and end card. The visual change reduces prominence without removing the disclosure.
