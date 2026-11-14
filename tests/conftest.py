from __future__ import annotations

from pathlib import Path

import pytest

from gtfs_jp_kit.feed import Feed, load_feed

FIXTURE = Path(__file__).parent / "fixtures" / "tozai"


@pytest.fixture
def tozai() -> Feed:
    return load_feed(FIXTURE)


@pytest.fixture
def make_feed():
    """Build a feed from the fixture, replacing or dropping files.

    ``make_feed(stops="stop_id,...\\n...", shapes=None)``: a string replaces
    the file, ``None`` removes it.
    """

    def build(**files: str | None) -> Feed:
        raw = {p.name: p.read_bytes() for p in FIXTURE.iterdir() if p.suffix == ".txt"}
        for name, text in files.items():
            fname = f"{name}.txt"
            if text is None:
                raw.pop(fname, None)
            else:
                raw[fname] = text.encode("utf-8")
        return Feed(raw, source="test")

    return build
