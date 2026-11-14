import subprocess
import sys


def _cli(*args):
    return subprocess.run(
        [sys.executable, "-c", "from redline_data.cli import main; raise SystemExit(main())", *args],
        capture_output=True, text=True, check=False,
    )


def test_version_entry_point():
    result = _cli("--version")
    assert result.returncode == 0
    assert result.stdout.strip() == "redline-data 0.1.0"


def test_unimplemented_fetch_is_rejected_without_artifacts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = _cli("fetch", "BXW")
    assert result.returncode == 2
    assert "unrecognized arguments" in result.stderr
    assert not list(tmp_path.iterdir())
