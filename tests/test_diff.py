from conftest import FIXTURE

from gtfs_jp_kit.cli import main
from gtfs_jp_kit.diff import feed_diff, render_stop_diff, stop_diff
from gtfs_jp_kit.feed import load_feed


def revised(make_feed):
    """The fixture after a fictional timetable revision."""
    base = load_feed(FIXTURE)
    times = base.raw("stop_times.txt").decode()
    # Shift the 07:10 trip to 07:15, drop the 21:50 one, rename a stop.
    times = times.replace("R1_0_WD_0710,07:10:00,07:10:00", "R1_0_WD_0710,07:15:00,07:15:00")
    times = "\n".join(line for line in times.splitlines() if not line.startswith("R1_0_WD_2150"))
    stops = base.raw("stops.txt").decode().replace("市役所前", "市役所・図書館前")
    info = base.raw("feed_info.txt").decode().replace("2026.10.01_v1", "2027.04.01_v1")
    return make_feed(stop_times=times + "\n", stops=stops, feed_info=info)


def test_stop_diff(make_feed, tozai):
    new = revised(make_feed)
    weekday, saturday, _ = stop_diff(tozai, new, "ST_EKI")
    assert [(a[0], b[0]) for a, b in weekday.shifted] == [(7 * 3600 + 600, 7 * 3600 + 900)]
    assert [k[0] for k in weekday.removed] == [21 * 3600 + 3000]
    assert weekday.added == []
    assert (weekday.before, weekday.after) == (13, 12)
    assert not saturday.changed
    text = render_stop_diff("東西駅前", [weekday, saturday], "ja")
    assert "07:10 → 07:15" in text and "廃止 21:50" in text and "変更なし" in text


def test_feed_diff(make_feed, tozai):
    d = feed_diff(tozai, revised(make_feed))
    assert d.version == ("2026.10.01_v1", "2027.04.01_v1")
    assert d.stops_renamed == [("ST_SHI", "市役所前", "市役所・図書館前")]
    assert d.stops_added == d.stops_removed == []


def test_cli_diff_same_feed(capsys):
    assert main(["diff", str(FIXTURE), str(FIXTURE), "--stop", "ST_EKI", "--lang", "ja"]) == 0
    out = capsys.readouterr().out
    assert out.count("変更なし") == 3
