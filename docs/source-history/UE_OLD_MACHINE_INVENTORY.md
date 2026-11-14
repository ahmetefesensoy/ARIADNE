# UE Project Context

*Last inspected: 14 November 2026 · Local engine: Unreal 5.8.4 · Historical machine inventory*

Current implementation target: `REDLINE_V3_KILAVUZU.md` and
`REDLINE_V3_UYGULAMA_SPEKI.md`. Their new C++ project has not been created by this
inventory. Re-scan the destination project before using these local observations.

## Engine and project

REDLINE is a proposed Marswalk human–robot science/planning simulation. The
repository currently contains documentation, prior demos and project skills;
the scan found no `.uproject` in this repository.

The local installed engine's `Engine/Build/Build.version` reports 5.8.4,
changelist 58902052, branch `++UE5+Release-5.8`, under
`C:\Users\USER\Desktop\UE_5.8`. This is an installation observation, not proof
that a REDLINE target has been built.

An external starting template exists at
`C:\Users\USER\Documents\Unreal Projects\MyProject\MyProject.uproject`.
It has a GUID EngineAssociation. These notes do not prove that the GUID is
registered to the inspected engine. The template is separate from the future
REDLINE project; do not treat its gameplay assets as implemented REDLINE work.

## Modules and builds

The external template declares no `Modules` array; no files were found under
its `Source` directory. No REDLINE C++ module, Build.cs, Target.cs, bridge plugin,
build target or compiler verification is established by this scan.

## Explicit template plugins

| `.uproject` entry | Declared state |
|---|---|
| ModelingToolsEditorMode | Enabled, Editor target allow-list |
| GameplayStateTree | Enabled |

Engine-default and transitive plugin activation was not enumerated. The table
does not assert that unlisted plugins are disabled. Maturity/API support should
be checked in the installed `.uplugin`/headers when relevant.

## Observed template configuration

- Editor startup and game default map:
  `/Game/TopDown/Lvl_TopDown.Lvl_TopDown`.
- Global GameMode:
  `/Game/TopDown/Blueprints/BP_TopDownGameMode.BP_TopDownGameMode_C`.
- Project display name: `Top Down BP Game Template`.
- Default input classes: `EnhancedPlayerInput` and `EnhancedInputComponent`.

REDLINE class names, C++ conventions, UI base classes, save system, networking
implementation, streaming configuration and frame-time budget are not yet
established. They should be recorded from the new project's source/configuration
as it is built, rather than filled with template guesses.

## Integration direction

The current design keeps ROS 2/Gazebo responsible for robot control/physics and
Unreal for the human environment and task UI. A WebSocket/rosbridge-based adapter
is a candidate, not an installed or validated bridge. Astronaut movement/proxy,
time/frames/units, asynchronous data handling and command/result ownership need
explicit contracts and measured checks.

Target workflow is Windows Unreal with the existing WSL ROS environment. The
actual target platforms and package/distribution arrangement remain design
choices. See `REDLINE_V3_KILAVUZU.md` for the current product snapshot and
`SKILL_PLANI.md` for specialist routing. Refresh this context when the real
REDLINE `.uproject` is added or the user changes the architecture.
