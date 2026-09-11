"""Bounded current written-question metadata, including corrections and withdrawals.

Contract: https://questions-statements-api.parliament.uk/swagger/v1/swagger.json
No member biographies, attachments or linked answer pages are fetched.
"""

from datetime import UTC
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.research.feed import search_terms
from ase.adapters.research_records.records import collect_json, receipt, text
from ase.adapters.research_subjects.events import subject_event as record_event
from ase.adapters.research_subjects.selection import day, in_window, selected
from ase.application.feeds.pipeline import strip_html
from ase.application.ports import Clock
from ase.domain.events import Category, Event
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchQuery


class ParliamentQuestionsProvider:
    supports_planned_terms = True

    id = "research-uk-parliament"
    name = "UK Parliament written questions"
    temporal_scope = (
        "First 20 current question records tabled in the requested period; "
        "answers may reflect later updates."
    )

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self.http, self.clock = http, clock

    def supports(self, query: ResearchQuery) -> bool:
        return selected(query, self.id, "parliament:") and (
            not query.country_isos or "GB" in query.country_isos
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Select UK Parliament with English terms and no conflicting country filter.",
            )
        url = (
            "https://questions-statements-api.parliament.uk/api/writtenquestions/questions?"
            + urlencode(
                {
                    "searchTerm": " ".join(search_terms(query)),
                    "take": 20,
                    "skip": 0,
                    "tabledWhenFrom": query.since.astimezone(UTC).date().isoformat(),
                    "tabledWhenTo": query.until.astimezone(UTC).date().isoformat(),
                    "includeWithdrawn": "true",
                    "expandMember": "false",
                    "sessionStatus": "Any",
                }
            )
        )
        return await collect_json(
            self.http,
            self.id,
            self.name,
            url,
            lambda data: self.parse(data, query),
            "First 20 matching written questions, filtered by tabled day. Current "
            "question/answer metadata may include later corrections; not an as-of archive. "
            "Questions are not findings, government answers are attributed claims. "
            "Attachments and linked records were not fetched; no completeness guarantee.",
        )

    def parse(self, data: dict[str, Any], query: ResearchQuery) -> list[Event]:
        rows = data.get("results")
        if not isinstance(rows, list):
            raise ValueError("Missing parliamentary results")
        result, seen = [], set()
        for wrapper in rows[:20]:
            row = wrapper.get("value") if isinstance(wrapper, dict) else None
            if not isinstance(row, dict):
                continue
            identity = row.get("id")
            published = day(text(row.get("dateTabled"), 40)[:10])
            question = text(strip_html(text(row.get("questionText"), 4000)), 1000)
            if (
                type(identity) is not int
                or identity <= 0
                or identity in seen
                or not question
                or not in_window(published, query)
            ):
                continue
            seen.add(identity)
            answer = text(strip_html(text(row.get("answerText"), 4000)), 650)
            withdrawn = row.get("isWithdrawn") if type(row.get("isWithdrawn")) is bool else None
            corrected = (
                row.get("answerIsCorrection")
                if type(row.get("answerIsCorrection")) is bool
                else None
            )
            result.append(
                record_event(
                    self.id,
                    str(identity),
                    text(row.get("heading")) or "UK Parliament written question",
                    f"Question: {question} "
                    f"Answer by {text(row.get('answeringBodyName'), 120) or 'unrecorded body'}: "
                    f"{answer or 'No answer text recorded.'} "
                    f"Withdrawn: {withdrawn if withdrawn is not None else 'unknown'}; "
                    f"correction flag: {corrected if corrected is not None else 'unknown'}. "
                    "Question and answer assertions are not independently verified.",
                    f"https://questions-statements-api.parliament.uk/api/writtenquestions/questions/{identity}",
                    self.clock.now(),
                    category=Category.POLITICAL,
                    published=published,
                    attributes={
                        "record_kind": "written_question_snapshot",
                        "question_id": identity,
                        "uin": text(row.get("uin"), 40),
                        "date_precision": "day",
                        "withdrawn": withdrawn,
                        "answer_correction": corrected,
                        "date_answered": text(row.get("dateAnswered"), 40) or None,
                    },
                ).with_changes(country_iso="GB")
            )
        return result
