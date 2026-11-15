"""Scenario parameters come from config/crew.yaml and config/suit.yaml (proje.md §7.2)."""
from pathlib import Path

import pytest

from redline_core.params import load_crew, load_models

REPO = Path(__file__).resolve().parents[3]


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_crew_members_load_with_scenario_provenance(tmp_path):
    path = write(
        tmp_path,
        "crew.yaml",
        "provenance_status: SCENARIO\n"
        "crew:\n"
        "  EV1: {body_mass_kg: 75, load_mass_kg: 80}\n"
        "  EV2: {body_mass_kg: 68, load_mass_kg: 80, theta: 1.1}\n",
    )
    crew = load_crew(path)
    assert crew["EV1"].crew_id == "EV1"
    assert crew["EV1"].body_mass_kg == 75.0
    assert crew["EV1"].theta == 1.0
    assert crew["EV2"].theta == 1.1


def test_models_override_only_named_parameters(tmp_path):
    path = write(
        tmp_path,
        "suit.yaml",
        "provenance_status: SCENARIO\nwalk: {slope_max_deg: 20}\nsuit: {battery_base_w: 75}\n",
    )
    walk, suit = load_models(path)
    assert walk.slope_max_deg == 20.0
    assert walk.slope_z == 1.645
    assert suit.battery_base_w == 75.0
    assert suit.battery_k == 0.05


def test_misspelled_parameter_is_rejected(tmp_path):
    path = write(tmp_path, "suit.yaml", "provenance_status: SCENARIO\nwalk: {slope_max: 20}\n")
    with pytest.raises(ValueError, match="slope_max"):
        load_models(path)


@pytest.mark.parametrize("status", ["", "provenance_status: GUESS\n"])
def test_parameter_files_must_declare_provenance(tmp_path, status):
    path = write(tmp_path, "crew.yaml", status + "crew:\n  EV1: {body_mass_kg: 75, load_mass_kg: 80}\n")
    with pytest.raises(ValueError, match="provenance"):
        load_crew(path)


def test_repository_scenario_files_load():
    crew = load_crew(REPO / "config" / "crew.yaml")
    assert set(crew) == {"EV1", "EV2"}
    walk, suit = load_models(REPO / "config" / "suit.yaml")
    assert walk.rock_detour_s is None or walk.rock_detour_s > 0
    assert suit.latent_heat_j_kg > 0
