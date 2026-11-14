from gtfs_jp_kit.checks import run_checks, structure


def codes(findings, severity=None):
    return sorted({f.code for f in findings if severity in (None, f.severity)})


def test_fixture_has_no_errors(tozai):
    found = run_checks(tozai)
    assert [f for f in found if f.severity == "error"] == []


def test_missing_required_files(make_feed):
    feed = make_feed(translations=None, fare_attributes=None)
    found = list(structure.required_files(feed))
    assert {f.file for f in found if f.code == "missing-required-file"} == {
        "translations.txt",
        "fare_attributes.txt",
    }


def test_calendar_needs_one_of_two(make_feed):
    assert "missing-calendar" not in codes(structure.required_files(make_feed(calendar=None)))
    feed = make_feed(calendar=None, calendar_dates=None)
    assert "missing-calendar" in codes(structure.required_files(feed), "error")


def test_fare_rules_required_for_multiple_fares(make_feed):
    fares = "fare_id,price,currency_type,payment_method,transfers\nA,200,JPY,0,0\nB,300,JPY,0,0\n"
    feed = make_feed(fare_attributes=fares, fare_rules=None)
    assert "missing-fare-rules" in codes(structure.conditional_files(feed), "error")
    flat = "fare_id,price,currency_type,payment_method,transfers\nA,200,JPY,0,0\n"
    assert "missing-fare-rules" not in codes(
        structure.conditional_files(make_feed(fare_attributes=flat, fare_rules=None))
    )


def test_shapes_required_with_continuous_stops(make_feed):
    routes = (
        "route_id,agency_id,route_short_name,route_long_name,route_type,continuous_pickup\n"
        "R1,A,1,線,3,0\n"
    )
    assert "missing-shapes" in codes(structure.conditional_files(make_feed(routes=routes)), "error")


def test_required_field_rows(make_feed):
    stops = "stop_id,stop_name,stop_lat,stop_lon\nS1,駅前,36.1,138.2\nS2,,36.1,138.2\n"
    found = list(structure.required_fields(make_feed(stops=stops)))
    missing_col = [f for f in found if f.code == "missing-required-field"]
    assert [f.field for f in missing_col] == ["location_type"]
    empty = [f for f in found if f.code == "empty-required-field"]
    assert [(f.field, f.line) for f in empty] == [("stop_name", 3)]


def test_unneeded_default_lang(make_feed):
    info = (
        "feed_publisher_name,feed_publisher_url,feed_lang,default_lang,feed_start_date,"
        "feed_end_date,feed_version\nX,https://example.jp,ja,ja,20260101,20261231,1\n"
    )
    assert codes(structure.unneeded_fields(make_feed(feed_info=info))) == ["unneeded-field"]
