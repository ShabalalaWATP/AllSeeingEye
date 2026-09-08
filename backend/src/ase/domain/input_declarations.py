"""Operator declarations anchored to exact privately extracted passages."""

from dataclasses import dataclass, replace
from uuid import UUID

from ase.domain.events import Event
from ase.domain.source_dates import Calendar, DateRole, resolve_source_date
from ase.domain.text_transformations import TextTransformation


@dataclass(frozen=True, slots=True)
class InputSourceDate:
    field: str
    raw_text: str
    role: DateRole
    calendar: Calendar


@dataclass(frozen=True, slots=True)
class InputPassageDeclaration:
    event_id: str
    content_hash: str
    transformations: tuple[TextTransformation, ...] = ()
    source_dates: tuple[InputSourceDate, ...] = ()


def apply_declarations(
    events: tuple[Event, ...],
    declarations: tuple[InputPassageDeclaration, ...],
    actor_id: UUID,
) -> tuple[Event, ...]:
    if not 1 <= len(declarations) <= 8 or len({row.event_id for row in declarations}) != len(
        declarations
    ):
        raise ValueError("Declare between one and eight unique passages")
    inventory = {event.id: event for event in events}
    result = dict(inventory)
    for row in declarations:
        event = inventory.get(row.event_id)
        if event is None or event.content_hash != row.content_hash:
            raise ValueError("Declaration passage or content digest no longer matches")
        if (
            not (row.transformations or row.source_dates)
            or len(event.transformations) + len(row.transformations) > 4
            or len(event.source_dates) + len(row.source_dates) > 4
        ):
            raise ValueError("Each passage supports up to four transformations and four dates")
        if any(item.origin == "operator" for item in event.transformations) or any(
            item.basis == "operator" for item in event.source_dates
        ):
            raise ValueError("Declarations require an original, undeclared passage")
        transformations = list(event.transformations)
        for transformation in row.transformations:
            original = getattr(event, transformation.field)
            if transformation.original_text != original:
                raise ValueError("Transformation original must match the exact whole passage field")
            transformations.append(
                replace(
                    transformation,
                    origin="operator",
                    actor_id=actor_id,
                    review_status="operator_declared",
                )
            )
        dates = list(event.source_dates)
        for source_date in row.source_dates:
            if source_date.field not in {"title", "summary"} or not source_date.raw_text.strip():
                raise ValueError("A source date requires a title or summary anchor")
            if source_date.raw_text not in (getattr(event, source_date.field) or ""):
                raise ValueError("Raw date must occur verbatim in the selected passage field")
            dates.append(
                resolve_source_date(
                    source_date.raw_text,
                    source_date.field,
                    source_date.calendar,
                    role=source_date.role,
                    actor_id=actor_id,
                )
            )
        # Only one explicit publication instant can populate previously unknown publication.
        # Day intervals and conflicting declarations never gain an artificial instant.
        publication = [row for row in dates if row.role == "publication"]
        published = event.published_at
        if published is None and len(publication) == 1:
            published = publication[0].value
        result[event.id] = replace(
            event,
            published_at=published,
            transformations=tuple(transformations),
            source_dates=tuple(dates),
        )
    return tuple(result[event.id] for event in events)
