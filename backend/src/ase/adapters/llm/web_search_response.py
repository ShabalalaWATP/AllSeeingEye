"""Parse bounded Responses web-search output without treating generated prose as evidence."""

from typing import Any

from ase.application.ports.web_search import WebSearchResult
from ase.domain.web_research import (
    MAX_CITATIONS,
    MAX_CONSULTED_URLS,
    MAX_SYNTHESIS,
    WebCitation,
    public_web_url,
)


def _tokens(value: Any) -> int | None:
    return value if type(value) is int and 0 <= value <= 10_000_000 else None


def _content(data: dict[str, Any]) -> tuple[str, tuple[WebCitation, ...]]:
    text = ""
    citations: list[WebCitation] = []
    for item in data.get("output", ()):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for part in item.get("content", ()):
            if not isinstance(part, dict) or part.get("type") != "output_text":
                continue
            value = part.get("text")
            if not isinstance(value, str):
                continue
            offset = len(text) + (2 if text else 0)
            text += ("\n\n" if text else "") + value
            for annotation in part.get("annotations", ()):
                if not isinstance(annotation, dict) or annotation.get("type") != "url_citation":
                    continue
                start, end = annotation.get("start_index"), annotation.get("end_index")
                url, title = annotation.get("url"), annotation.get("title")
                if (
                    type(start) is not int
                    or type(end) is not int
                    or not 0 <= start <= end <= len(value)
                    or not isinstance(url, str)
                    or not isinstance(title, str)
                    or end + offset > MAX_SYNTHESIS
                ):
                    continue
                try:
                    citation = WebCitation(url, title[:300], start + offset, end + offset)
                except ValueError:
                    continue
                if citation not in citations and len(citations) < MAX_CITATIONS:
                    citations.append(citation)
    return text[:MAX_SYNTHESIS], tuple(citations)


def parse_web_response(data: Any, fallback_model: str, latency_ms: float) -> WebSearchResult:
    if not isinstance(data, dict) or not isinstance(data.get("output"), list):
        return WebSearchResult(
            "",
            (),
            (),
            fallback_model,
            0,
            latency_ms,
            failure="The web-search endpoint returned an invalid response.",
        )
    raw_usage = data.get("usage")
    usage: dict[str, Any] = raw_usage if isinstance(raw_usage, dict) else {}
    prompt, completion = _tokens(usage.get("input_tokens")), _tokens(usage.get("output_tokens"))
    model = data.get("model")
    model = model if isinstance(model, str) and 0 < len(model) <= 200 else fallback_model
    calls = [
        item
        for item in data["output"]
        if isinstance(item, dict) and item.get("type") == "web_search_call"
    ]
    completed = [item for item in calls if item.get("status") == "completed"]
    failure = None
    if data.get("status") != "completed":
        failure = "The model did not finish within its web-search output budget."
    elif (
        not completed
        or len(completed) != len(calls)
        or len(calls) > 3
        or not any(
            isinstance(row.get("action"), dict) and row["action"].get("type") == "search"
            for row in completed
        )
    ):
        failure = "No complete bounded live web search was confirmed by the provider."
    try:
        synthesis, citations = _content(data)
    except (TypeError, ValueError):
        synthesis, citations = "", ()
    if not synthesis.strip() or not citations:
        failure = failure or "The web search returned no attributable generated context."
    consulted: list[str] = []
    for item in completed:
        action = item.get("action")
        sources = action.get("sources", ()) if isinstance(action, dict) else ()
        if not isinstance(sources, list):
            continue
        for source in sources:
            url = source.get("url") if isinstance(source, dict) else None
            if (
                isinstance(url, str)
                and public_web_url(url)
                and url not in consulted
                and len(consulted) < MAX_CONSULTED_URLS
            ):
                consulted.append(url)
    return WebSearchResult(
        synthesis if failure is None else "",
        citations if failure is None else (),
        tuple(consulted) if failure is None else (),
        model,
        min(len(calls), 3),
        latency_ms,
        prompt,
        completion,
        failure,
    )
