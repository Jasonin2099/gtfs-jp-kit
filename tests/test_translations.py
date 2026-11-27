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


def test_duplicate_primary_key(make_feed):
    rows = (
        "stops,stop_name,ja-Hrkt,しやくしょまえ,,,市役所前\n"  # line 2
        "stops,stop_name,en,City Hall,,,市役所前\n"  # line 3
        "stops,stop_name,ja-Hrkt,しやくしょまえ,,,市役所前\n"  # same as 2
        "stops,stop_name,en,Shiyakusho-mae,,,市役所前\n"  # conflicts with 3
        "stops,stop_name,en,City Hall,ST_SHI,,\n"  # record_id key: a different key
        "stops,stop_name,zh-Hans,市政府前,,,市役所前\n"  # other language: fine
    )
    found = [f for f in translations.structure(make_feed(translations=HEAD + rows))]
    dups = [f for f in found if f.code == "translation-duplicate"]
    assert [(f.line, f.severity) for f in dups] == [(4, "error"), (5, "error")]
    assert "line 2" in dups[0].message and "identical" in dups[0].message
    assert "'City Hall'" in dups[1].message
    assert "異なる" in dups[1].message_ja
    # the duplicate row is reported once, not checked again
    assert codes(found) == ["translation-duplicate", "translation-duplicate"]


def test_half_width_kana_reading(make_feed):
    rows = (
        "stops,stop_name,ja-Hrkt,ｼﾔｸｼｮﾏｴ,,,市役所前\n"
        "stops,stop_name,ja-Hrkt,ｼﾐﾝ病院,,,市民病院\n"  # half-width and kanji
    )
    found = list(translations.structure(make_feed(translations=HEAD + rows)))
    hw = [f for f in found if f.code == "reading-half-width-kana"]
    assert [f.severity for f in hw] == ["info", "info"]
    assert "'しやくしょまえ'" in hw[0].message and "「しやくしょまえ」" in hw[0].message_ja
    # pure half-width katakana is still kana: no reading-not-kana on top
    assert [f.line for f in found if f.code == "reading-not-kana"] == [3]
    assert translations.half_width_reading_fix("ﾊﾞｽﾀｰﾐﾅﾙ") == "ばすたーみなる"
    # full-width katakana readings are fine (ja-Hrkt = hiragana + katakana)
    ok = HEAD + "stops,stop_name,ja-Hrkt,シヤクショマエ,,,市役所前\n"
    assert list(translations.structure(make_feed(translations=ok))) == []


STOPS = (
    "stop_id,stop_name,stop_lat,stop_lon,zone_id,location_type,parent_station,platform_code\n"
    "ST_EKI,東西駅前,36.1000,138.2500,,1,,\n"
    "ST_EKI_1,東西駅前,36.1001,138.2501,Z1,0,ST_EKI,1\n"
    "ST_EKI_2,東西駅前,36.1002,138.2502,Z1,0,ST_EKI,2\n"
    "ST_SHI,市役所前,36.1050,138.2550,Z1,0,,\n"
    "ST_SHI_N,市役所前,36.2050,138.3550,Z1,0,,\n"
    "ST_BYO,市民病院,36.1100,138.2600,Z1,0,,\n"
    "ST_DAN,みどり団地,34.3950,138.2400,Z1,0,,\n"
)


def test_reading_varies(make_feed):
    rows = (
        "stops,stop_name,ja-Hrkt,とうざいえきまえ,,,東西駅前\n"
        "stops,stop_name,ja-Hrkt,とうざいえき,ST_EKI_2,,\n"  # one platform differs
        "stops,stop_name,ja-Hrkt,しやくしょまえ,,,市役所前\n"
        "stops,stop_name,ja-Hrkt,しやくしょまい,ST_SHI_N,,\n"  # another place, other reading
    )
    feed = make_feed(stops=STOPS, translations=HEAD + rows)
    found = list(translations.stop_reading_consistency(feed))
    by_name = {f.message.split("'")[1]: f for f in found}
    assert set(by_name) == {"東西駅前", "市役所前"}
    eki, shi = by_name["東西駅前"], by_name["市役所前"]
    assert eki.severity == "warning" and "within one station" in eki.message
    assert "「とうざいえき」(ST_EKI_2)" in eki.message_ja and eki.line == 2
    assert shi.severity == "info" and "different places" in shi.message


def test_reading_varies_quiet_cases(tozai, make_feed):
    assert list(translations.stop_reading_consistency(tozai)) == []
    # same reading given by record_id and by field_value: no finding
    rows = (
        "stops,stop_name,ja-Hrkt,とうざいえきまえ,,,東西駅前\n"
        "stops,stop_name,ja-Hrkt,とうざいえきまえ,ST_EKI_1,,\n"
    )
    feed = make_feed(stops=STOPS, translations=HEAD + rows)
    assert list(translations.stop_reading_consistency(feed)) == []
    assert list(translations.stop_reading_consistency(make_feed(translations=None))) == []
