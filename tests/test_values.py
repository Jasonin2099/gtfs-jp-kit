from gtfs_jp_kit import corpnum
from gtfs_jp_kit.checks import values

INFO_HEAD = (
    "feed_publisher_name,feed_publisher_url,feed_lang,feed_start_date,feed_end_date,feed_version\n"
)


def codes(findings):
    return sorted(f.code for f in findings)


def test_corporate_numbers():
    assert corpnum.is_valid("5000020999990")
    assert not corpnum.is_valid("3000123456789")
    assert corpnum.parse_agency_id("5000020999990_2") == ("5000020999990", "2")


def test_feed_lang_and_period(make_feed):
    feed = make_feed(feed_info=INFO_HEAD + "X,https://example.jp,en,20270101,20260101,1\n")
    assert codes(values.feed_info(feed)) == ["feed-lang-not-ja", "feed-period-reversed"]
    later = make_feed(feed_info=INFO_HEAD + "X,https://example.jp,ja,20280101,20281231,1\n")
    assert codes(values.feed_info(later)) == ["service-outside-feed-period"] * 3


def test_bad_date(make_feed):
    feed = make_feed(feed_info=INFO_HEAD + "X,https://example.jp,ja,2026-01-01,20261231,1\n")
    assert "bad-date" in codes(values.feed_info(feed))


def test_agency_rules(make_feed):
    agency = (
        "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
        "3000123456789,A,https://example.jp,Asia/Seoul,ko\n"
        "tozai,B,https://example.jp,Asia/Tokyo,ja\n"
    )
    assert codes(values.agency(make_feed(agency=agency))) == [
        "agency-id-check-digit",
        "agency-id-not-corporate-number",
        "agency-lang",
        "agency-timezone",
    ]


def test_route_colors(make_feed):
    routes = (
        "route_id,agency_id,route_short_name,route_long_name,route_type,route_color,route_text_color\n"
        "R1,A,1,線,3,1E6FB8,\n"
        "R2,A,2,線,3,#FF0000,FFFFFF\n"
        "R3,A,3,線,3,FFFF00,FFFFFF\n"
    )
    assert codes(values.routes(make_feed(routes=routes))) == [
        "bad-color",
        "route-color-contrast",
        "route-text-color-missing",
    ]


def test_fares(make_feed):
    fares = "fare_id,price,currency_type,payment_method,transfers\nA,210.5,JPY,0,0\nB,2,USD,0,0\n"
    rules = "fare_id,origin_id,destination_id\nA,Z9,Z8\n"
    stops = "stop_id,stop_name,stop_lat,stop_lon,location_type\nS,駅,36,138,0\n"
    feed = make_feed(fare_attributes=fares, fare_rules=rules, stops=stops)
    assert codes(values.fares(feed)) == ["fare-currency", "fare-price-yen", "zone-id-missing"]
