# REDLINE v3 — fresh application repository

Start with root `proje.md`: this is the user's final implementation specification after the idea phase. Read sections 0–4 and 18, then the relevant implementation section. Supporting design history lives in `research/proje-fikirleri/`; the v3 guide is there. The handoff lives in `research/handoff/`. These v3 files supersede historical v2 notes. Follow the user's latest explicit changes.

Project skills are in .agents/skills; read the matching SKILL.md and only the references needed for the task. `research/proje-fikirleri/SKILL_PLANI.md` records sources. optional-user-skills is a reference copy, not a runtime/tool connection.

Write the REDLINE application from scratch. Do not copy the previous ROS/web/rover implementation. Prior skill helpers, research, metadata and the integrity tool must retain their source/licence/prior-work notices.

Follow milestone dependencies and the vertical integration path in spec section 18; mark milestones done only with observed acceptance evidence. Update docs/PROGRESS.md and docs/VERIFICATION_LOG.md as appropriate. Keep core algorithms in python/redline_core; ROS/UI call them. Apply required core and node tests from the spec.

Read each planetary CRS from product metadata; numeric bbox overlap is not alignment. Preserve ARCHIVE/DERIVED/SIMULATED/SCENARIO status and provenance. Sample origin and analysis location are distinct. Resolve the APXS coordinate-semantics discrepancy recorded in `research/handoff/YENI_DEPO_AKTARIMI.md` against product/localization evidence before generalizing.

The user excludes the old `önceki deneme` folder from this repository. Do not restore it or copy its implementation. Old references to that folder are historical context only. Earlier Git commits remain historical records, not current project inputs.

Visual design, UI styling, levels, materials and 3D assets will be developed together with the user. Until then implement and test backend/contracts/build infrastructure; do not generate or spend credits on models, redesign screens, or create scene content.

Keep one robot physics/control authority in ROS/Gazebo and explicit Unreal presentation/command boundaries. Physics /clock and mission/PET time are distinct. Verify frame/unit/quaternion conversion and action/command/result behavior with the spec’s acceptance checks.

No secrets in the repository. Account sessions, installed runtimes, tool availability and the old Blueprint template are not provided by this handoff. Re-inventory the real new environment and regenerate .agents/ue-project-context.md after the new C++ project exists.
