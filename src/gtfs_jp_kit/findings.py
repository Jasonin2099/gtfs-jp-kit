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


def markdown_report(findings: list[Finding], lang: str = "en", title: str = "") -> str:
    """A Markdown report, e.g. for a pull request comment or a job summary."""
    counts = summarize(findings)
    ja = lang == "ja"
    head = title or ("GTFS-JP チェック結果" if ja else "GTFS-JP check")
    if ja:
        line = f"エラー {counts['error']} / 警告 {counts['warning']} / 情報 {counts['info']}"
    else:
        line = f"{counts['error']} errors, {counts['warning']} warnings, {counts['info']} info"
    out = [f"### {head}", "", line, ""]
    if findings:
        cols = (
            ("重要度", "コード", "場所", "内容") if ja else ("Severity", "Code", "Where", "Message")
        )
        out.append("| " + " | ".join(cols) + " |")
        out.append("|---|---|---|---|")
        for f in findings:
            where = f.file + (f":{f.line}" if f.line else "") + (f" `{f.field}`" if f.field else "")
            msg = (f.message_ja if ja else f.message).replace("|", "\\|")
            out.append(f"| {f.severity} | `{f.code}` | {where} | {msg} |")
    return "\n".join(out) + "\n"
