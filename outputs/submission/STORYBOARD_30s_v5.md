# REDLINE — 30 s demo video (v5) storyboard

File: `REDLINE_30s_v5.mp4` · 1920×1080 · 30 fps · 30.0 s · music: team song `redline_sessiz_yorunge_take_02.mp3` (AI-generated with Suno; labelled on screen) · no speech, all on-screen text in English.
Rebuild: `render/render_v5.py` (WSL). Every number on screen is from `docs/verification/SPACE_APPS_CLAIMS.json`.

| Time (s) | Shot | On-screen line | Status pill | Source |
|---|---|---|---|---|
| 0.0–3.0 | Curiosity boxwork postcard | "Two astronauts. A few hours of oxygen." | REAL NASA IMAGE | PIA26680 |
| 3.0–4.5 | Lander touchdown | "A solar storm can arrive in minutes." | SIMULATION · UNREAL + AI 3D | `feature-videos/01_acilis.mp4` 8.5 s |
| 4.5–6.0 | Habitat mission board | "Briefing in the habitat: 12 linked tasks." | SIMULATION · UNREAL + AI 3D | `01_acilis.mp4` 30.0 s |
| 6.0–8.5 | REDLINE map: Known · Unknown · Red line | "Every unknown becomes minutes of return margin." | REAL NASA DATA + ROS 2 RUN | HiRISE atlas + C1 run |
| 8.5–10.0 | Drone flight | "A drone scouts the costliest unknown." | ROS 2 + GAZEBO FLIGHT + AI 3D | `raw-takes/02_drone_ilk_ucus.mp4` 44.5 s |
| 10.0–12.5 | Gazebo · RViz · Unreal side by side | "One rover, three views: physics, sensors, crew." | ROS 2 · GAZEBO · RVIZ · UNREAL (views recorded separately) | `09_gazebo/rviz/rover_kayalar.mp4` |
| 12.5–14.0 | Surface sample | "Sample: its origin stays on the map." | SCRIPTED SHOT · SIMULATED | `clips/task_sample.mp4` |
| 14.0–15.5 | Hand-held XRF | "690 real APXS runs: placement beats time." | SIMULATED INSTRUMENT · NASA DATA MODEL | `clips/task_xrf.mp4` |
| 15.5–17.0 | Environment station | "Environment station deployed." | SCRIPTED SHOT · SIMULATED | `clips/task_station.mp4` |
| 17.0–18.5 | Rover drill | "Rover drill on real BXW terrain." | SCRIPTED SHOT · SIMULATED | `clips/task_drill.mp4` |
| 18.5–20.0 | Habitat lab | "Lab results linked to the sample's origin." | SIMULATED LAB | `clips/task_lab.mp4` |
| 20.0–26.5 | Real solar storm | "A real solar storm, replayed." · ×61 in 53 min · 0 s to shelter mode · 6.02 → 0.41 km² · Earth 32 min away | REAL RAD DATA · ROS 2 RUN (SIMULATED WALKER) | RAD sol 4190 + C1 run + Unreal HUD replay inset |
| 26.5–30.0 | End card on Gale sunset | REDLINE · Known · Unknown · Red line · Team CRST · ariadneamerica.study · data and AI credits | — | PIA19400 |

Features shown: real NASA site and imagery · habitat and briefing · uncertainty map with red line · drone scouting (ROS 2/Gazebo) · rover LiDAR + Nav2 (RViz) · Gazebo↔Unreal link · sample custody · XRF with APXS-derived error model · environment station · drill · lab · real RAD storm replay with flight rule · Unreal HUD.
