"""Render timetables as Markdown, CSV or plain text."""

from __future__ import annotations

import csv
import io

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
        lines.append("| " + " | ".join([str(h), *map(_md_escape, cells)]) + " |")
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
                out.append(f"{h:>3} | " + " ".join(cell))
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
            w.writerow([c, d.hhmm, d.route_name, d.headsign, d.symbol, d.stop_id, d.trip_id])
    return buf.getvalue()
