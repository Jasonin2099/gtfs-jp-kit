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


def test_info(capsys):
    assert main(["info", str(FIXTURE), "--lang", "ja"]) == 0
    out = capsys.readouterr().out
    assert "東西市" in out and "2026-10-01 - 2027-03-31" in out
    assert main(["info", str(FIXTURE), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["services"] == ["SA", "SU", "WD"]
    assert data["translation_languages"] == ["en", "ja-Hrkt"]


def test_timetable_stop(capsys):
    assert main(["timetable", "stop", str(FIXTURE), "東西駅前", "--format", "md"]) == 0
    assert "| Hour | Weekdays |" in capsys.readouterr().out
    assert main(["timetable", "stop", str(FIXTURE), "nowhere"]) == 2
    assert main(["timetable", "stop", str(FIXTURE), "ST_SHI", "--days", "holiday"]) == 2
