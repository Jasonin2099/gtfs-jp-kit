"""Command line interface: ``gtfs-jp <command>``."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, render
from .calendar import DAY_TYPES, parse_date
from .checks import run_checks
from .feed import load_feed
from .findings import summarize
from .info import render as render_info
from .info import summary
from .timetable import stop_timetable


def _cmd_check(args: argparse.Namespace) -> int:
    feed = load_feed(args.feed)
    findings = run_checks(feed)
    if args.ignore:
        ignored = set(args.ignore.split(","))
        findings = [f for f in findings if f.code not in ignored]
    if args.min_severity == "warning":
        findings = [f for f in findings if f.severity != "info"]
    elif args.min_severity == "error":
        findings = [f for f in findings if f.severity == "error"]
    counts = summarize(findings)
    if args.format == "json":
        json.dump(
            {"feed": args.feed, "summary": counts, "findings": [f.to_dict() for f in findings]},
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        for f in findings:
            print(f.text(args.lang))
        if args.lang == "ja":
            print(f"エラー {counts['error']} / 警告 {counts['warning']} / 情報 {counts['info']}")
        else:
            print(f"{counts['error']} errors, {counts['warning']} warnings, {counts['info']} info")
    if counts["error"] or (args.strict and counts["warning"]):
        return 1
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    s = summary(load_feed(args.feed))
    if args.format == "json":
        print(json.dumps(s, ensure_ascii=False, indent=2))
    else:
        print(render_info(s, args.lang))
    return 0


def _cmd_timetable_stop(args: argparse.Namespace) -> int:
    feed = load_feed(args.feed)
    day_types = tuple(t for t in args.days.split(",") if t)
    bad = [t for t in day_types if t not in DAY_TYPES]
    if bad:
        print(f"unknown day type: {', '.join(bad)} (use {', '.join(DAY_TYPES)})", file=sys.stderr)
        return 2
    try:
        tt = stop_timetable(
            feed,
            args.stop,
            on=parse_date(args.date) if args.date else None,
            day_types=day_types,
            routes=set(args.route) if args.route else None,
            lang=args.lang,
        )
    except KeyError as e:
        print(e.args[0], file=sys.stderr)
        return 2
    if args.format == "md":
        sys.stdout.write(render.stop_markdown(tt, args.lang))
    elif args.format == "csv":
        sys.stdout.write(render.stop_csv(tt))
    else:
        sys.stdout.write(render.stop_text(tt, args.lang))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gtfs-jp", description="GTFS-JP toolkit")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("check", help="check a feed against the GTFS-JP v4 profile")
    c.add_argument("feed", help="GTFS zip file or directory")
    c.add_argument("--format", choices=["text", "json"], default="text")
    c.add_argument("--lang", choices=["en", "ja"], default="en", help="message language")
    c.add_argument(
        "--min-severity", choices=["info", "warning", "error"], default="info", dest="min_severity"
    )
    c.add_argument("--ignore", default="", help="comma-separated finding codes to drop")
    c.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    c.set_defaults(func=_cmd_check)

    i = sub.add_parser("info", help="summarize a feed")
    i.add_argument("feed")
    i.add_argument("--format", choices=["text", "json"], default="text")
    i.add_argument("--lang", choices=["en", "ja"], default="en")
    i.set_defaults(func=_cmd_info)

    t = sub.add_parser("timetable", help="print timetables")
    tsub = t.add_subparsers(dest="kind", required=True)
    ts = tsub.add_parser("stop", help="stop timetable (停留所時刻表)")
    ts.add_argument("feed")
    ts.add_argument("stop", help="stop_id, station id or exact stop_name")
    ts.add_argument("--date", help="one service date (YYYYMMDD); default: regular day types")
    ts.add_argument("--days", default=",".join(DAY_TYPES), help="weekday,saturday,sunday")
    ts.add_argument("--route", action="append", help="only this route_id (repeatable)")
    ts.add_argument("--format", choices=["text", "md", "csv"], default="text")
    ts.add_argument("--lang", choices=["en", "ja"], default="en")
    ts.set_defaults(func=_cmd_timetable_stop)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
