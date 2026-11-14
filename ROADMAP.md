# Roadmap

Small, self-contained items. Each one should be a single pull request with tests.

## Checks

- [ ] `--profile v3` that applies the GTFS-JP v3 required/optional table instead of v4
- [x] attributions.txt: one of is_producer / is_operator / is_authority must be 1 (条件付必須)
- [ ] agency_url / feed_publisher_url: http(s) URL format
- [ ] agency_phone: Japanese phone number format (hyphenated, half-width)
- [ ] stops.txt: platform_code values are half-width and short (のりば番号)
- [x] stops.txt: coordinates inside Japan's bounding box (catch swapped lat/lon)
- [ ] stops.txt: same stop_name with different readings across rows
- [ ] translations.txt: duplicate primary keys
- [ ] translations.txt: half-width katakana in readings (warn, suggest hiragana)
- [ ] translations.txt: English stop names that look translated instead of romanized (e.g. "Primary school")
- [ ] routes.txt: jp_parent_route_id usage notes (v3 vs v4 meaning)
- [x] trips.txt: jp_trip_desc_symbol set without jp_trip_desc
- [ ] fare_attributes.txt: payment_method / transfers enum values
- [x] fare_rules.txt: references to unknown fare_id / route_id / zone
- [ ] calendar_dates.txt: national holidays not handled when weekday service runs on them
- [ ] feed_info.txt: feed_version format `YYYY.MM.DD_vN` hint
- [ ] Fares V2 (任意): minimal referential checks for fare_products / fare_leg_rules
- [ ] Flex (任意): note that Google 乗換案内 does not accept Flex files (as of 2025-12)
- [ ] `--select` to run only some rule groups
- [ ] SARIF output for GitHub code scanning
- [x] Markdown report output for pull request comments

## Timetables

- [x] Option to show 24:xx / 25:xx as 0:xx / 1:xx (next day)
- [ ] Group by direction / boarding platform (のりば) at large stations
- [ ] Vertical (tategaki) friendly HTML variant
- [ ] Highlight first and last departures (始発 / 最終)
- [ ] Route timetable: mark stops where a trip passes without stopping (レ)
- [ ] Route timetable: split into pages of N trips
- [ ] Use the ja-Hrkt / en translations for an English or ruby-annotated timetable
- [ ] `--lang en` timetables that use translated stop and headsign names
- [ ] Frequency-based trips (frequencies.txt)
- [ ] Batch mode: one HTML file per stop with an index page

## Diff

- [ ] Diff route timetables
- [ ] Detect stops that moved by more than N metres
- [ ] Fare changes (price per fare_id)
- [ ] JSON output for diffs

## Project

- [ ] Publish to PyPI
- [ ] Docs site with examples
- [ ] Benchmark on a large feed (100k+ stop_times) and stream stop_times if needed
- [ ] Type-check with mypy in CI
