# gtfs-jp-kit

[![ci](https://github.com/Jasonin2099/gtfs-jp-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/Jasonin2099/gtfs-jp-kit/actions/workflows/ci.yml)

GTFS-JP profile checks and Japanese-style timetables for GTFS feeds, in pure
Python with no dependencies.

- **`gtfs-jp check`** checks the rules that the Japanese national profile
  ([GTFS-JP v4](https://www.mlit.go.jp/commmmons/document/007/), MLIT, March 2026)
  adds on top of GTFS: required files and fields, `ja-Hrkt` readings in
  translations.txt, 法人番号 agency IDs, `Asia/Tokyo`, yen fares, and the
  former v3 extension files. Messages in English or Japanese, text or JSON.
- **`gtfs-jp timetable stop`** prints a stop timetable the way it is posted at
  a Japanese bus stop: one row per hour, minutes per day type
  (平日 / 土曜 / 日曜・祝日), marks for other destinations and
  `jp_trip_desc_symbol`, as text, Markdown, CSV or printable HTML.
- **`gtfs-jp timetable route`** prints a route timetable (stops × trips).
- **`gtfs-jp diff`** shows what a timetable revision (ダイヤ改正) changes for
  passengers: departures moved, added or removed at a stop, stops renamed,
  routes added or removed.
- **`gtfs-jp info`** summarizes a feed.

```console
$ pip install git+https://github.com/Jasonin2099/gtfs-jp-kit
$ gtfs-jp check feed.zip --lang ja
$ gtfs-jp timetable stop feed.zip 東西駅前 --format md --lang ja
```

```markdown
| 時 | 平日 | 土曜 | 日曜・祝日 |
|---:|:---|:---|:---|
| 7 | み05 10 40 | 40 |  |
| 8 | み05 病20 |  |  |
| 9 | 20 | 20 | 20 |

- 無印：1 市民病院行き
- み：2 みどり団地行き
- 病: 市民病院 正面玄関まで乗り入れ
```

(Output from the fictional test feed in `tests/fixtures/tozai`.)

## Usage

```console
gtfs-jp check FEED [--profile v4|v3] [--lang en|ja] [--format text|json|markdown]
                   [--min-severity info|warning|error] [--ignore CODE,CODE] [--strict]
gtfs-jp info FEED [--lang en|ja] [--format text|json]
gtfs-jp timetable stop FEED STOP [--date YYYYMMDD | --days weekday,saturday,sunday]
                                 [--route ROUTE_ID] [--format text|md|csv|html] [--lang en|ja]
gtfs-jp timetable route FEED ROUTE_ID [--direction 0|1] [--date YYYYMMDD | --day weekday]
                                      [--format text|md|csv|html] [--lang en|ja]
gtfs-jp diff OLD NEW [--stop STOP ...] [--lang en|ja]
```

`--profile v3` checks a feed made for GTFS-JP v3 (標準的なバス情報フォーマット
第 3 版) against the v3 file and field table instead of v4: shapes.txt,
location_type, feed dates and feed_version are optional, nothing is 推奨, and
agency_jp.txt / office_jp.txt / pattern_jp.txt are not reported as leftovers.
Value rules (`ja`, `Asia/Tokyo`, `JPY`, readings) are the same, because v3 fixes
those values too. See [docs/rules.md](docs/rules.md#profiles).

Times after midnight keep GTFS service-day hours (24:30) by default;
`--wrap-midnight` prints them as 00:30 while keeping them at the end of the day.

`FEED` is a GTFS zip or a directory. `STOP` is a stop_id, a station
(its platforms are included) or an exact stop_name. `check` exits with 1 when
there are errors (or warnings with `--strict`), so it can gate CI.

In GitHub Actions, the Markdown report can go straight into the job summary:

```yaml
- run: pip install git+https://github.com/Jasonin2099/gtfs-jp-kit
- run: gtfs-jp check gtfs/ --lang ja --format markdown >> "$GITHUB_STEP_SUMMARY"
```

Every check code is listed in [docs/rules.md](docs/rules.md) with the part of
the specification it comes from.

From Python:

```python
from gtfs_jp_kit import load_feed
from gtfs_jp_kit.checks import run_checks
from gtfs_jp_kit.timetable import stop_timetable

feed = load_feed("feed.zip")
errors = [f for f in run_checks(feed) if f.severity == "error"]
tt = stop_timetable(feed, "東西駅前", lang="ja")
```

## Related projects / why this exists

Good tools already exist, and this project tries not to duplicate them:

- [MobilityData/gtfs-validator](https://github.com/MobilityData/gtfs-validator)
  is the reference validator for GTFS itself. It does not know the GTFS-JP
  profile (for example that translations.txt and `ja-Hrkt` readings are
  required). Run it first; gtfs-jp-kit only checks the Japanese layer.
- [gtfs-analyzer](https://github.com/ttezer/gtfs-analyzer) (Rust/WASM, browser)
  includes a GTFS-JP v3/v4 profile. gtfs-jp-kit is the small pip-installable
  equivalent for Python pipelines, notebooks and CI, with Japanese messages.
- [gtfs-semantic-diff](https://github.com/niyalist/gtfs-semantic-diff) does a full
  semantic diff of two feeds. `gtfs-jp diff` is intentionally narrow: the
  per-stop view needed for a 改正のお知らせ.
- [gtfs-to-html](https://github.com/BlinkTagInc/gtfs-to-html) (Node.js) builds
  route timetables for websites. gtfs-jp-kit adds the Japanese bus-stop layout
  (hour rows × day types, destination marks).
- [gtfs-kit](https://pypi.org/project/gtfs-kit/) and
  [partridge](https://github.com/remix/partridge) are pandas-based GTFS
  analysis libraries. gtfs-jp-kit uses only the standard library so that it
  installs anywhere, including small CI images.
- [GTFS-JP作成ツール（西沢ツール）](https://gtfs-gis.jp/gtfs/) creates GTFS-JP
  from Excel; gtfs-jp-kit is meant for checking and presenting the result.

## 日本語

gtfs-jp-kit は、GTFS データを「標準的なバス情報フォーマット」の後継である
**公共交通運行情報標準データ仕様（GTFS-JP）第 4 版**の観点でチェックし、
日本のバス停に掲示されているような時刻表を出力する Python ツールです。
依存ライブラリはありません。

- `gtfs-jp check`：GTFS-JP 独自の必須ファイル・必須項目、読み仮名（ja-Hrkt）、
  法人番号の検査用数字、`Asia/Tokyo`、円単位の運賃、第 3 版拡張ファイル
  （agency_jp.txt など）の参照整合性を確認します。`--lang ja` で日本語表示。
  第 3 版向けに作ったデータは `--profile v3` で第 3 版の必須・任意の区分で確認できます。
- `gtfs-jp timetable stop`：時ごとの行 × 平日・土曜・日曜祝日の列で停留所時刻表を
  作ります。行先違いと `jp_trip_desc_symbol` は記号と凡例で示します。
  テキスト・Markdown・CSV・印刷向け HTML に対応。
- `gtfs-jp timetable route`：路線時刻表（停留所 × 便）。
- `gtfs-jp diff`：ダイヤ改正で停留所の発車時刻がどう変わるか（時刻変更・新設・廃止）、
  停留所名の変更、路線の新設・廃止を表示します。

GTFS 本体の検証は [MobilityData の GTFS Validator](https://github.com/MobilityData/gtfs-validator)
に任せ、このツールは日本向けの規定だけを扱います。チェック項目と仕様書の該当箇所は
[docs/rules.md](docs/rules.md) を参照してください。

テスト用データ `tests/fixtures/tozai` は、仕様書の記載例に出てくる架空の「東西市」を
もとにした架空のデータです。実在の事業者・停留所とは関係ありません。

## License

MIT. The GTFS-JP specification is published by 国土交通省 (MLIT); this project
only refers to it.
