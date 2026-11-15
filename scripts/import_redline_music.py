"""Import the two selected Beatra MP3 takes into the REDLINE Unreal project."""

from pathlib import Path

import unreal


PROJECT_DIR = Path(unreal.Paths.project_dir()).resolve()
REPO_ROOT = PROJECT_DIR.parents[1]
SOURCE_DIR = REPO_ROOT / "assets" / "audio" / "incoming" / "redline_sessiz_yorunge"
DESTINATION = "/Game/Audio/Music"
TRACKS = (
    (SOURCE_DIR / "redline_sessiz_yorunge_take_01.mp3", "SW_REDLINE_SessizYorunge_Exploration"),
    (SOURCE_DIR / "redline_sessiz_yorunge_take_02.mp3", "SW_REDLINE_SessizYorunge_Crisis"),
)


def import_track(filename: Path, asset_name: str) -> str:
    if not filename.is_file():
        raise RuntimeError(f"Missing source audio: {filename}")

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(filename))
    task.set_editor_property("destination_path", DESTINATION)
    task.set_editor_property("destination_name", asset_name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("replace_existing_settings", False)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    imported = list(task.get_editor_property("imported_object_paths"))
    if len(imported) != 1:
        raise RuntimeError(f"Expected one imported object for {filename}, got {imported}")
    sound = unreal.EditorAssetLibrary.load_asset(imported[0])
    if not isinstance(sound, unreal.SoundWave):
        raise RuntimeError(f"Imported object is not a SoundWave: {imported[0]}")
    sound.set_editor_property("looping", False)
    if not unreal.EditorAssetLibrary.save_loaded_asset(sound, only_if_is_dirty=False):
        raise RuntimeError(f"Could not save {imported[0]}")
    unreal.log(f"REDLINE_AUDIO_IMPORTED path={imported[0]} duration={sound.get_editor_property('duration')}")
    return imported[0]


def main() -> None:
    imported = [import_track(filename, asset_name) for filename, asset_name in TRACKS]
    unreal.log(f"REDLINE_AUDIO_IMPORT_COMPLETE count={len(imported)} assets={imported}")


main()
