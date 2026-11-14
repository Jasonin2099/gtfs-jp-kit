"""gtfs-jp-kit: GTFS-JP profile checks and Japanese-style timetables."""

from .feed import Feed, load_feed

__all__ = ["Feed", "load_feed", "__version__"]
__version__ = "0.1.0.dev0"
