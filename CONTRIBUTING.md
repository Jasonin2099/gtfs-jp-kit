# Contributing

Thanks for helping! Issues and pull requests in English or Japanese are welcome.
日本語での Issue・PR も歓迎します。

## Setup

```console
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
```

## Adding a check

1. Find the rule in the GTFS-JP v4 specification and note the section.
2. Add a function to the right module in `src/gtfs_jp_kit/checks/` (or a new
   one) that yields `Finding`s with an English and a Japanese message, and
   register it in `checks/__init__.py`.
3. Add a row for the code to `docs/rules.md` (a test fails otherwise).
4. Add a test that builds a broken feed with the `make_feed` fixture.

Choose the severity from the wording of the spec: 必須 / 禁止 → `error`,
[JP] value rules and probable mistakes → `warning`, 推奨 and notes → `info`.

## Test data

Tests use the synthetic feed in `tests/fixtures/tozai`; regenerate it with
`python tests/fixtures/make_tozai.py`. Please do not add real feeds unless
their license clearly allows redistribution, and add attribution next to them.

## Scope

GTFS validity in general belongs to the MobilityData validator. This project
covers what is specific to Japan, and presentation (timetables, diffs).
