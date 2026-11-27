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
    feed = make_feed(feed_info=INFO_HEAD + "X,https://example.jp,en,20270101,20260101,20270101_1\n")
    assert codes(values.feed_info(feed)) == ["feed-lang-not-ja", "feed-period-reversed"]
    later = make_feed(
        feed_info=INFO_HEAD + "X,https://example.jp,ja,20280101,20281231,20280101_1\n"
    )
    assert codes(values.feed_info(later)) == ["service-outside-feed-period"] * 3


def test_feed_version_date_hint(make_feed):
    def found(version):
        feed = make_feed(
            feed_info=INFO_HEAD + f"X,https://example.jp,ja,20261001,20270331,{version}\n"
        )
        return [f for f in values.feed_info(feed) if f.code == "feed-version-no-date"]

    # the spec's own examples (feed_info.txt and §(5)) all carry the revision date
    for ok in (
        "20250401_0003",
        "20250401_0003_20250408修正",
        "2025/03/30 改正-見える化 ver2.6g",
        "2025年4月1日改正ダイヤ_2025年4月8日修正",
        "2026.10.01_v1",
        "令和7年4月1日改正",
        "２０２５０４０１",
    ):
        assert found(ok) == [], ok
    [f] = found("ver2")
    assert f.severity == "info" and f.field == "feed_version" and "20250401_0003" in f.message
    assert found("2025年度版") and found("20251301")
    # an empty feed_version is the required-field check's job, not this hint's
    assert found("") == []


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


def test_fare_values(make_feed):
    fares = (
        "fare_id,price,currency_type,payment_method,transfers,transfer_duration,ic_price\n"
        "OK1,200,JPY,0,0,,195\n"
        "OK2,200,JPY,1,,3600,-1\n"  # empty transfers = unlimited
        "OK3,200,JPY,1,2,0,\n"
        "P2,200,JPY,2,0,,\n"  # payment_method 2
        "PFW,200,JPY,１,0,,\n"  # full-width 1
        "PEM,200,JPY,,0,,\n"  # payment_method is 必須
        "T3,200,JPY,0,3,,\n"
        "TD,200,JPY,0,1,1.5h,\n"
        "IC,200,JPY,0,0,,195.5\n"
        "PR,２００,JPY,0,0,,\n"  # full-width price
    )
    found = [
        (f.line, f.field)
        for f in values.fares(make_feed(fare_attributes=fares))
        if f.code in ("bad-fare-value", "fare-price-yen")
    ]
    assert found == [
        (5, "payment_method"),
        (6, "payment_method"),
        (7, "payment_method"),
        (8, "transfers"),
        (9, "transfer_duration"),
        (10, "ic_price"),
        (11, "price"),
    ]
    assert "半角の 1" in values.fare_value_problem("payment_method", "１")[1]
    # columns that are not there are not reported (structure checks cover missing columns)
    bare = make_feed(fare_attributes="fare_id,price,currency_type\nA,200,JPY\n")
    assert "bad-fare-value" not in codes(values.fares(bare))


def test_platform_code_and_stop_name(make_feed):
    head = "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station,platform_code\n"
    rows = [
        "A,東西駅前,36.1,138.2,0,P,1",
        "B,東西駅前,36.1,138.2,0,P,センタービル前",  # allowed by the spec [JP]
        "C,東西駅前,36.1,138.2,0,P,1番のりば",
        "D,東西駅前,36.1,138.2,0,P,3番線",
        "E,東西駅前,36.1,138.2,0,P,のりばA",
        "F,東西駅前,36.1,138.2,0,P,２",  # full-width
        "G,東西駅前 1番のりば,36.1,138.2,0,P,",
        "H,東西駅前（2番）,36.1,138.2,0,P,",
        "I,博多駅(JR),36.1,138.2,0,P,",  # sub-name, fine
        "J,バスのりば,36.1,138.2,0,P,",  # no number, fine
        "K,東西駅 3番線,36.1,138.2,,P,",
        "P,東西駅 のりばB,36.1,138.2,1,,",  # station: name not checked
    ]
    found = [(f.line, f.code) for f in values.stops(make_feed(stops=head + "\n".join(rows) + "\n"))]
    assert found == [
        (4, "platform-code-words"),
        (5, "platform-code-words"),
        (6, "platform-code-words"),
        (7, "platform-code-full-width"),
        (8, "stop-name-platform"),
        (9, "stop-name-platform"),
        (12, "stop-name-platform"),
    ]
    msgs = {f.line: f for f in values.stops(make_feed(stops=head + "\n".join(rows) + "\n"))}
    assert '("1")' in msgs[4].message and "「3」" in msgs[5].message_ja
    assert values.platform_code_fix("Platform 2") == "2"


def test_fixture_stops_clean(tozai):
    assert list(values.stops(tozai)) == []


def test_phone_hyphens_and_attributions(make_feed):
    head = "agency_id,agency_name,agency_url,agency_timezone,agency_lang,agency_phone\n"
    agency = head + "tozai,B,https://example.jp,Asia/Tokyo,ja,0352538111\n"
    found = [f for f in values.agency(make_feed(agency=agency)) if "phone" in f.code]
    assert [(f.code, f.severity, f.spec) for f in found] == [("phone-no-hyphen", "info", "§4.13")]

    attributions = (
        "attribution_id,organization_name,is_producer,attribution_phone\n"
        "A1,X,1,03-5253-8111\n"
        "A2,Y,1,０３－５２５３－８１１１\n"
        "A3,Z,1,0352538111\n"
        "A4,W,1,\n"
    )
    found = values.attributions(make_feed(attributions=attributions))
    assert [(f.line, f.code, f.field) for f in found] == [
        (3, "bad-phone", "attribution_phone"),
        (4, "phone-no-hyphen", "attribution_phone"),
    ]
