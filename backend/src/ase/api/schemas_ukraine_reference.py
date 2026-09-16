"""Reference contract for the Ukraine page: equipment, force structure, timeline and images."""

from __future__ import annotations

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, Field

from ase.domain.ukraine.reference import (
    SPECIALITIES,
    TIMELINE_THEMES,
    EquipmentEntry,
    ForceNode,
    ReferenceCatalogue,
    Side,
    TimelineEvent,
)


class LinkOut(BaseModel):
    label: str
    url: str


class ReferenceImageOut(BaseModel):
    id: str
    licence: str
    credit: str
    source_url: str
    width: int = Field(ge=0)
    height: int = Field(ge=0)


class EquipmentOut(BaseModel):
    id: str
    side: Side
    group: str
    subgroup: str
    name: str
    origin: str
    role: str
    description: str
    numbers: str | None
    wikidata_id: str | None
    image_id: str | None
    as_of: date
    links: list[LinkOut]

    @classmethod
    def from_entry(cls, entry: EquipmentEntry) -> Self:
        return cls(
            id=entry.id,
            side=entry.side,
            group=entry.group,
            subgroup=entry.subgroup,
            name=entry.name,
            origin=entry.origin,
            role=entry.role,
            description=entry.description,
            numbers=entry.numbers,
            wikidata_id=entry.wikidata_id,
            image_id=entry.image_id,
            as_of=entry.as_of,
            links=[LinkOut(label=link.label, url=link.url) for link in entry.links],
        )


class ForceNodeOut(BaseModel):
    id: str
    side: Side
    parent_id: str | None
    name: str
    role: str
    commander: str | None
    figure_id: str | None
    strength: str | None
    wikidata_id: str | None
    image_id: str | None
    as_of: date
    links: list[LinkOut]

    @classmethod
    def from_node(cls, node: ForceNode) -> Self:
        return cls(
            id=node.id,
            side=node.side,
            parent_id=node.parent_id,
            name=node.name,
            role=node.role,
            commander=node.commander,
            figure_id=node.figure_id,
            strength=node.strength,
            wikidata_id=node.wikidata_id,
            image_id=node.image_id,
            as_of=node.as_of,
            links=[LinkOut(label=link.label, url=link.url) for link in node.links],
        )


class TimelinePhaseOut(BaseModel):
    id: str
    label: str
    start: date
    end: date | None
    summary: str


class TimelineEventOut(BaseModel):
    id: str
    phase_id: str
    on: date
    title: str
    text: str
    theme: str
    wikidata_id: str | None
    image_id: str | None
    links: list[LinkOut]

    @classmethod
    def from_event(cls, event: TimelineEvent) -> Self:
        return cls(
            id=event.id,
            phase_id=event.phase_id,
            on=event.on,
            title=event.title,
            text=event.text,
            theme=event.theme,
            wikidata_id=event.wikidata_id,
            image_id=event.image_id,
            links=[LinkOut(label=link.label, url=link.url) for link in event.links],
        )


class SpecialityOut(BaseModel):
    key: str
    label: str
    subgroups: dict[str, str]


class UkraineReferenceOut(BaseModel):
    retrieved_at: datetime
    source_note: str
    specialities: list[SpecialityOut]
    themes: dict[str, str]
    equipment: list[EquipmentOut]
    forces: list[ForceNodeOut]
    phases: list[TimelinePhaseOut]
    events: list[TimelineEventOut]
    images: dict[str, ReferenceImageOut]

    @classmethod
    def from_catalogue(cls, catalogue: ReferenceCatalogue) -> Self:
        return cls(
            retrieved_at=catalogue.retrieved_at,
            source_note=catalogue.source_note,
            specialities=[
                SpecialityOut(key=key, label=label, subgroups=dict(subgroups))
                for key, (label, subgroups) in SPECIALITIES.items()
            ],
            themes=dict(TIMELINE_THEMES),
            equipment=[EquipmentOut.from_entry(entry) for entry in catalogue.equipment],
            forces=[ForceNodeOut.from_node(node) for node in catalogue.forces],
            phases=[
                TimelinePhaseOut(
                    id=p.id, label=p.label, start=p.start, end=p.end, summary=p.summary
                )
                for p in catalogue.phases
            ],
            events=[TimelineEventOut.from_event(event) for event in catalogue.events],
            images={
                key: ReferenceImageOut(
                    id=image.id,
                    licence=image.licence,
                    credit=image.credit,
                    source_url=image.source_url,
                    width=image.width,
                    height=image.height,
                )
                for key, image in catalogue.images.items()
            },
        )
