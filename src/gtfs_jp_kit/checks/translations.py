"""translations.txt rules: reading (ja-Hrkt) coverage, duplicate keys and record references.

GTFS-JP v4 makes translations.txt 必須, readings (``language=ja-Hrkt``) for
names 必須 and English 推奨.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator

from .. import spec
from ..feed import Feed
from ..findings import Finding

#: table_name -> primary key column used by record_id.
RECORD_KEYS = {
    "agency": "agency_id",
    "stops": "stop_id",
    "routes": "route_id",
    "trips": "trip_id",
    "stop_times": "trip_id",
    "pathways": "pathway_id",
    "levels": "level_id",
    "attributions": "attribution_id",
}
TABLES = (*RECORD_KEYS, "feed_info")
#: GTFS primary key of translations.txt; GTFS-JP v4 uses the GTFS format as is.
PRIMARY_KEY = ("table_name", "field_name", "language", "record_id", "record_sub_id", "field_value")

#: Hiragana, katakana, prolonged sound mark, middle dot, spaces and a few
#: separators that appear in readings of stop names.
_KANA = re.compile(r"^[\u3041-\u309F\u30A0-\u30FF\u31F0-\u31FF\u3000\s・ー～〜()（）\-]+$")
#: Anything that is not plain ASCII is treated as Japanese text that needs a reading.
_NEEDS_READING = re.compile(r"[^\x00-\x7F]")

#: (table, field, severity) of names whose reading is checked.
READING_TARGETS = (
    ("stops", "stop_name", "error"),
    ("agency", "agency_name", "warning"),
    ("routes", "route_long_name", "warning"),
    ("routes", "route_short_name", "warning"),
    ("trips", "trip_headsign", "warning"),
    ("stop_times", "stop_headsign", "warning"),
)


#: Half-width katakana and their sound marks (U+FF65–U+FF9F).
_HALF_KANA = re.compile(r"[\uFF65-\uFF9F]")


def half_width_reading_fix(text: str) -> str:
    """Suggested reading for one written in half-width katakana: hiragana.

    The spec's examples (「しやくしょまえ」「はねだくうこうだいいちたーみなる」) are
    hiragana; NFKC on the half-width part first turns ｶﾞ into ガ, then
    katakana become hiragana. Other characters are left alone.

    >>> half_width_reading_fix("ｼﾔｸｼｮﾏｴ")
    'しやくしょまえ'
    >>> half_width_reading_fix("ﾄｳｻﾞｲｴｷﾏｴ～ｼﾐﾝﾋﾞｮｳｲﾝ")
    'とうざいえきまえ～しみんびょういん'
    """
    out = []
    full = re.sub(r"[\uFF65-\uFF9F]+", lambda m: unicodedata.normalize("NFKC", m.group()), text)
    for ch in full:
        o = ord(ch)
        out.append(chr(o - 0x60) if 0x30A1 <= o <= 0x30F6 else ch)
    return "".join(out)


def is_kana_reading(text: str) -> bool:
    """True if ``text`` is written in kana only, as GTFS-JP asks for readings.

    >>> is_kana_reading("しやくしょまえ")
    True
    >>> is_kana_reading("まるのうち２ちょうめ")
    False
    """
    return bool(_KANA.match(text))


class _Index:
    """Which (table, field, language) combinations are translated, by id or value."""

    def __init__(self, feed: Feed) -> None:
        self.by_id: set[tuple[str, str, str, str]] = set()
        self.by_value: set[tuple[str, str, str, str]] = set()
        for row in feed["translations"]:
            key = (row.get("table_name", ""), row.get("field_name", ""), row.get("language", ""))
            if row.get("record_id"):
                self.by_id.add((*key, row["record_id"]))
            if row.get("field_value"):
                self.by_value.add((*key, row["field_value"]))

    def has(self, table: str, field: str, lang: str, record_id: str, value: str) -> bool:
        return (table, field, lang, record_id) in self.by_id or (
            table,
            field,
            lang,
            value,
        ) in self.by_value


def structure(feed: Feed) -> Iterator[Finding]:
    table = feed.get("translations")
    if table is None:
        return
    if "table_name" not in table.columns and "trans_id" in table.columns:
        yield Finding(
            "translations-old-format",
            "error",
            "translations.txt uses the GTFS-JP v1 (trans_id) format; use the GTFS format",
            "translations.txt が GTFS-JP 初版（trans_id）形式です。GTFS 標準の形式にしてください",
            file="translations.txt",
            spec="translations.txt",
        )
        return
    keys: dict[str, set[str]] = {}
    #: primary key (table_name, field_name, language, record_id, record_sub_id,
    #: field_value) -> (first line, its translation)
    first: dict[tuple[str, ...], tuple[int, str]] = {}
    for line, row in table.with_lines():
        name = row.get("table_name", "")
        f = dict(file="translations.txt", line=line, spec="translations.txt")
        pk = tuple(row.get(c, "") for c in PRIMARY_KEY)
        text = row.get("translation", "")
        if pk in first:
            dup_line, dup_text = first[pk]
            if text == dup_text:
                en, ja = " (identical translation)", "（翻訳も同じ）"
            else:
                en = f" with a different translation ({dup_text!r})"
                ja = f"（翻訳が異なる：「{dup_text}」）"
            yield Finding(
                "translation-duplicate",
                "error",
                f"same key as line {dup_line}{en}",
                f"{dup_line} 行目と同じキーです{ja}",
                field="translation",
                **f,
            )
            continue
        first[pk] = (line, text)
        if name not in TABLES and not feed.has(name):
            yield Finding(
                "translation-unknown-table",
                "error",
                f'table_name "{name}" is not a translatable file in this feed',
                f"table_name「{name}」は翻訳できるファイルではありません",
                field="table_name",
                **f,
            )
            continue
        rid, sub, val = (
            row.get("record_id", ""),
            row.get("record_sub_id", ""),
            row.get("field_value", ""),
        )
        if name == "feed_info":
            if rid or sub or val:
                yield Finding(
                    "translation-feed-info-key",
                    "error",
                    "record_id, record_sub_id and field_value must be empty for feed_info",
                    "feed_info の翻訳では record_id・record_sub_id・field_value は禁止です",
                    **f,
                )
            continue
        if bool(rid) == bool(val):
            yield Finding(
                "translation-key",
                "error",
                "set exactly one of record_id and field_value",
                "record_id と field_value はどちらか一方だけを設定します",
                field="record_id",
                **f,
            )
            continue
        if rid and name == "stop_times" and not sub:
            yield Finding(
                "translation-sub-id",
                "error",
                "record_sub_id (stop_sequence) is required for stop_times with record_id",
                "stop_times を record_id で翻訳するときは record_sub_id（stop_sequence）が必須です",
                field="record_sub_id",
                **f,
            )
        if rid and name in RECORD_KEYS:
            if name not in keys:
                keys[name] = {r.get(RECORD_KEYS[name], "") for r in feed[name]}
            if rid not in keys[name]:
                yield Finding(
                    "translation-unknown-record",
                    "error",
                    f"record_id {rid} does not exist in {name}.txt",
                    f"record_id {rid} が {name}.txt に存在しません",
                    field="record_id",
                    **f,
                )
        if val:
            field_name = row.get("field_name", "")
            values = {r.get(field_name, "") for r in feed[name]}
            if val not in values:
                yield Finding(
                    "translation-unused-value",
                    "warning",
                    f"no {name}.{field_name} equals {val!r}; this translation never applies",
                    f"field_value「{val}」と完全一致する {name}.{field_name} がありません",
                    field="field_value",
                    **f,
                )
        if row.get("language") == "ja-Hrkt":
            text = row.get("translation", "")
            if text and _HALF_KANA.search(text):
                fix = half_width_reading_fix(text)
                yield Finding(
                    "reading-half-width-kana",
                    "info",
                    f"ja-Hrkt reading {text!r} uses half-width katakana; suggest {fix!r}",
                    f"読み仮名「{text}」に半角カナがあります。「{fix}」を推奨します（50音検索用）",
                    field="translation",
                    **f,
                )
            if text and not is_kana_reading(half_width_reading_fix(text)):
                yield Finding(
                    "reading-not-kana",
                    "warning",
                    f"ja-Hrkt reading {text!r} contains non-kana characters",
                    f"読み仮名「{text}」にかな以外の文字が含まれています（数字等もかなで書きます）",
                    field="translation",
                    **f,
                )


def readings(feed: Feed, profile: spec.Profile | str | None = None) -> Iterator[Finding]:
    english = spec.get_profile(profile).english_recommended
    if not feed.has("translations"):
        return
    idx = _Index(feed)
    for table_name, field_name, severity in READING_TARGETS:
        table = feed.get(table_name)
        if table is None or field_name not in table.columns:
            continue
        key_col = RECORD_KEYS[table_name]
        missing: dict[str, int] = {}
        missing_en = 0
        seen: set[str] = set()
        for line, row in table.with_lines():
            value = row.get(field_name, "")
            if not value or not _NEEDS_READING.search(value):
                continue
            if table_name == "stops" and row.get("location_type", "") not in ("", "0", "1"):
                continue
            rid = row.get(key_col, "")
            if not idx.has(table_name, field_name, "ja-Hrkt", rid, value):
                missing.setdefault(value, line)
            if value not in seen:
                seen.add(value)
                if not idx.has(table_name, field_name, "en", rid, value):
                    missing_en += 1
        for value, line in missing.items():
            yield Finding(
                "reading-missing",
                severity,
                f"{field_name} {value!r} has no ja-Hrkt reading in translations.txt",
                f"{field_name}「{value}」の読み仮名（ja-Hrkt）が translations.txt にありません",
                file=f"{table_name}.txt",
                line=line,
                field=field_name,
                spec="translations.txt",
            )
        if english and missing_en:
            yield Finding(
                "english-missing",
                "info",
                f"{missing_en} distinct {field_name} values have no English (en) translation",
                f"{field_name} のうち {missing_en} 件に英語（en）の翻訳がありません（推奨）",
                file=f"{table_name}.txt",
                field=field_name,
                spec="translations.txt",
            )


def _stop_readings(feed: Feed) -> tuple[dict[str, str], dict[str, str]]:
    """ja-Hrkt readings of stops.stop_name, by stop_id and by field_value."""
    by_id: dict[str, str] = {}
    by_value: dict[str, str] = {}
    for row in feed["translations"]:
        if (row.get("table_name"), row.get("field_name"), row.get("language")) != (
            "stops",
            "stop_name",
            "ja-Hrkt",
        ):
            continue
        text = row.get("translation", "")
        if not text:
            continue
        if row.get("record_id"):
            by_id.setdefault(row["record_id"], text)
        elif row.get("field_value"):
            by_value.setdefault(row["field_value"], text)
    return by_id, by_value


def stop_reading_consistency(feed: Feed) -> Iterator[Finding]:
    """The same stop_name read in more than one way.

    Readings are what Japanese journey planners use for 50音 search, so the
    platforms of one station should share one reading. Different places with
    the same written name can legitimately be read differently (同名異読), so
    that case is only a hint.
    """
    if not feed.has("translations") or not feed.has("stops"):
        return
    by_id, by_value = _stop_readings(feed)
    if not by_id:  # readings by field_value alone cannot disagree for one name
        return
    #: stop_name -> reading -> [(line, stop_id, station group)]
    names: dict[str, dict[str, list[tuple[int, str, str]]]] = {}
    for line, row in feed["stops"].with_lines():
        if row.get("location_type", "") not in ("", "0", "1"):
            continue
        name, sid = row.get("stop_name", ""), row.get("stop_id", "")
        reading = by_id.get(sid) or by_value.get(name, "")
        if not name or not reading:
            continue
        group = sid if row.get("location_type") == "1" else (row.get("parent_station") or sid)
        names.setdefault(name, {}).setdefault(reading, []).append((line, sid, group))
    for name, readings_ in names.items():
        if len(readings_) < 2:
            continue
        groups = [{g for _, _, g in rows} for rows in readings_.values()]
        same_station = any(a & b for i, a in enumerate(groups) for b in groups[i + 1 :])
        first_line = min(line for rows in readings_.values() for line, _, _ in rows)
        listed = "、".join(
            f"「{r}」({', '.join(sid for _, sid, _ in rows[:3])}{', …' if len(rows) > 3 else ''})"
            for r, rows in readings_.items()
        )
        listed_en = "; ".join(
            f"{r!r} ({', '.join(sid for _, sid, _ in rows[:3])}{', ...' if len(rows) > 3 else ''})"
            for r, rows in readings_.items()
        )
        if same_station:
            en = f"stop_name {name!r} has different readings within one station: {listed_en}"
            ja = f"同じ駅・停留所内で「{name}」の読み仮名が異なります：{listed}"
        else:
            en = (
                f"stop_name {name!r} is read differently at different stops: {listed_en} "
                "(fine if these are different places read differently)"
            )
            ja = (
                f"「{name}」の読み仮名が停留所によって異なります：{listed}"
                "（別の場所で読みが違うなら問題ありません）"
            )
        yield Finding(
            "reading-varies",
            "warning" if same_station else "info",
            en,
            ja,
            file="stops.txt",
            line=first_line,
            field="stop_name",
            spec="translations.txt",
        )
