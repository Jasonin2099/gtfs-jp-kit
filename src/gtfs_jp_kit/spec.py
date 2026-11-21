"""Machine-readable parts of the GTFS-JP v4 specification.

Source: 国土交通省「公共交通運行情報標準データ仕様（GTFS-JP）」第 4.0 版
(2026-03), §8.2 ファイルリスト and （参考 3）"GTFS Schedule 日本標準仕様書と
GTFS 国際標準仕様のファイル、フィールドの必須等区分の差分". Only the places
where GTFS-JP differs from (is stricter than) the international GTFS
reference are listed here; plain GTFS validity is left to the MobilityData
validator.
"""

from __future__ import annotations

from dataclasses import dataclass

SPEC_NAME = "GTFS-JP v4.0 (MLIT, 2026-03)"

#: Files that are 必須 in GTFS-JP v4 (§8.2).
REQUIRED_FILES = (
    "feed_info.txt",
    "agency.txt",
    "stops.txt",
    "routes.txt",
    "trips.txt",
    "stop_times.txt",
    "fare_attributes.txt",
    "translations.txt",
)

#: At least one of these must exist (calendar.txt / calendar_dates.txt, 条件付必須).
CALENDAR_FILES = ("calendar.txt", "calendar_dates.txt")

#: Files that are 推奨 in GTFS-JP v4.
RECOMMENDED_FILES = ("attributions.txt", "transfers.txt")

#: Fields that GTFS-JP makes 必須 although GTFS leaves them optional/conditional.
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "feed_info.txt": ("feed_lang", "feed_start_date", "feed_end_date", "feed_version"),
    "agency.txt": ("agency_id", "agency_lang"),
    "stops.txt": ("stop_name", "stop_lat", "stop_lon", "location_type"),
    "routes.txt": ("agency_id",),
}

#: Fields that GTFS-JP marks 推奨.
RECOMMENDED_FIELDS: dict[str, tuple[str, ...]] = {
    "feed_info.txt": ("feed_contact_email", "feed_contact_url"),
    "agency.txt": ("agency_phone", "agency_fare_url", "agency_email"),
    "stops.txt": ("platform_code",),
    "routes.txt": ("route_color", "route_text_color"),
    "trips.txt": ("trip_headsign", "direction_id"),
    "stop_times.txt": ("stop_headsign", "timepoint"),
}

#: Fields that GTFS-JP marks 不要 (not needed for domestic feeds).
UNNEEDED_FIELDS: dict[str, tuple[str, ...]] = {
    "feed_info.txt": ("default_lang",),
    "stops.txt": ("tts_stop_name", "stop_timezone"),
}

#: GTFS-JP v3 extension files that v4 moved to （参考 1）.
V3_EXTENSION_FILES = ("agency_jp.txt", "office_jp.txt", "pattern_jp.txt")

#: GTFS-JP first-edition file replaced by translations.txt / jp_parent_route_id.
V1_LEGACY_FILES = ("routes_jp.txt",)


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Profile:
    """Which file and field table the structure checks apply."""

    key: str
    name: str
    required_files: tuple[str, ...]
    recommended_files: tuple[str, ...]
    required_fields: dict[str, tuple[str, ...]]
    recommended_fields: dict[str, tuple[str, ...]]
    unneeded_fields: dict[str, tuple[str, ...]]
    #: v4 makes shapes.txt 条件付必須 (and recommends it otherwise); v3 leaves it 任意.
    shapes_rules: bool
    #: agency_jp / office_jp / pattern_jp are part of v3 but only 参考 in v4.
    v3_extensions_are_legacy: bool
    #: English translations are 推奨 in v4; v3 has no 推奨 category.
    english_recommended: bool


V4 = Profile(
    key="v4",
    name=SPEC_NAME,
    required_files=REQUIRED_FILES,
    recommended_files=RECOMMENDED_FILES,
    required_fields=REQUIRED_FIELDS,
    recommended_fields=RECOMMENDED_FIELDS,
    unneeded_fields=UNNEEDED_FIELDS,
    shapes_rules=True,
    v3_extensions_are_legacy=True,
    english_recommended=True,
)

#: GTFS-JP v3 (標準的なバス情報フォーマット 第 3 版). Source: 国土交通省
#: 「公共交通運行情報標準データ仕様（GTFS-JP）と標準的なバス情報フォーマット
#: 第３版（GTFS-JP v3）等との差分について」(2026-03), §3.1 and §3.2 (the "JP v3
#: 区分" columns). v3 has no 推奨 category. Values marked 固定 there
#: (feed_lang, agency_timezone, agency_lang, route_type, currency_type) are
#: required with a fixed value; the value rules check those for both profiles.
#: translations.txt with ja-Hrkt readings is 必須 in v3 as well (v3 §2-14-1).
V3 = Profile(
    key="v3",
    name="GTFS-JP v3 (標準的なバス情報フォーマット 第3版)",
    required_files=REQUIRED_FILES,
    recommended_files=(),
    required_fields={
        "feed_info.txt": ("feed_lang",),
        "agency.txt": ("agency_id", "agency_lang"),
        "stops.txt": ("stop_name", "stop_lat", "stop_lon"),
        "routes.txt": ("agency_id",),
    },
    recommended_fields={},
    unneeded_fields={
        "stops.txt": ("stop_timezone", "wheelchair_boarding"),
        "fare_rules.txt": ("contains_id",),
    },
    shapes_rules=False,
    v3_extensions_are_legacy=False,
    english_recommended=False,
)

PROFILES: dict[str, Profile] = {p.key: p for p in (V4, V3)}
DEFAULT_PROFILE = "v4"


def get_profile(profile: str | Profile | None) -> Profile:
    if isinstance(profile, Profile):
        return profile
    key = profile or DEFAULT_PROFILE
    try:
        return PROFILES[key]
    except KeyError:
        raise ValueError(f"unknown profile {key!r} (use {', '.join(PROFILES)})") from None
