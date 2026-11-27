# Check rules / チェック項目

All rules come from 国土交通省「公共交通運行情報標準データ仕様（GTFS-JP）」第 4.0 版
(March 2026). "§8.2" is the file list, "参考1" the former v3 extensions and
"参考3" the table of differences from the international GTFS reference.
Only rules that are specific to GTFS-JP are checked; run the
[MobilityData GTFS validator](https://github.com/MobilityData/gtfs-validator)
for plain GTFS validity.

Severity: **error** = breaks a 必須 / 禁止 rule; **warning** = very likely wrong
or against a [JP] value rule; **info** = 推奨 items and notes.

## Profiles

`--profile v4` (default) uses the tables above. `--profile v3` uses the
"JP v3 区分" columns of 国土交通省「公共交通運行情報標準データ仕様（GTFS-JP）と
標準的なバス情報フォーマット第３版（GTFS-JP v3）等との差分について」(March 2026),
§3.1 (files) and §3.2 (fields):

| | v4 | v3 |
|---|---|---|
| Required files | same 8 files + calendar / calendar_dates | same |
| shapes.txt | 条件付必須 / recommended (`missing-shapes`) | 任意 (not reported) |
| attributions.txt, transfers.txt | 推奨 (`missing-recommended-file`) | not defined / 任意 |
| Extra required fields | feed_lang, feed_start_date, feed_end_date, feed_version, agency_id, agency_lang, stop_name, stop_lat, stop_lon, location_type, routes.agency_id | feed_lang, agency_id, agency_lang, stop_name, stop_lat, stop_lon, routes.agency_id |
| 推奨 fields (`recommended-field-empty`) | see `spec.RECOMMENDED_FIELDS` | none (v3 has no 推奨) |
| 不要 fields (`unneeded-field`) | default_lang, tts_stop_name, stop_timezone | stop_timezone, wheelchair_boarding, fare_rules.contains_id |
| agency_jp / office_jp / pattern_jp (`v3-extension-file`) | info: no longer needed | part of the spec, not reported (references are still checked) |
| English translations (`english-missing`) | 推奨 | 任意 (not reported) |

v3 marks feed_lang, agency_timezone, agency_lang, route_type and currency_type
as 固定 (required with a fixed value), and makes `ja-Hrkt` readings in
translations.txt 必須 (v3 §2-14-1), so the value and reading rules are the
same in both profiles.

## Files and fields (structure)

| Code | Severity | Rule |
|---|---|---|
| `missing-required-file` | error | feed_info, agency, stops, routes, trips, stop_times, fare_attributes and translations are 必須 (§8.2) |
| `missing-calendar` | error | calendar.txt or calendar_dates.txt must exist |
| `missing-recommended-file` | info | attributions.txt and transfers.txt are 推奨 |
| `missing-fare-rules` | error | fare_rules.txt is required unless there is a single flat fare |
| `missing-shapes` | error / info | shapes.txt is required with continuous pickup/drop-off (フリー乗降), otherwise recommended |
| `missing-levels` | error | levels.txt is required when pathways.txt has elevators |
| `forbidden-file` | error | networks.txt / route_networks.txt are forbidden when routes.txt uses network_id |
| `missing-required-field` | error | a column that GTFS-JP makes 必須 is missing (参考3) |
| `empty-required-field` | error | a 必須 column is empty in a row |
| `recommended-field-empty` | info | a 推奨 column is missing or empty (counts per file) |
| `unneeded-field` | info | default_lang, tts_stop_name, stop_timezone are 不要 for domestic feeds |

## Values ([JP] rules)

| Code | Severity | Rule |
|---|---|---|
| `feed-info-rows` | error | feed_info.txt has exactly one row |
| `feed-lang-not-ja` | error | feed_lang is `ja` |
| `bad-date` | error | feed_start_date / feed_end_date are YYYYMMDD |
| `feed-period-reversed` | error | feed_start_date ≤ feed_end_date |
| `feed-version-no-date` | info | feed_version contains no date; the spec recommends combining the ダイヤ改正日 (YYYYMMDD) with a management code, version etc. (例「20250401_0003」) [JP]. Not a format rule: any value with a date passes (20250401, 2025/03/30, 2025.04.01, 2025年4月1日, 令和7年4月1日) |
| `service-outside-feed-period` | warning | a calendar.txt service does not overlap the feed validity period |
| `agency-timezone` | warning | agency_timezone is `Asia/Tokyo` |
| `agency-lang` | warning | agency_lang is `ja` |
| `agency-id-not-corporate-number` | info | agency_id should be the 13-digit 法人番号 (optionally `_N`) |
| `agency-id-check-digit` | warning | a 13-digit agency_id has a wrong 法人番号 check digit |
| `bad-phone` | warning | agency_phone and attribution_phone are dialable Japanese numbers: half-width only, no notes or hours in the field, 10 digits (11 for 0X0 / 0800) or `+81` without the leading 0 |
| `phone-no-hyphen` | info | a valid phone number written as digits only; §4.13 asks for half-width digits with hyphens (`03-5253-8111`). Not auto-fixed, since the hyphen positions depend on the area code |
| `bad-url` | error | agency_url, agency_fare_url, feed_publisher_url and feed_contact_url are http(s) URLs with a host (no missing scheme, spaces or full-width ASCII) |
| `route-text-color-missing` | error | route_text_color is set whenever route_color is set |
| `bad-color` | error | colors are 6 hex digits without `#` |
| `route-color-contrast` | warning | route_color / route_text_color contrast is below 3:1 |
| `fare-currency` | warning | currency_type is `JPY` |
| `fare-price-yen` | error | JPY prices are whole numbers (half-width digits) |
| `bad-fare-value` | error | payment_method is 0 (pay after boarding, on board) or 1 (pay before boarding, at a counter or machine) — not the bus 前払い / 後払い distinction; transfers is empty (unlimited), 0, 1 or 2; transfer_duration is whole seconds; ic_price is whole yen or -1 (fare_attributes.txt, §4.14). Full-width digits get a half-width hint |
| `zone-id-missing` | error | fare_rules.txt uses zones but stops have no zone_id |
| `platform-code-words` | warning | platform_code contains 「番線」「のりば」 or similar words; set only the number, letter or sign (stops.txt [国際]). The message suggests the value without them |
| `platform-code-full-width` | info | platform_code is full-width alphanumerics. Not a spec rule: a hint, since the spec examples and route planners use half-width |
| `stop-name-platform` | warning | the stop_name of a platform (location_type 0 or empty) contains a platform number such as 「1番のりば」「のりばA」「3番線」; it belongs in platform_code (stops.txt [Google]). Parenthesised sub-names like 「博多駅(JR)」 are not flagged |

## References

| Code | Severity | Rule |
|---|---|---|
| `attribution-role` | error | each attributions.txt row has is_producer, is_operator or is_authority = 1 (条件付必須) |
| `stop-outside-japan` | warning | stop coordinates are outside Japan (and a hint when lat/lon look swapped) |
| `fare-rule-reference` | error | fare_rules.txt refers to an unknown fare_id, route_id or zone |
| `trip-symbol-without-desc` | warning | jp_trip_desc_symbol is set but jp_trip_desc does not explain it |

## translations.txt

| Code | Severity | Rule |
|---|---|---|
| `translations-old-format` | error | the first-edition `trans_id` format is used |
| `translation-duplicate` | error | two rows share the GTFS primary key (table_name, field_name, language, record_id, record_sub_id, field_value); the message says whether the translations differ |
| `translation-unknown-table` | error | table_name is not a translatable file |
| `translation-feed-info-key` | error | feed_info translations must not set record_id / record_sub_id / field_value |
| `translation-key` | error | exactly one of record_id and field_value is set |
| `translation-sub-id` | error | stop_times translations by record_id need record_sub_id |
| `translation-unknown-record` | error | record_id does not exist in the target file |
| `translation-unused-value` | warning | no row matches field_value exactly, so the translation never applies |
| `reading-not-kana` | warning | a `ja-Hrkt` reading contains kanji, digits or Latin letters |
| `reading-missing` | error / warning | a Japanese name has no `ja-Hrkt` reading (error for stop_name, warning for agency, route, headsign names) |
| `english-missing` | info | names without an English (`en`) translation, which is 推奨 |

## GTFS-JP v3 / first-edition files (参考1)

| Code | Severity | Rule |
|---|---|---|
| `v3-extension-file` | info | agency_jp.txt, office_jp.txt, pattern_jp.txt are no longer needed in v4 |
| `v1-legacy-file` | warning | routes_jp.txt is from the first edition |
| `agency-jp-unknown-agency` | error | agency_jp.agency_id is not in agency.txt |
| `agency-jp-zip` | warning | agency_zip_number is 7 digits without a hyphen |
| `office-jp-name` | error | office_jp.office_name is required |
| `trip-unknown-office` | error | trips.jp_office_id is not in office_jp.txt |
| `trip-unknown-pattern` | warning | trips.jp_pattern_id is not in pattern_jp.txt (only when that file exists) |
