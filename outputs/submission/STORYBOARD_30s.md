# ARIADNE — 30 s demo storyboard (v9)

15 November 2026 · Current edit: `ARIADNE_30s_v9.mp4`. Project name corrected to ARIADNE; V8 timing and visual style retained.
1920×1080 · 30 fps · 900 frames · 30.000 s. English captions, no speech.
Rebuild in WSL: `python3 outputs/submission/render/render_v9.py outputs/submission/ARIADNE_30s_v9.mp4`.
The renderer preserves an existing output; choose another filename for a new render.

| Time | Picture | Caption / purpose | Source status |
|---|---|---|---|
| 0–2.8 s | Lander arrival | The crew needs a safe route home. | Unreal simulation; some models Tripo AI |
| 2.8–6.8 s | HiRISE-based site map and return boundary | Time left for a safe return. Earth communication is about 32 min for a question and an answer. | NASA/USGS terrain and recorded ROS mission data; simulated walker/suit |
| 6.8–10.8 s | Large RViz view, Gazebo and Unreal views alongside | LiDAR and route planning | Actual separate robot recordings; not synchronized proof of arrival or avoidance |
| 10.8–13 s | Scout during SURVEY phase | Drone scouting, driven by ROS 2. | Actual recorded Gazebo flight, simulated observations; pre-stabilization take retained |
| 13–15.5 s | Rover and drill | Drill at the science target. | Scripted Unreal demonstration, simulated drilling |
| 15.5–19 s | Habitat laboratory and large pH/conductivity plots | Read the sample results | Scripted lab view; all 31 recorded simulated model rows, no smoothing |
| 19–26.5 s | Return boundary contracts; RAD curve rises | The storm changes the return plan. | Recorded ROS scenario and real RAD data; edited transition, simulated walker |
| 26.5–30 s | Gale sunset and ARIADNE title | Mars EVA planning and rehearsal; project URL; sources and AI credit | NASA PIA19400, dimmed |

The palette is charcoal, sand, sage and rust. Plain source notes replace blue/yellow badges. Original RViz costmap colours remain intact because they are part of the actual sensor-view recording. AI credits remain readable in a quiet footer and the final card.

Audio is an explicit edit: the existing Suno take 02, existing landing Foley at the opening and an existing ready chime placed as an alarm cue at 21.2 s. The chime is not claimed as a live recorded ROS alarm. There is no new voiceover.

Earlier storyboards: `STORYBOARD_30s_v5.md`, `STORYBOARD_30s_v8.md`. Detailed sources and limits: `CREDITS_AND_AI.md`. Machine-readable timeline, input hashes and limits: `render/v9-assets/edit-manifest.json`.
