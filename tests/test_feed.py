import zipfile

from gtfs_jp_kit.feed import load_feed, parse_table


def test_parse_bom_and_blank_lines():
    raw = "\ufeffstop_id,stop_name\r\nS1, 市役所前 \r\n\r\nS2,駅前\r\n".encode()
    t = parse_table("stops.txt", raw)
    assert t.columns == ["stop_id", "stop_name"]
    assert [r["stop_name"] for r in t] == ["市役所前", "駅前"]
    assert t.lines == [2, 4]


def test_short_rows_are_padded():
    t = parse_table("x.txt", b"a,b,c\n1,2\n")
    assert t.rows == [{"a": "1", "b": "2", "c": ""}]


def test_cp932_fallback():
    raw = "stop_id,stop_name\nS1,市役所前\n".encode("cp932")
    t = parse_table("stops.txt", raw)
    assert t.rows[0]["stop_name"] == "市役所前"


def test_load_zip_with_nested_folder(tmp_path):
    z = tmp_path / "feed.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("gtfs/agency.txt", "agency_id,agency_name\nA,テストバス\n")
        zf.writestr("__MACOSX/._agency.txt", "junk")
    feed = load_feed(z)
    assert feed.has("agency")
    assert feed["agency"].rows[0]["agency_name"] == "テストバス"
    assert not feed.has("stops")
    assert len(feed["stops"]) == 0
