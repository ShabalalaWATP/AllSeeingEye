"""Attach execution-time translation provenance without changing original title anchors."""

from dataclasses import replace

from ase.application.ports.translate import TranslatedText
from ase.domain.events import Event
from ase.domain.text_transformations import TextTransformation


def translated_event(event: Event, translated: TranslatedText) -> Event:
    transformation = TextTransformation(
        field="title",
        original_text=event.title,
        transformed_text=translated.text,
        kind="translation",
        source_language=event.language,
        target_language="en",
        origin="machine",
        method="ase-title-translation-v1",
        model=translated.model,
        profile_id=translated.profile_id,
        provider=translated.provider,
        limitations=() if translated.model else ("The translator did not report model identity.",),
    )
    retained = tuple(
        row
        for row in event.transformations
        if not (row.field == "title" and row.kind == "translation" and row.origin == "machine")
    )
    if len(retained) >= 4:
        return event
    return replace(event, title_en=translated.text, transformations=(*retained, transformation))
