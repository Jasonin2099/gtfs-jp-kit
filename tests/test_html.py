from html.parser import HTMLParser

from gtfs_jp_kit import html
from gtfs_jp_kit.route_timetable import route_timetable
from gtfs_jp_kit.timetable import stop_timetable


class _Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def parse(doc):
    p = _Collect()
    p.feed(doc)
    return p.tags


def test_stop_html(tozai):
    doc = html.stop_html(stop_timetable(tozai, "東西駅前", lang="ja"), "ja")
    tags = parse(doc)
    assert ("html", {"lang": "ja"}) in tags
    assert "<b>病</b>20" in doc
    assert sum(1 for t, _ in tags if t == "tr") == 1 + 19  # header + hours 6..24
    assert "<script" not in doc


def test_html_escapes(make_feed, tozai):
    stops = (
        "stop_id,stop_name,stop_lat,stop_lon,location_type\n"
        'S1,"<b>A&B</b>",36,138,0\nS2,終点,36,138,0\n'
    )
    times = (
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        "R1_0_WD_0640,06:40:00,06:40:00,S1,1\nR1_0_WD_0640,06:50:00,06:50:00,S2,2\n"
    )
    feed = make_feed(stops=stops, stop_times=times)
    doc = html.stop_html(stop_timetable(feed, "S1"))
    assert "&lt;b&gt;A&amp;B&lt;/b&gt;" in doc and "<b>A&B" not in doc


def test_route_html_colors(tozai):
    doc = html.route_html(route_timetable(tozai, "R1", direction="0"), "en", "1E6FB8", "FFFFFF")
    assert "background:#1E6FB8;color:#FFFFFF" in doc
    assert 'title="市民病院 正面玄関まで乗り入れ"' in doc
