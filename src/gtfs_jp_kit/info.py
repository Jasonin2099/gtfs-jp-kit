"""One-screen summary of a feed."""

from __future__ import annotations

from .calendar import ServiceCalendar
from .feed import Feed

COUNTED = ("agency", "stops", "routes", "trips", "stop_times", "translations", "shapes")


def summary(feed: Feed) -> dict:
    info = feed["feed_info"].rows[0] if len(feed["feed_info"]) else {}
    cal = ServiceCalendar(feed)
    period = cal.period()
    langs = sorted({r.get("language", "") for r in feed["translations"]} - {""})
    return {
        "publisher": info.get("feed_publisher_name", ""),
        "version": info.get("feed_version", ""),
        "feed_start_date": info.get("feed_start_date", ""),
        "feed_end_date": info.get("feed_end_date", ""),
        "service_period": [d.isoformat() for d in period] if period else [],
        "agencies": [r.get("agency_name", "") for r in feed["agency"]],
        "counts": {name: len(feed[name]) for name in COUNTED if feed.has(name)},
        "services": cal.service_ids,
        "translation_languages": langs,
        "files": feed.file_names,
    }


def render(s: dict, lang: str = "en") -> str:
    ja = lang == "ja"
    lines = [
        f"{'提供組織' if ja else 'Publisher'}: {s['publisher']}  ({s['version']})",
        f"{'有効期間' if ja else 'Valid'}: {s['feed_start_date']} - {s['feed_end_date']}",
    ]
    if s["service_period"]:
        a, b = s["service_period"]
        lines.append(f"{'運行日' if ja else 'Service days'}: {a} - {b}")
    lines.append(f"{'事業者' if ja else 'Agencies'}: {', '.join(s['agencies'])}")
    lines.append(
        ("件数" if ja else "Counts") + ": " + ", ".join(f"{k} {v}" for k, v in s["counts"].items())
    )
    lines.append(f"{'運行区分' if ja else 'Services'}: {', '.join(s['services'])}")
    if s["translation_languages"]:
        lines.append(
            f"{'翻訳言語' if ja else 'Translations'}: {', '.join(s['translation_languages'])}"
        )
    return "\n".join(lines)
