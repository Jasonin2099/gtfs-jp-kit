from gtfs_jp_kit.checks import references


def codes(findings):
    return sorted(f.code for f in findings)


def test_fixture_clean(tozai):
    for check in (
        references.attributions,
        references.stop_coordinates,
        references.fare_rules,
        references.trip_symbols,
    ):
        assert list(check(tozai)) == []


def test_attribution_role(make_feed):
    feed = make_feed(
        attributions="organization_name,is_producer,is_operator\n東西市,1,\n運行会社,0,0\n"
    )
    assert [(f.code, f.line) for f in references.attributions(feed)] == [("attribution-role", 3)]


def test_swapped_coordinates(make_feed):
    stops = "stop_id,stop_name,stop_lat,stop_lon,location_type\nS1,駅,138.2,36.1,0\nS2,駅,0,0,0\n"
    found = list(references.stop_coordinates(make_feed(stops=stops)))
    assert len(found) == 2
    assert "swapped" in found[0].message and "swapped" not in found[1].message


def test_fare_rule_references(make_feed):
    rules = "fare_id,route_id,origin_id\nF200,R1,Z1\nNOPE,R9,Z9\n"
    found = list(references.fare_rules(make_feed(fare_rules=rules)))
    assert [f.field for f in found] == ["fare_id", "route_id", "origin_id"]


def test_symbol_without_desc(make_feed):
    trips = "route_id,service_id,trip_id,jp_trip_desc_symbol\nR1,WD,T1,◆\nR1,WD,T2,◆\n"
    assert codes(references.trip_symbols(make_feed(trips=trips))) == ["trip-symbol-without-desc"]
