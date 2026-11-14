# REDLINE v3 — fresh application repository

Read YENI_DEPO_AKTARIMI.md, REDLINE_V3_UYGULAMA_SPEKI.md sections 0–4 and 18, then the relevant design section in REDLINE_V3_KILAVUZU.md. These v3 files supersede historical v2 notes. Follow the user’s latest explicit changes.

Project skills are in .agents/skills; read the matching SKILL.md and only the references needed for the task. SKILL_PLANI.md records sources. optional-user-skills is a reference copy, not a runtime/tool connection.

Write the REDLINE application from scratch. Do not copy the previous ROS/web/rover implementation. Prior skill helpers, research, metadata and the integrity tool must retain their source/licence/prior-work notices.

Follow milestone dependencies and the vertical integration path in spec section 18; mark milestones done only with observed acceptance evidence. Update docs/PROGRESS.md and docs/VERIFICATION_LOG.md as appropriate. Keep core algorithms in python/redline_core; ROS/UI call them. Apply required core and node tests from the spec.

Read each planetary CRS from product metadata; numeric bbox overlap is not alignment. Preserve ARCHIVE/DERIVED/SIMULATED/SCENARIO status and provenance. Sample origin and analysis location are distinct. Resolve the APXS coordinate-semantics discrepancy recorded in YENI_DEPO_AKTARIMI.md against product/localization evidence before generalizing.

Keep one robot physics/control authority in ROS/Gazebo and explicit Unreal presentation/command boundaries. Physics /clock and mission/PET time are distinct. Verify frame/unit/quaternion conversion and action/command/result behavior with the spec’s acceptance checks.

No secrets in the repository. Account sessions, installed runtimes, tool availability and the old Blueprint template are not provided by this handoff. Re-inventory the real new environment and regenerate .agents/ue-project-context.md after the new C++ project exists.
