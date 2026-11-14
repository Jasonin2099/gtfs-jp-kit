"""Standalone, printable HTML timetables (no JavaScript, no external assets)."""

from __future__ import annotations

from html import escape

from .route_timetable import RouteTimetable
from .timetable import StopTimetable

CSS = """
:root { color-scheme: light dark; }
body { font-family: system-ui, "Hiragino Sans", "Noto Sans JP", sans-serif; margin: 1.5rem; }
h1 { font-size: 1.4rem; margin: 0 0 .75rem; }
table { border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { border: 1px solid #8884; padding: .25rem .5rem; vertical-align: top; }
thead th { background: #8882; }
th.hour { text-align: right; width: 2.5em; }
td.min { letter-spacing: .02em; min-width: 8em; }
td.min span { display: inline-block; margin-right: .6em; }
td.min b { font-weight: 600; font-size: .75em; margin-right: .05em; }
td.blank { color: #8888; text-align: center; }
ul.legend { padding-left: 1.2rem; font-size: .9rem; }
@media print { body { margin: 0; } thead th { background: none; } }
"""


def _page(title: str, body: str, lang: str) -> str:
    return (
        "<!doctype html>\n"
        f'<html lang="{"ja" if lang == "ja" else "en"}">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
        f"{body}</body>\n</html>\n"
    )


def stop_html(tt: StopTimetable, lang: str = "en") -> str:
    hour = "時" if lang == "ja" else "Hour"
    parts = [f"<h1>{escape(tt.stop_name)}</h1>\n<table>\n<thead><tr>"]
    parts.append(f'<th class="hour" scope="col">{hour}</th>')
    parts.extend(f'<th scope="col">{escape(c)}</th>' for c in tt.columns)
    parts.append("</tr></thead>\n<tbody>\n")
    for h in tt.hours:
        parts.append(f'<tr><th class="hour" scope="row">{tt.hour_label(h)}</th>')
        for c in tt.columns:
            spans = []
            for d in tt.departures[c]:
                if d.hour != h:
                    continue
                mark = tt.marks.get((d.route_name, d.headsign), "") + d.symbol
                title = escape(
                    f"{tt.time_label(d)} {d.route_name} {d.headsign}".strip(), quote=True
                )
                m = f"<b>{escape(mark)}</b>" if mark else ""
                spans.append(f'<span title="{title}">{m}{d.minute:02d}</span>')
            parts.append(f'<td class="min">{"".join(spans)}</td>')
        parts.append("</tr>\n")
    parts.append("</tbody>\n</table>\n")
    legend = tt.legend(lang)
    if legend:
        parts.append('<ul class="legend">')
        parts.extend(f"<li>{escape(x)}</li>" for x in legend)
        parts.append("</ul>\n")
    return _page(tt.stop_name, "".join(parts), lang)


def route_html(rt: RouteTimetable, lang: str = "en", color: str = "", text_color: str = "") -> str:
    stop_label = "停留所" if lang == "ja" else "Stop"
    style = ""
    if color and text_color:
        style = f' style="background:#{escape(color)};color:#{escape(text_color)}"'
    title = f"{rt.route_name} ({rt.title})"
    parts = [f"<h1><span{style}>&nbsp;{escape(rt.route_name)}&nbsp;</span> {escape(rt.title)}</h1>"]
    parts.append(f'\n<table>\n<thead><tr><th scope="col">{stop_label}</th>')
    for t in rt.trips:
        head = t.get("jp_trip_desc_symbol", "") + t.get("trip_headsign", "")
        desc = escape(t.get("jp_trip_desc", ""), quote=True)
        attr = f' title="{desc}"' if desc else ""
        parts.append(f'<th scope="col"{attr}>{escape(head)}</th>')
    parts.append("</tr></thead>\n<tbody>\n")
    for sid, name in rt.stops:
        parts.append(f'<tr><th scope="row">{escape(name)}</th>')
        for cell in rt.row(sid):
            parts.append(f"<td>{cell}</td>" if cell else '<td class="blank">—</td>')
        parts.append("</tr>\n")
    parts.append("</tbody>\n</table>\n")
    return _page(title, "".join(parts), lang)
