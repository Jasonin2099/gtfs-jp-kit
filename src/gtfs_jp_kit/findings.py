"""The result type shared by all checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass

SEVERITIES = ("error", "warning", "info")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    message_ja: str
    file: str = ""
    line: int = 0
    field: str = ""
    spec: str = ""

    def text(self, lang: str = "en") -> str:
        where = self.file
        if self.line:
            where += f":{self.line}"
        if self.field:
            where += f" [{self.field}]"
        msg = self.message_ja if lang == "ja" else self.message
        ref = f" ({self.spec})" if self.spec else ""
        return f"{self.severity:7} {self.code:28} {where}  {msg}{ref}".rstrip()

    def to_dict(self) -> dict:
        return asdict(self)


def summarize(findings: list[Finding]) -> dict[str, int]:
    out = {s: 0 for s in SEVERITIES}
    for f in findings:
        out[f.severity] = out.get(f.severity, 0) + 1
    return out
