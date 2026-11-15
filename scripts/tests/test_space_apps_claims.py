"""The claims ledger only lets a slide claim through when its evidence file says so."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("space_apps_claims", ROOT / "scripts/space_apps_claims.py")
claims = importlib.util.module_from_spec(spec)
spec.loader.exec_module(claims)


def write(tmp_path, name, content):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    return name


def claim(cid, evidence, checks, on_slide=True):
    return {"id": cid, "text_en": cid, "on_slide": on_slide, "evidence": evidence, "checks": checks}


def test_json_checks_follow_dotted_paths_and_list_indices(tmp_path):
    ev = write(tmp_path, "e.json", {"a": {"b": [{"v": 351.42}, {"v": 2}]}, "ok": True, "n": 16})
    result = claims.evaluate([claim("rad", ev, [
        {"key": "a.b.0.v", "approx": 351.4, "tol": 0.05},
        {"key": "ok", "equals": True},
        {"key": "n", "min": 16, "max": 16}])], tmp_path)
    assert result["claims"][0]["passed"] is True
    assert result["slide_ready"] is True


def test_value_outside_tolerance_fails_with_observed_value(tmp_path):
    ev = write(tmp_path, "e.json", {"area": 0.41})
    result = claims.evaluate([claim("s1", ev, [{"key": "area", "approx": 0.30, "tol": 0.01}])], tmp_path)
    item = result["claims"][0]
    assert item["passed"] is False
    assert item["checks"][0]["observed"] == 0.41
    assert result["slide_ready"] is False


def test_missing_evidence_or_key_fails_instead_of_passing(tmp_path):
    ev = write(tmp_path, "e.json", {"x": 1})
    result = claims.evaluate([claim("gone", "nope.json", [{"key": "x", "equals": 1}]),
                              claim("nokey", ev, [{"key": "y", "equals": 1}])], tmp_path)
    assert [c["passed"] for c in result["claims"]] == [False, False]
    assert "missing" in result["claims"][0]["reason"]
    assert result["claims"][1]["checks"][0]["observed"] is None


def test_goal_that_is_not_met_does_not_block_slides_but_is_reported(tmp_path):
    ev = write(tmp_path, "c.json", {"passed": False})
    result = claims.evaluate([claim("t6_unreal", ev, [{"key": "passed", "equals": True}], on_slide=False)], tmp_path)
    assert result["claims"][0]["passed"] is False
    assert result["slide_ready"] is True
    assert result["not_yet"] == ["t6_unreal"]


def test_text_and_junit_evidence(tmp_path):
    log = write(tmp_path, "log.md", "Rotada 16 engelli hücre bulundu")
    xml = write(tmp_path, "py.xml", '<testsuites><testsuite tests="700" failures="0" errors="0" skipped="0"/></testsuites>')
    bad = write(tmp_path, "bad.xml", '<testsuite tests="10" failures="1" errors="0"/>')
    result = claims.evaluate([
        claim("log", log, [{"contains": "16 engelli hücre"}]),
        claim("py", xml, [{"junit_min_tests": 700}]),
        claim("bad", bad, [{"junit_min_tests": 1}])], tmp_path)
    assert [c["passed"] for c in result["claims"]] == [True, True, False]
