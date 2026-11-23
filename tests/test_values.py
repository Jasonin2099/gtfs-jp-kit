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


def test_http_urls(make_feed):
    ok = make_feed()
    assert "bad-url" not in codes(values.urls(ok))

    bad_info = make_feed(feed_info=INFO_HEAD + "X,www.example.jp,ja,20260101,20261231,1\n")
    assert codes(values.urls(bad_info)) == ["bad-url"]

    agency = (
        "agency_id,agency_name,agency_url,agency_timezone,agency_lang,agency_fare_url\n"
        "tozai,B,example.jp,Asia/Tokyo,ja,https://example.jp/fare\n"
        "west,C,https://example.jp,Asia/Tokyo,ja,ftp://example.jp/fare\n"
    )
    assert codes(values.urls(make_feed(agency=agency))) == ["bad-url", "bad-url"]

    # full-width scheme, spaces, missing host, https is fine with a path in Japanese
    assert values.is_http_url("https://example.jp/バス")
    assert not values.is_http_url("ｈｔｔｐｓ://example.jp")
    assert not values.is_http_url("https://example.jp/path with space")
    assert not values.is_http_url("https://")
    assert not values.is_http_url("javascript:alert(1)")
    assert values.is_http_url("http://localhost:8080/gtfs")


def test_agency_phone(make_feed):
    head = "agency_id,agency_name,agency_url,agency_timezone,agency_lang,agency_phone\n"
    rows = [
        "03-2816-5700",  # spec example
        "0120-123-456",
        "090-1234-5678",
        "+81-3-2816-5700",
        "(082)123-4567",
        "",
        "０３－２８１６－５７００",  # full-width
        "03-2816-5700（平日9時～17時）",  # notes in the field
        "03-2816-570",  # 9 digits
        "2816-5700",  # no area code
    ]
    agency = head + "".join(f"tozai,B,https://example.jp,Asia/Tokyo,ja,{p}\n" for p in rows)
    found = [f for f in values.agency(make_feed(agency=agency)) if f.code == "bad-phone"]
    assert [f.line for f in found] == [8, 9, 10, 11]
    assert {f.severity for f in found} == {"warning"}
    assert "(03-2816-5700)" in found[0].message
    assert "受付時間" in found[1].message_ja
    assert values.phone_problem("0800-123-4567") is None
    assert values.phone_problem("0800-123-456") is not None
    assert values.phone_problem("+1-212-555-0100") is not None
