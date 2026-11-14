"""Regenerate the synthetic ``tozai`` feed used by the tests.

Everything here is fictional: 東西市 is the example municipality used in the
GTFS-JP v4 specification, and the corporate number below is made up (it only
has a valid check digit). Run ``python tests/fixtures/make_tozai.py``.
"""

from __future__ import annotations

import csv
from pathlib import Path

OUT = Path(__file__).with_name("tozai")
AGENCY = "5000020999990"


def write(name: str, header: list[str], rows: list[list[str]]) -> None:
    OUT.mkdir(exist_ok=True)
    with (OUT / f"{name}.txt").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


STOPS = [
    # stop_id, name, kana, en, lat, lon, location_type, parent, platform
    ["ST_EKI", "東西駅前", "とうざいえきまえ", "Tozai Station", "36.1000", "138.2500", "1", "", ""],
    [
        "ST_EKI_1",
        "東西駅前",
        "とうざいえきまえ",
        "Tozai Station",
        "36.1001",
        "138.2501",
        "0",
        "ST_EKI",
        "1",
    ],
    [
        "ST_EKI_2",
        "東西駅前",
        "とうざいえきまえ",
        "Tozai Station",
        "36.1002",
        "138.2502",
        "0",
        "ST_EKI",
        "2",
    ],
    ["ST_SHI", "市役所前", "しやくしょまえ", "Shiyakusho-mae", "36.1050", "138.2550", "0", "", ""],
    ["ST_BYO", "市民病院", "しみんびょういん", "Shimin Byoin", "36.1100", "138.2600", "0", "", ""],
    ["ST_DAN", "みどり団地", "みどりだんち", "Midori Danchi", "34.3950", "138.2400", "0", "", ""],
]

ROUTES = [
    # route_id, short, long, kana_long, en_long, color, text_color
    [
        "R1",
        "1",
        "東西駅前～市民病院",
        "とうざいえきまえ～しみんびょういん",
        "Tozai Sta. - Shimin Byoin",
        "1E6FB8",
        "FFFFFF",
    ],
    [
        "R2",
        "2",
        "東西駅前～みどり団地",
        "とうざいえきまえ～みどりだんち",
        "Tozai Sta. - Midori Danchi",
        "2E8B57",
        "FFFFFF",
    ],
]

PATTERNS = {
    ("R1", "0"): (
        ["ST_EKI_1", "ST_SHI", "ST_BYO"],
        [0, 6, 12],
        "市民病院",
        "しみんびょういん",
        "Shimin Byoin",
    ),
    ("R1", "1"): (
        ["ST_BYO", "ST_SHI", "ST_EKI_1"],
        [0, 6, 12],
        "東西駅前",
        "とうざいえきまえ",
        "Tozai Station",
    ),
    ("R2", "0"): (["ST_EKI_2", "ST_DAN"], [0, 9], "みどり団地", "みどりだんち", "Midori Danchi"),
}

DEPARTURES = {
    ("R1", "0", "WD"): [
        "06:40",
        "07:10",
        "07:40",
        "08:20",
        "09:20",
        "12:20",
        "17:20",
        "18:10",
        "21:50",
        "24:30",
    ],
    ("R1", "1", "WD"): ["07:00", "07:30", "08:40", "12:40", "17:40", "18:30", "22:10"],
    ("R2", "0", "WD"): ["07:05", "08:05", "17:05"],
    ("R1", "0", "SA"): ["07:40", "09:20", "12:20", "17:20"],
    ("R1", "1", "SA"): ["08:00", "12:40", "17:40"],
    ("R1", "0", "SU"): ["09:20", "15:20"],
}

# One weekday trip runs via an extra note shown with a timetable symbol.
NOTES = {("R1", "0", "WD", "08:20"): ("市民病院 正面玄関まで乗り入れ", "病")}


def hhmm_add(t: str, minutes: int) -> str:
    h, m = map(int, t.split(":"))
    total = h * 60 + m + minutes
    return f"{total // 60:02d}:{total % 60:02d}:00"


def main() -> None:
    write(
        "feed_info",
        [
            "feed_publisher_name",
            "feed_publisher_url",
            "feed_lang",
            "feed_start_date",
            "feed_end_date",
            "feed_version",
            "feed_contact_email",
        ],
        [
            [
                "東西市",
                "https://example.jp/tozai/bus",
                "ja",
                "20261001",
                "20270331",
                "2026.10.01_v1",
                "bus@example.jp",
            ]
        ],
    )
    write(
        "agency",
        [
            "agency_id",
            "agency_name",
            "agency_url",
            "agency_timezone",
            "agency_lang",
            "agency_phone",
        ],
        [
            [
                AGENCY,
                "東西市コミュニティバス",
                "https://example.jp/tozai/bus",
                "Asia/Tokyo",
                "ja",
                "000-000-0000",
            ]
        ],
    )
    write(
        "stops",
        [
            "stop_id",
            "stop_name",
            "stop_lat",
            "stop_lon",
            "zone_id",
            "location_type",
            "parent_station",
            "platform_code",
        ],
        [[s[0], s[1], s[4], s[5], "" if s[6] == "1" else "Z1", s[6], s[7], s[8]] for s in STOPS],
    )
    write(
        "routes",
        [
            "route_id",
            "agency_id",
            "route_short_name",
            "route_long_name",
            "route_type",
            "route_color",
            "route_text_color",
        ],
        [[r[0], AGENCY, r[1], r[2], "3", r[5], r[6]] for r in ROUTES],
    )
    write(
        "calendar",
        [
            "service_id",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "start_date",
            "end_date",
        ],
        [
            ["WD", "1", "1", "1", "1", "1", "0", "0", "20261001", "20270331"],
            ["SA", "0", "0", "0", "0", "0", "1", "0", "20261001", "20270331"],
            ["SU", "0", "0", "0", "0", "0", "0", "1", "20261001", "20270331"],
        ],
    )
    # 2026-11-03 (Tue) and 2026-11-23 (Mon) are national holidays: run the Sunday timetable.
    write(
        "calendar_dates",
        ["service_id", "date", "exception_type"],
        [
            ["WD", "20261103", "2"],
            ["SU", "20261103", "1"],
            ["WD", "20261123", "2"],
            ["SU", "20261123", "1"],
        ],
    )
    trips, stop_times, tr = [], [], []
    for (route, direction, service), times in DEPARTURES.items():
        stops, offsets, headsign, kana, en = PATTERNS[(route, direction)]
        for t in times:
            trip_id = f"{route}_{direction}_{service}_{t.replace(':', '')}"
            desc, symbol = NOTES.get((route, direction, service, t), ("", ""))
            trips.append(
                [
                    route,
                    service,
                    trip_id,
                    headsign,
                    direction,
                    f"P_{route}_{direction}",
                    desc,
                    symbol,
                ]
            )
            for seq, (stop, off) in enumerate(zip(stops, offsets), start=1):
                hms = hhmm_add(t, off)
                stop_times.append([trip_id, hms, hms, stop, str(seq), "1"])
    write(
        "trips",
        [
            "route_id",
            "service_id",
            "trip_id",
            "trip_headsign",
            "direction_id",
            "jp_pattern_id",
            "jp_trip_desc",
            "jp_trip_desc_symbol",
        ],
        trips,
    )
    write(
        "stop_times",
        ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence", "timepoint"],
        stop_times,
    )
    write(
        "fare_attributes",
        ["fare_id", "price", "currency_type", "payment_method", "transfers", "agency_id"],
        [["F200", "200", "JPY", "0", "0", AGENCY]],
    )
    write("fare_rules", ["fare_id", "route_id"], [["F200", "R1"], ["F200", "R2"]])
    tr.append(["agency", "agency_name", "ja-Hrkt", "とうざいしこみゅにてぃばす", AGENCY, "", ""])
    tr.append(["agency", "agency_name", "en", "Tozai City Community Bus", AGENCY, "", ""])
    for s in STOPS:
        tr.append(["stops", "stop_name", "ja-Hrkt", s[2], "", "", s[1]])
        tr.append(["stops", "stop_name", "en", s[3], "", "", s[1]])
    for r in ROUTES:
        tr.append(["routes", "route_long_name", "ja-Hrkt", r[3], r[0], "", ""])
        tr.append(["routes", "route_long_name", "en", r[4], r[0], "", ""])
    for _, _, headsign, kana, en in PATTERNS.values():
        tr.append(["trips", "trip_headsign", "ja-Hrkt", kana, "", "", headsign])
        tr.append(["trips", "trip_headsign", "en", en, "", "", headsign])
    # field_value translations are keyed by value, so de-duplicate.
    seen, rows = set(), []
    for row in tr:
        key = tuple(row)
        if key not in seen:
            seen.add(key)
            rows.append(row)
    write(
        "translations",
        [
            "table_name",
            "field_name",
            "language",
            "translation",
            "record_id",
            "record_sub_id",
            "field_value",
        ],
        rows,
    )


if __name__ == "__main__":
    main()
