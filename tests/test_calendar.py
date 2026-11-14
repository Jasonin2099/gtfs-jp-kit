from datetime import date

from gtfs_jp_kit.calendar import ServiceCalendar


def test_active_with_holiday_exception(tozai):
    cal = ServiceCalendar(tozai)
    assert cal.active(date(2026, 11, 24)) == {"WD"}  # Tuesday
    assert cal.active(date(2026, 11, 23)) == {"SU"}  # Monday, 勤労感謝の日
    assert cal.active(date(2026, 11, 28)) == {"SA"}
    assert cal.active(date(2027, 5, 1)) == set()  # after the feed


def test_period_and_day_types(tozai):
    cal = ServiceCalendar(tozai)
    assert cal.period() == (date(2026, 10, 1), date(2027, 3, 31))
    assert cal.day_type_services("weekday") == {"WD"}
    assert cal.day_type_services("sunday") == {"SU"}


def test_calendar_dates_only(make_feed):
    dates = "service_id,date,exception_type\nX,20261107,1\nX,20261114,1\nX,20261108,1\n"
    cal = ServiceCalendar(make_feed(calendar=None, calendar_dates=dates))
    assert cal.day_type_services("saturday") == {"X"}
    assert cal.dates("X")[0] == date(2026, 11, 7)
