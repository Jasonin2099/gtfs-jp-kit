"""Machine-readable parts of the GTFS-JP v4 specification.

Source: 国土交通省「公共交通運行情報標準データ仕様（GTFS-JP）」第 4.0 版
(2026-03), §8.2 ファイルリスト and （参考 3）"GTFS Schedule 日本標準仕様書と
GTFS 国際標準仕様のファイル、フィールドの必須等区分の差分". Only the places
where GTFS-JP differs from (is stricter than) the international GTFS
reference are listed here; plain GTFS validity is left to the MobilityData
validator.
"""

from __future__ import annotations

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
