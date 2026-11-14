from datetime import date

import pytest

from gtfs_jp_kit import render
from gtfs_jp_kit.route_timetable import merge_stop_orders, route_timetable


def test_merge_orders_branch_and_short_turn():
    assert merge_stop_orders([["A", "B", "C"], ["A", "B"]]) == ["A", "B", "C"]
    assert merge_stop_orders([["X", "A", "B"], ["A", "B", "C"]]) == ["X", "A", "B", "C"]


def test_route_matrix(tozai):
    rt = route_timetable(tozai, "R1", direction="0", lang="ja")
    assert rt.title == "平日"
    assert [name for _, name in rt.stops] == ["東西駅前", "市役所前", "市民病院"]
    assert len(rt.trips) == 10
    assert rt.row("ST_SHI")[:3] == ["06:46", "07:16", "07:46"]
    assert rt.trips[3]["jp_trip_desc_symbol"] == "病"


def test_route_on_holiday(tozai):
    rt = route_timetable(tozai, "R1", on=date(2026, 11, 23))
    assert len(rt.trips) == 2


def test_unknown_route(tozai):
    with pytest.raises(KeyError):
        route_timetable(tozai, "R9")


def test_route_renderers(tozai):
    rt = route_timetable(tozai, "R2")
    md = render.route_markdown(rt)
    assert "| みどり団地 | 07:14 | 08:14 | 17:14 |" in md
    assert render.route_csv(rt).splitlines()[1].startswith("ST_EKI_2,東西駅前,07:05")
    assert render.route_text(rt).splitlines()[0] == "2 (Weekdays)"
