"""Render timetables as Markdown, CSV or plain text."""

from __future__ import annotations

import csv
import io

from .route_timetable import RouteTimetable
from .timetable import StopTimetable


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|")


def stop_markdown(tt: StopTimetable, lang: str = "en") -> str:
    hour = "時" if lang == "ja" else "Hour"
    lines = [f"## {_md_escape(tt.stop_name)}", ""]
    lines.append("| " + " | ".join([hour, *map(_md_escape, tt.columns)]) + " |")
    lines.append("|---:|" + "|".join(":---" for _ in tt.columns) + "|")
    for h in tt.hours:
        cells = [" ".join(tt.cell(c, h)) for c in tt.columns]
        lines.append("| " + " | ".join([tt.hour_label(h), *map(_md_escape, cells)]) + " |")
    legend = tt.legend(lang)
    if legend:
        lines.append("")
        lines.extend(f"- {_md_escape(x)}" for x in legend)
    return "\n".join(lines) + "\n"


def stop_text(tt: StopTimetable, lang: str = "en") -> str:
    out = [tt.stop_name]
    for c in tt.columns:
        out.append(f"[{c}]")
        for h in tt.hours:
            cell = tt.cell(c, h)
            if cell:
                out.append(f"{tt.hour_label(h):>3} | " + " ".join(cell))
    legend = tt.legend(lang)
    if legend:
        out.append("")
        out.extend(legend)
    return "\n".join(out) + "\n"


def stop_csv(tt: StopTimetable) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["column", "time", "route", "headsign", "symbol", "stop_id", "trip_id"])
    for c in tt.columns:
        for d in tt.departures[c]:
            w.writerow(
                [c, tt.time_label(d), d.route_name, d.headsign, d.symbol, d.stop_id, d.trip_id]
            )
    return buf.getvalue()


def route_markdown(rt: RouteTimetable, lang: str = "en") -> str:
    blank = "—"
    stop_label = "停留所" if lang == "ja" else "Stop"
    lines = [f"## {_md_escape(rt.route_name)} ({_md_escape(rt.title)})", ""]
    heads = [t.get("jp_trip_desc_symbol", "") + t.get("trip_headsign", "") for t in rt.trips]
    lines.append("| " + " | ".join([stop_label, *map(_md_escape, heads)]) + " |")
    lines.append("|:---|" + "|".join(":---:" for _ in rt.trips) + "|")
    for sid, name in rt.stops:
        cells = [c or blank for c in rt.row(sid)]
        lines.append("| " + " | ".join([_md_escape(name), *cells]) + " |")
    return "\n".join(lines) + "\n"


def route_csv(rt: RouteTimetable) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["stop_id", "stop_name", *(t["trip_id"] for t in rt.trips)])
    for sid, name in rt.stops:
        w.writerow([sid, name, *rt.row(sid)])
    return buf.getvalue()


def route_text(rt: RouteTimetable, lang: str = "en") -> str:
    width = max((len(n) for _, n in rt.stops), default=4)
    out = [f"{rt.route_name} ({rt.title})"]
    for sid, name in rt.stops:
        cells = [c or "  -  " for c in rt.row(sid)]
        # Full-width names: pad with ideographic spaces so columns line up.
        out.append(name + "\u3000" * (width - len(name)) + "  " + " ".join(cells))
    return "\n".join(out) + "\n"
