import json

from conftest import FIXTURE

from gtfs_jp_kit.cli import main


def test_check_text(capsys):
    assert main(["check", str(FIXTURE)]) == 0
    out = capsys.readouterr().out
    assert "0 errors" in out


def test_check_json_ja(capsys):
    assert main(["check", str(FIXTURE), "--format", "json", "--min-severity", "warning"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["error"] == 0
    assert all(f["severity"] != "info" for f in data["findings"])


def test_check_fails_on_error(tmp_path, capsys):
    (tmp_path / "agency.txt").write_text("agency_id,agency_name\nA,バス\n", encoding="utf-8")
    assert main(["check", str(tmp_path), "--lang", "ja"]) == 1
    assert "必須" in capsys.readouterr().out
