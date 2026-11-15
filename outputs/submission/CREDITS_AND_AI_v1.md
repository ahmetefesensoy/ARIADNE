# REDLINE 30 s demo video — sources, data status and AI disclosure

File: `REDLINE_30s.mp4` (1920x1080, 30 fps, 30.0 s, H.264/AAC, no speech; all on-screen text in English).
Rebuild: `render/render_video.py` in WSL (python3 + numpy + Pillow + ffmpeg); NASA images used are in `render/nasa/`.

| Time | Shot | On-screen status | Source |
|---|---|---|---|
| 0-4 s | Boxwork region postcard | REAL NASA IMAGE | NASA/JPL-Caltech, Curiosity, PIA26680 |
| 4-7 s | Lander touchdown | SIMULATION (Unreal) + AI-GENERATED 3D MODELS | `outputs/feature-videos/01_acilis.mp4` |
| 7-9 s | Boxwork from orbit | REAL NASA IMAGE (greyscale, warm tint) | NASA/JPL-Caltech/University of Arizona, HiRISE, PIA26306 |
| 9-14.5 s | REDLINE map | REAL NASA DATA + ROS 2 RUN | HiRISE colour + hillshade (tablet atlas BXW); margin tile and red line from run `20261115T101234Z-C1_SOL4190_CHAPTER-42` |
| 14.5-16.7 s | Drone flight | ROS 2 + GAZEBO FLIGHT (shown in Unreal) + AI-GENERATED 3D MODELS | `outputs/raw-takes/02_drone_ilk_ucus.mp4` 44.5-46.7 s; observations are simulated |
| 16.7-18.5 s | RViz | ROS 2 · RVIZ | `outputs/raw-takes/09_rviz_kayalar.mp4` 97.0-98.8 s; real RViz pixels of the Gazebo rover (LiDAR costmap, Nav2 plan) |
| 18.5-25.5 s | Solar storm | REAL RAD DATA + ROS 2 RUN (simulated walker) | `data/env/rad_4190.csv` (MSL RAD, sol 4190, detector E); red line before/after alarm from the same C1 run; inset = Unreal HUD replay of a C1 recording, `outputs/raw-takes/10_firtina_kayit_oynatimi.mp4` 53.8-60.8 s (alarm at 56.2 s aligned to the map alarm) |
| 25.5-27.5 s | Hand-held XRF | SIMULATED INSTRUMENT + AI-GENERATED 3D MODELS | `outputs/feature-videos/04_xrf.mp4` |
| 27.5-30 s | End card | REAL NASA IMAGE (dimmed) | Gale crater sunset, NASA/JPL-Caltech/MSSS/Texas A&M Univ., PIA19400 |

Numbers on screen are the claim-ledger values (`docs/verification/SPACE_APPS_CLAIMS.json`): `rad_spike` (x61, alarm 05:21:50, peak 06:15:19), `light_time` (32 min round trip), `storm_shrinks_line_ros` (6.02 -> 0.41 km2), `storm_chapter_realtime_ros` (shelter mode in 0 s).

AI-generated content (labelled on screen): some 3D models (Tripo) and the music (Suno, `redline_sessiz_yorunge_take_02.mp3`). NASA images and science data are not AI-generated. No NASA logo is used.

The Unreal storm view is a replay of a recorded ROS run, not a new live run (claim `unreal_live_storm` stays open).
