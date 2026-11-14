"""Read a GTFS feed from a ZIP file or a directory.

Only the standard library is used. Every row keeps the line number it came
from so that checks can point at the exact place in the source file.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


@dataclass
class Table:
    """One ``*.txt`` file of a feed."""

    name: str
    columns: list[str]
    rows: list[dict[str, str]]
    lines: list[int] = field(default_factory=list)

    def __iter__(self) -> Iterator[dict[str, str]]:
        return iter(self.rows)

    def __len__(self) -> int:
        return len(self.rows)

    def with_lines(self) -> Iterator[tuple[int, dict[str, str]]]:
        """Yield ``(line_number, row)``; line 1 is the header."""
        return zip(self.lines, self.rows)

    def index(self, key: str) -> dict[str, dict[str, str]]:
        """Map ``row[key]`` to the row (last one wins on duplicates)."""
        return {r.get(key, ""): r for r in self.rows}


def _decode(raw: bytes) -> str:
    # GTFS must be UTF-8; many Japanese feeds add a BOM. Fall back to cp932 so
    # that a mis-encoded feed can still be loaded and reported by the checks.
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp932", errors="replace")


def parse_table(name: str, raw: bytes) -> Table:
    text = _decode(raw)
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(reader)
    except StopIteration:
        return Table(name=name, columns=[], rows=[], lines=[])
    columns = [c.strip() for c in header]
    rows: list[dict[str, str]] = []
    lines: list[int] = []
    for values in reader:
        if not values or all(v.strip() == "" for v in values):
            continue
        row = {col: (values[i].strip() if i < len(values) else "") for i, col in enumerate(columns)}
        rows.append(row)
        lines.append(reader.line_num)
    return Table(name=name, columns=columns, rows=rows, lines=lines)


class Feed:
    """A lazily parsed GTFS feed.

    >>> feed = load_feed("tests/fixtures/minato")  # doctest: +SKIP
    >>> len(feed["stops"])  # doctest: +SKIP
    """

    def __init__(self, files: dict[str, bytes], source: str = "") -> None:
        self._raw = files
        self._cache: dict[str, Table] = {}
        self.source = source

    @property
    def file_names(self) -> list[str]:
        return sorted(self._raw)

    def has(self, name: str) -> bool:
        return _txt(name) in self._raw

    def get(self, name: str) -> Table | None:
        fname = _txt(name)
        if fname not in self._raw:
            return None
        if fname not in self._cache:
            self._cache[fname] = parse_table(fname, self._raw[fname])
        return self._cache[fname]

    def __getitem__(self, name: str) -> Table:
        table = self.get(name)
        if table is None:
            return Table(name=_txt(name), columns=[], rows=[], lines=[])
        return table

    def raw(self, name: str) -> bytes | None:
        return self._raw.get(name)


def _txt(name: str) -> str:
    return name if "." in name else f"{name}.txt"


def load_feed(path: PathLike) -> Feed:
    """Load a feed from a ``.zip`` file or a directory of ``.txt`` files.

    Files inside a single top-level folder in the ZIP are accepted too, which
    is a common packaging mistake in published feeds.
    """
    p = Path(path)
    files: dict[str, bytes] = {}
    if p.is_dir():
        for f in sorted(p.iterdir()):
            if f.is_file() and f.suffix in (".txt", ".geojson"):
                files[f.name] = f.read_bytes()
    elif zipfile.is_zipfile(p):
        with zipfile.ZipFile(p) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                base = info.filename.rsplit("/", 1)[-1]
                if base.endswith((".txt", ".geojson")) and not base.startswith("."):
                    files.setdefault(base, zf.read(info))
    else:
        raise FileNotFoundError(f"not a GTFS zip or directory: {path}")
    return Feed(files, source=str(path))
