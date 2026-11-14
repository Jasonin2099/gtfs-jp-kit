from gtfs_jp_kit.checks import legacy

AGENCY = "5000020999990"


def codes(findings):
    return sorted(f.code for f in findings)


def test_fixture_has_no_legacy(tozai):
    assert list(legacy.presence(tozai)) == []
    assert list(legacy.references(tozai)) == []


def test_v3_files_are_info_and_checked(make_feed):
    feed = make_feed(
        agency_jp=f"agency_id,agency_official_name,agency_zip_number\n{AGENCY},東西市,123-4567\nX,他社,\n",
        office_jp="office_id,office_name\nO1,東営業所\nO2,\n",
        pattern_jp="jp_pattern_id\nP_R1_0\n",
        routes_jp="route_id,route_update_date\nR1,20261001\n",
    )
    assert codes(legacy.presence(feed)) == ["v1-legacy-file"] + ["v3-extension-file"] * 3
    found = codes(legacy.references(feed))
    assert found == [
        "agency-jp-unknown-agency",
        "agency-jp-zip",
        "office-jp-name",
        "trip-unknown-pattern",
        "trip-unknown-pattern",
    ]


def test_office_reference(make_feed):
    trips = "route_id,service_id,trip_id,jp_office_id\nR1,WD,T1,O9\nR1,WD,T2,O9\n"
    found = list(
        legacy.references(make_feed(trips=trips, office_jp="office_id,office_name\nO1,東\n"))
    )
    assert [(f.code, f.line) for f in found] == [("trip-unknown-office", 2)]
