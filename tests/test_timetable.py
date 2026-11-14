from datetime import date

from gtfs_jp_kit import render
from gtfs_jp_kit.timetable import departures, resolve_stops, stop_timetable


def test_resolve_station_and_name(tozai):
    assert resolve_stops(tozai, "ST_EKI") == ["ST_EKI", "ST_EKI_1", "ST_EKI_2"]
    assert resolve_stops(tozai, "東西駅前") == ["ST_EKI", "ST_EKI_1", "ST_EKI_2"]
    assert resolve_stops(tozai, "ST_SHI") == ["ST_SHI"]
    assert resolve_stops(tozai, "nowhere") == []


def test_last_stop_is_not_a_departure(tozai):
    # 市民病院 is the terminus of direction 0 and the origin of direction 1.
    deps = departures(tozai, ["ST_BYO"], {"WD"})
    assert {d.headsign for d in deps} == {"東西駅前"}
    assert len(deps) == 7


def test_day_type_columns(tozai):
    tt = stop_timetable(tozai, "東西駅前", lang="ja")
    assert tt.columns == ["平日", "土曜", "日曜・祝日"]
    assert tt.cell("平日", 8) == ["み05", "病20"]
    assert tt.cell("日曜・祝日", 15) == ["20"]
    assert tt.hours[0] == 6 and tt.hours[-1] == 24  # 24:30 stays on the service day
    assert "み：2 みどり団地行き" in tt.legend("ja")
    assert "病: 市民病院 正面玄関まで乗り入れ" in tt.legend("ja")


def test_single_date_uses_exceptions(tozai):
    holiday = stop_timetable(tozai, "ST_SHI", on=date(2026, 11, 23))
    assert holiday.columns == ["2026-11-23"]
    assert [d.hhmm for d in holiday.departures["2026-11-23"]] == ["09:26", "15:26"]


def test_route_filter(tozai):
    tt = stop_timetable(tozai, "東西駅前", routes={"R2"}, day_types=("weekday",))
    assert [d.hhmm for d in tt.departures["Weekdays"]] == ["07:05", "08:05", "17:05"]
    assert tt.marks == {("2", "みどり団地"): ""}


def test_renderers(tozai):
    tt = stop_timetable(tozai, "東西駅前", lang="ja")
    md = render.stop_markdown(tt, "ja")
    assert md.splitlines()[2] == "| 時 | 平日 | 土曜 | 日曜・祝日 |"
    assert "| 8 | み05 病20 |  |  |" in md
    csv_out = render.stop_csv(tt).splitlines()
    assert csv_out[0].startswith("column,time,route")
    assert len(csv_out) == 1 + sum(len(v) for v in tt.departures.values())
    assert "[平日]" in render.stop_text(tt, "ja")
