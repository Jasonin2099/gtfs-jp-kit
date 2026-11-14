"""Japanese corporate numbers (法人番号).

GTFS-JP recommends using the 13-digit 法人番号 of the operator as
``agency_id`` (optionally with an ``_N`` suffix when one corporation
publishes several feeds). The first digit is a check digit defined by the
National Tax Agency:

    check = 9 - (Σ P_n × Q_n mod 9),  Q_n = 1 for odd n, 2 for even n

where P_n is the n-th digit of the 12-digit base number counted from the
right.
"""

from __future__ import annotations

import re

_AGENCY_ID = re.compile(r"^(\d{13})(?:_(\d+))?$")


def check_digit(base: str) -> int:
    """Return the check digit for a 12-digit base number.

    >>> check_digit("000012050002")
    7
    """
    if len(base) != 12 or not base.isdigit():
        raise ValueError("base number must be 12 digits")
    total = sum(int(d) * (1 if n % 2 else 2) for n, d in enumerate(reversed(base), start=1))
    return 9 - total % 9


def is_valid(number: str) -> bool:
    """True for a 13-digit corporate number with a correct check digit.

    >>> is_valid("7000012050002")
    True
    >>> is_valid("7000012050003")
    False
    """
    if len(number) != 13 or not number.isdigit():
        return False
    return int(number[0]) == check_digit(number[1:])


def parse_agency_id(agency_id: str) -> tuple[str, str] | None:
    """Split ``"<法人番号>_<枝番>"``; return None if it is not of that shape.

    >>> parse_agency_id("7000012050002_2")
    ('7000012050002', '2')
    >>> parse_agency_id("tozai-bus") is None
    True
    """
    m = _AGENCY_ID.match(agency_id)
    if not m:
        return None
    return m.group(1), m.group(2) or ""
