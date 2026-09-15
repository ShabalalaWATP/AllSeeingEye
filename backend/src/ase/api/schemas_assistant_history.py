"""Bounded private Ask Eye snapshots; these are user-controlled chat text, not evidence."""

from datetime import datetime
from ipaddress import ip_address
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.api.schemas_assistant import AssistantAnswerOut


def _public_https_url(value: str) -> bool:
    if len(value) > 2048 or any(ord(char) < 33 or char in "\\<>\"'" for char in value):
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if parsed.scheme != "https" or not host or parsed.username or parsed.password:
            return False
        host = host.rstrip(".")
        if not host or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return False
        try:
            ip_address(host)
        except ValueError:
            return "." in host and all(part for part in host.split("."))
        return False
    except ValueError:
        return False


def _validate_text_tree(value: object) -> None:
    if isinstance(value, str):
        if len(value) > 4_000 or any(ord(char) < 32 and char not in "\n\t" for char in value):
            raise ValueError("Saved chat contains an invalid or oversized text field.")
    elif isinstance(value, dict):
        for child in value.values():
            _validate_text_tree(child)
    elif isinstance(value, list):
        if len(value) > 40:
            raise ValueError("Saved chat contains too many items.")
        for child in value:
            _validate_text_tree(child)


class SavedReportReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    version: int = Field(ge=1, le=1_000_000)


class SavedTurnIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2_000)
    scope: str = Field(pattern="^(global|viewport|selected|report)$")
    time_window: str = Field(pattern="^(auto|48|120|168|336|720|2160|8760)$")
    source_categories: list[str] | None = Field(default=None, max_length=14)
    # Keep the exact report selection beside the answer.  The answer contains
    # the frozen edition metadata too, but this field makes the saved turn's
    # scope explicit and lets the API reject mixed or tampered transcripts.
    report: SavedReportReference | None = None
    answer: AssistantAnswerOut

    @model_validator(mode="after")
    def valid_answer(self) -> "SavedTurnIn":
        if not self.question.strip() or not self.answer.paragraphs:
            raise ValueError("Only answered questions can be saved.")
        report_answer = self.answer.report
        if self.scope == "report":
            if (
                self.answer.scope.mode != "report"
                or report_answer is None
                or self.report is None
                or self.report.id != report_answer.id
                or self.report.version != report_answer.version
            ):
                raise ValueError(
                    "Report-scoped saved turns must identify the exact report edition."
                )
        elif (
            self.report is not None
            or self.answer.scope.mode == "report"
            or report_answer is not None
        ):
            raise ValueError("Map-scoped saved turns cannot include report context.")
        if len(self.answer.paragraphs) > 12 or len(self.answer.sources) > 32:
            raise ValueError("Saved answer exceeds its item limit.")
        for source in self.answer.sources:
            if source.url is not None and not _public_https_url(source.url):
                source.url = None
        if self.source_categories and any(len(item) > 40 for item in self.source_categories):
            raise ValueError("Source category is too long.")
        _validate_text_tree(self.model_dump(mode="json"))
        return self

    def safe_dict(self) -> dict[str, object]:
        answer = self.answer.model_dump(mode="json", exclude={"continuation_id", "model"})
        return {
            "question": self.question.strip(),
            "scope": self.scope,
            "time_window": self.time_window,
            "source_categories": self.source_categories,
            "report": self.report.model_dump(mode="json") if self.report else None,
            "answer": answer,
        }


class SavedConversationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    turns: list[SavedTurnIn] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def valid_title(self) -> "SavedConversationIn":
        if not self.title.strip():
            raise ValueError("Enter a title for the saved conversation.")
        return self


class SavedTurnOut(SavedTurnIn):
    pass


class SavedConversationOut(BaseModel):
    id: UUID
    title: str
    turns: list[SavedTurnOut]
    created_at: datetime
    updated_at: datetime
    snapshot_notice: str = (
        "Private user-controlled chat snapshot. Check source links before "
        "treating its text as evidence."
    )


class SavedConversationSummaryOut(BaseModel):
    id: UUID
    title: str
    turn_count: int
    created_at: datetime
    updated_at: datetime


class SavedConversationPageOut(BaseModel):
    items: list[SavedConversationSummaryOut]
