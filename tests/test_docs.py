"""Every finding code in the source must be documented in docs/rules.md."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rules_documented():
    src = "".join(
        p.read_text(encoding="utf-8") for p in (ROOT / "src/gtfs_jp_kit/checks").glob("*.py")
    )
    codes = set(re.findall(r'Finding\(\s*"([a-z0-9-]+)"', src))
    docs = set(
        re.findall(r"^\| `([a-z0-9-]+)` \|", (ROOT / "docs/rules.md").read_text("utf-8"), re.M)
    )
    assert codes, "no codes found"
    assert codes - docs == set(), "undocumented"
    assert docs - codes == set(), "documented but not implemented"
