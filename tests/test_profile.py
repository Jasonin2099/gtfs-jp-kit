"""--profile v3: the GTFS-JP v3 required/optional table instead of v4."""

import json

import pytest
from conftest import FIXTURE

from gtfs_jp_kit import spec
from gtfs_jp_kit.checks import legacy, run_checks, structure, translations
from gtfs_jp_kit.cli import main


def codes(findings, severity=None):
    return sorted({f.code for f in findings if severity in (None, f.severity)})


def test_profiles_and_default():
    assert spec.get_profile(None) is spec.V4
    assert spec.get_profile("v3") is spec.V3
    assert spec.get_profile(spec.V3) is spec.V3
    with pytest.raises(ValueError):
        spec.get_profile("v5")


def test_v3_required_files_are_the_same_but_nothing_is_recommended(make_feed):
    feed = make_feed(translations=None)
    found = list(structure.required_files(feed, "v3"))
    assert codes(found) == ["missing-required-file"]
    assert "missing-recommended-file" in codes(structure.required_files(feed, "v4"))


def test_v3_shapes_are_optional(make_feed):
    routes = (
        "route_id,agency_id,route_short_name,route_long_name,route_type,continuous_pickup\n"
        "R1,5000020999990,1,東西線,3,0\n"
    )
    feed = make_feed(routes=routes)
    assert "missing-shapes" in codes(structure.conditional_files(feed, "v4"), "error")
    assert "missing-shapes" not in codes(structure.conditional_files(feed, "v3"))


def test_v3_location_type_and_feed_dates_are_optional(make_feed):
    stops = "stop_id,stop_name,stop_lat,stop_lon,zone_id\nST_EKI_1,東西駅前,36.1001,138.2501,Z1\n"
    feed_info = "feed_publisher_name,feed_publisher_url,feed_lang\n東西市,https://example.jp/,ja\n"
    feed = make_feed(stops=stops, feed_info=feed_info)
    v4 = {(f.file, f.field) for f in structure.required_fields(feed, "v4")}
    v3 = {(f.file, f.field) for f in structure.required_fields(feed, "v3")}
    assert ("stops.txt", "location_type") in v4
    assert ("feed_info.txt", "feed_version") in v4
    assert v3 == set()


def test_v3_still_requires_fixed_and_jp_fields(make_feed):
    agency = "agency_name,agency_url,agency_timezone\n東西市交通局,https://example.jp/,Asia/Tokyo\n"
    feed = make_feed(agency=agency)
    v3 = {f.field for f in structure.required_fields(feed, "v3") if f.file == "agency.txt"}
    assert v3 == {"agency_id", "agency_lang"}


def test_v3_has_no_recommended_fields(tozai):
    assert codes(structure.recommended_fields(tozai, "v4")) == ["recommended-field-empty"]
    assert list(structure.recommended_fields(tozai, "v3")) == []


def test_v3_unneeded_fields(make_feed):
    stops = (
        "stop_id,stop_name,stop_lat,stop_lon,zone_id,wheelchair_boarding\n"
        "ST_EKI_1,東西駅前,36.1001,138.2501,Z1,1\n"
    )
    feed = make_feed(stops=stops)
    assert list(structure.unneeded_fields(feed, "v4")) == []
    found = list(structure.unneeded_fields(feed, "v3"))
    assert [(f.code, f.field) for f in found] == [("unneeded-field", "wheelchair_boarding")]


def test_v3_extension_files_are_not_legacy_in_v3(make_feed):
    feed = make_feed(office_jp="office_id,office_name\nO1,東営業所\n")
    assert codes(legacy.presence(feed, "v4")) == ["v3-extension-file"]
    assert list(legacy.presence(feed, "v3")) == []
    feed = make_feed(routes_jp="route_id,route_update_date\nR1,20261001\n")
    assert codes(legacy.presence(feed, "v3")) == ["v1-legacy-file"]


def test_v3_english_is_not_recommended(make_feed):
    text = (FIXTURE / "translations.txt").read_text(encoding="utf-8")
    no_en = "".join(line for line in text.splitlines(True) if ",en," not in line)
    feed = make_feed(translations=no_en)
    assert "english-missing" in codes(translations.readings(feed, "v4"))
    assert "english-missing" not in codes(translations.readings(feed, "v3"))


def test_v3_readings_are_still_required(make_feed):
    header = "table_name,field_name,language,translation,record_id,record_sub_id,field_value\n"
    feed = make_feed(translations=header)
    assert "reading-missing" in codes(translations.readings(feed, "v3"), "error")


def test_run_checks_with_profile(tozai):
    v4 = run_checks(tozai)
    v3 = run_checks(tozai, profile="v3")
    assert [f for f in v3 if f.severity == "error"] == []
    assert "recommended-field-empty" in codes(v4)
    assert "recommended-field-empty" not in codes(v3)


def test_cli_profile(capsys):
    assert main(["check", str(FIXTURE), "--profile", "v3", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["profile"] == "v3"
    assert all(f["code"] != "recommended-field-empty" for f in data["findings"])
    assert main(["check", str(FIXTURE), "--profile", "v3", "--format", "markdown"]) == 0
    assert capsys.readouterr().out.startswith("### GTFS-JP v3 check")
