from gtfs_jp_kit.checks import translations

HEAD = "table_name,field_name,language,translation,record_id,record_sub_id,field_value\n"


def codes(findings):
    return sorted(f.code for f in findings)


def test_fixture_is_clean(tozai):
    assert list(translations.structure(tozai)) == []
    assert list(translations.readings(tozai)) == []


def test_structure_errors(make_feed):
    rows = (
        "stops,stop_name,ja-Hrkt,しやくしょまえ,ST_SHI,,市役所前\n"  # both keys
        "stops,stop_name,ja-Hrkt,しやくしょまえ,NOPE,,\n"  # unknown record
        "stop_times,stop_headsign,en,X,R1_0_WD_0640,,\n"  # missing sub id
        "feed_info,feed_publisher_name,en,Tozai City,,,東西市\n"  # feed_info key
        "bogus,name,en,X,,,Y\n"  # unknown table
        "stops,stop_name,ja-Hrkt,市やくしょ,,,市役所前\n"  # kanji in reading
        "stops,stop_name,en,Old Name,,,旧停留所\n"  # value never matches
    )
    found = codes(translations.structure(make_feed(translations=HEAD + rows)))
    assert found == [
        "reading-not-kana",
        "translation-feed-info-key",
        "translation-key",
        "translation-sub-id",
        "translation-unknown-record",
        "translation-unknown-table",
        "translation-unused-value",
    ]


def test_old_format(make_feed):
    feed = make_feed(translations="trans_id,lang,translation\n市役所前,ja-Hrkt,しやくしょまえ\n")
    assert codes(translations.structure(feed)) == ["translations-old-format"]


def test_missing_readings(make_feed):
    rows = "stops,stop_name,ja-Hrkt,しやくしょまえ,,,市役所前\n"
    found = list(translations.readings(make_feed(translations=HEAD + rows)))
    stop_errors = [f for f in found if f.code == "reading-missing" and f.file == "stops.txt"]
    assert {f.severity for f in stop_errors} == {"error"}
    assert len(stop_errors) == 3  # 東西駅前 (reported once), 市民病院, みどり団地
    assert any(f.code == "english-missing" for f in found)
    # route_short_name "1" is ASCII and needs no reading
    assert not any(f.field == "route_short_name" for f in found)


def test_reading_by_record_id(make_feed):
    rows = "".join(
        f"stops,stop_name,ja-Hrkt,よみ,{sid},,\n"
        for sid in ("ST_EKI", "ST_EKI_1", "ST_EKI_2", "ST_SHI", "ST_BYO", "ST_DAN")
    )
    found = translations.readings(make_feed(translations=HEAD + rows))
    assert not [f for f in found if f.file == "stops.txt" and f.code == "reading-missing"]
