from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import json
import re


@dataclass(frozen=True)
class Source:
    url: str
    title: str
    text: str


@dataclass(frozen=True)
class Finding:
    claim: str
    source_number: int
    excerpt: str


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.title = "Untitled source"
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        clean = " ".join(data.split())
        if not clean:
            return
        if self._in_title:
            self.title = clean
        self.parts.append(clean)


def plan(question: str, urls: list[str]) -> dict[str, object]:
    if not question.strip():
        raise ValueError("Question must not be blank.")
    if not urls:
        raise ValueError("Provide at least one source URL.")
    invalid = [url for url in urls if urlparse(url).scheme not in {"http", "https"}]
    if invalid:
        raise ValueError(f"Only http(s) URLs are allowed: {invalid[0]}")
    terms = [term.lower() for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9-]{2,}", question)]
    return {"question": question.strip(), "keywords": sorted(set(terms)), "urls": urls}


def fetch_source(url: str, timeout: int = 15) -> Source:
    request = Request(url, headers={"User-Agent": "AgentBrief/0.1 (+local research workflow)"})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "text/plain"}:
            raise ValueError(f"Unsupported source type {content_type} at {url}")
        body = response.read(1_500_000).decode(response.headers.get_content_charset() or "utf-8", "replace")
    if content_type == "text/plain":
        return Source(url=url, title=urlparse(url).netloc, text=" ".join(body.split()))
    parser = _TextExtractor()
    parser.feed(body)
    return Source(url=url, title=parser.title, text=" ".join(parser.parts))


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if len(sentence.strip()) >= 40]


def extract_findings(question: str, sources: list[Source], limit: int = 6) -> list[Finding]:
    keywords = set(plan(question, [source.url for source in sources])["keywords"])
    ranked: list[tuple[int, int, str]] = []
    for source_number, source in enumerate(sources, start=1):
        for sentence in _sentences(source.text):
            words = set(re.findall(r"[A-Za-z0-9-]+", sentence.lower()))
            score = len(keywords & words)
            if score:
                ranked.append((score, source_number, sentence))
    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    findings: list[Finding] = []
    seen: set[str] = set()
    for _, source_number, sentence in ranked:
        normalized = sentence.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        findings.append(Finding(claim=sentence, source_number=source_number, excerpt=sentence))
        if len(findings) == limit:
            break
    return findings


def run(question: str, urls: list[str], fetch=fetch_source) -> dict[str, object]:
    task_plan = plan(question, urls)
    sources: list[Source] = []
    errors: list[dict[str, str]] = []
    for url in urls:
        try:
            sources.append(fetch(url))
        except Exception as error:  # record failures rather than fabricate a result
            errors.append({"url": url, "error": str(error)})
    if not sources:
        raise RuntimeError("All sources failed to load; no briefing was written.")
    findings = extract_findings(question, sources)
    return {
        "plan": task_plan,
        "generated_at": datetime.now(UTC).isoformat(),
        "sources": [asdict(source) | {"text": source.text[:600]} for source in sources],
        "findings": [asdict(finding) for finding in findings],
        "errors": errors,
    }


def render_markdown(result: dict[str, object]) -> str:
    plan_data = result["plan"]
    assert isinstance(plan_data, dict)
    lines = [f"# Brief: {plan_data['question']}", "", "## Evidence-backed findings", ""]
    findings = result["findings"]
    assert isinstance(findings, list)
    if findings:
        for finding in findings:
            assert isinstance(finding, dict)
            lines.append(f"- {finding['claim']} [Source {finding['source_number']}]")
    else:
        lines.append("- No source sentence matched the question keywords. Review the sources below.")
    lines.extend(["", "## Sources", ""])
    sources = result["sources"]
    assert isinstance(sources, list)
    for number, source in enumerate(sources, start=1):
        assert isinstance(source, dict)
        lines.append(f"{number}. [{source['title']}]({source['url']})")
    errors = result["errors"]
    assert isinstance(errors, list)
    if errors:
        lines.extend(["", "## Sources that could not be loaded", ""])
        for error in errors:
            assert isinstance(error, dict)
            lines.append(f"- `{error['url']}` — {error['error']}")
    return "\n".join(lines) + "\n"


def write_result(output: Path, result: dict[str, object]) -> None:
    output.mkdir(parents=True, exist_ok=False)
    (output / "brief.md").write_text(render_markdown(result), encoding="utf-8")
    (output / "run.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

