# Check rules / チェック項目

All rules come from 国土交通省「公共交通運行情報標準データ仕様（GTFS-JP）」第 4.0 版
(March 2026). "§8.2" is the file list, "参考1" the former v3 extensions and
"参考3" the table of differences from the international GTFS reference.
Only rules that are specific to GTFS-JP are checked; run the
[MobilityData GTFS validator](https://github.com/MobilityData/gtfs-validator)
for plain GTFS validity.

Severity: **error** = breaks a 必須 / 禁止 rule; **warning** = very likely wrong
or against a [JP] value rule; **info** = 推奨 items and notes.

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
| `service-outside-feed-period` | warning | a calendar.txt service does not overlap the feed validity period |
| `agency-timezone` | warning | agency_timezone is `Asia/Tokyo` |
| `agency-lang` | warning | agency_lang is `ja` |
| `agency-id-not-corporate-number` | info | agency_id should be the 13-digit 法人番号 (optionally `_N`) |
| `agency-id-check-digit` | warning | a 13-digit agency_id has a wrong 法人番号 check digit |
| `route-text-color-missing` | error | route_text_color is set whenever route_color is set |
| `bad-color` | error | colors are 6 hex digits without `#` |
| `route-color-contrast` | warning | route_color / route_text_color contrast is below 3:1 |
| `fare-currency` | warning | currency_type is `JPY` |
| `fare-price-yen` | error | JPY prices are whole numbers |
| `zone-id-missing` | error | fare_rules.txt uses zones but stops have no zone_id |

## translations.txt

| Code | Severity | Rule |
|---|---|---|
| `translations-old-format` | error | the first-edition `trans_id` format is used |
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
