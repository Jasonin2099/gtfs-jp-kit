"""Service days from calendar.txt and calendar_dates.txt."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from .feed import Feed

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

#: Day types used by Japanese timetables (平日 / 土曜 / 日曜・祝日).
DAY_TYPES = ("weekday", "saturday", "sunday")
DAY_TYPE_LABELS = {
    "en": {"weekday": "Weekdays", "saturday": "Saturdays", "sunday": "Sundays & holidays"},
    "ja": {"weekday": "平日", "saturday": "土曜", "sunday": "日曜・祝日"},
}


def parse_date(value: str) -> date:
    """Parse ``YYYYMMDD`` (GTFS) or ``YYYY-MM-DD``.

    >>> parse_date("20261123")
    datetime.date(2026, 11, 23)
    """
    v = value.replace("-", "")
    return date(int(v[:4]), int(v[4:6]), int(v[6:8]))


def _day_type(d: date) -> str:
    wd = d.weekday()
    return "weekday" if wd < 5 else ("saturday" if wd == 5 else "sunday")


class ServiceCalendar:
    def __init__(self, feed: Feed) -> None:
        self.weekly: dict[str, tuple[set[int], date, date]] = {}
        for row in feed["calendar"]:
            days = {i for i, name in enumerate(WEEKDAYS) if row.get(name) == "1"}
            try:
                start, end = parse_date(row["start_date"]), parse_date(row["end_date"])
            except (KeyError, ValueError, IndexError):
                continue
            self.weekly[row.get("service_id", "")] = (days, start, end)
        self.added: dict[str, set[date]] = {}
        self.removed: dict[str, set[date]] = {}
        for row in feed["calendar_dates"]:
            try:
                d = parse_date(row["date"])
            except (KeyError, ValueError, IndexError):
                continue
            target = self.added if row.get("exception_type") == "1" else self.removed
            target.setdefault(row.get("service_id", ""), set()).add(d)

    @property
    def service_ids(self) -> list[str]:
        return sorted(set(self.weekly) | set(self.added))

    def runs_on(self, service_id: str, d: date) -> bool:
        if d in self.removed.get(service_id, ()):
            return False
        if d in self.added.get(service_id, ()):
            return True
        weekly = self.weekly.get(service_id)
        return bool(weekly and weekly[1] <= d <= weekly[2] and d.weekday() in weekly[0])

    def active(self, d: date) -> set[str]:
        """Service IDs running on ``d``."""
        return {s for s in self.service_ids if self.runs_on(s, d)}

    def dates(self, service_id: str) -> list[date]:
        out = set(self.added.get(service_id, ()))
        weekly = self.weekly.get(service_id)
        if weekly:
            days, start, end = weekly
            d = start
            while d <= end:
                if d.weekday() in days:
                    out.add(d)
                d += timedelta(days=1)
        return sorted(out - self.removed.get(service_id, set()))

    def period(self) -> tuple[date, date] | None:
        all_dates = [d for s in self.service_ids for d in self.dates(s)]
        return (min(all_dates), max(all_dates)) if all_dates else None

    def day_type_services(self, day_type: str) -> set[str]:
        """Services that make up the regular 平日 / 土曜 / 日祝 timetable.

        A calendar.txt service belongs to a day type when it runs on any day
        of that type in its weekly pattern. A calendar_dates.txt-only service
        is classified by the day type of most of its dates.
        """
        wanted = {"weekday": {0, 1, 2, 3, 4}, "saturday": {5}, "sunday": {6}}[day_type]
        out = set()
        for sid in self.service_ids:
            weekly = self.weekly.get(sid)
            if weekly and weekly[0]:
                if weekly[0] & wanted:
                    out.add(sid)
            else:
                counts = Counter(_day_type(d) for d in self.added.get(sid, ()))
                if counts and counts.most_common(1)[0][0] == day_type:
                    out.add(sid)
        return out
