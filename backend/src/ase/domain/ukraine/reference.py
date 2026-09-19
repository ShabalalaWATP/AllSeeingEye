"""Curated reference notes for the Ukraine page: equipment, force structure and the timeline.

These are background written by hand with a source link and an as-of date on every entry,
enriched with Wikidata identifiers, articles and licensed images. They are notes, never
intelligence: the page labels them as reference and shows who wrote and dated them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from types import MappingProxyType

MAX_EQUIPMENT = 200
MAX_FORCE_NODES = 800
MAX_TIMELINE_EVENTS = 160
MAX_PHASES = 16
MAX_IMAGES = 400
MAX_LINKS = 8
MAX_TITLE = 160
MAX_TEXT = 900
MAX_IMAGE_BYTES = 60_000


class Side(StrEnum):
    RU = "ru"
    UA = "ua"


# Speciality groups in display order, with the sub-headings inside each.
SPECIALITIES: Mapping[str, tuple[str, Mapping[str, str]]] = MappingProxyType(
    {
        "drones": (
            "Drones",
            MappingProxyType(
                {
                    "reconnaissance": "Reconnaissance",
                    "fpv": "FPV strike drones",
                    "fibre_optic": "Fibre-optic FPV",
                    "loitering": "Loitering munitions",
                    "long_range": "Long-range one-way attack",
                    "interceptor": "Interceptor drones",
                    "naval_ground": "Naval and ground drones",
                }
            ),
        ),
        "communications_ew": (
            "Communications and electronic warfare",
            MappingProxyType(
                {
                    "satcom": "Satellite links",
                    "radios": "Tactical radios",
                    "command_software": "Command software",
                    "jamming": "Jamming and direction finding",
                    "gnss": "GNSS interference",
                }
            ),
        ),
        "air_defence": (
            "Air defence",
            MappingProxyType(
                {
                    "long_range": "Long range",
                    "medium_range": "Medium range",
                    "short_range": "Short range and point defence",
                    "manpads": "MANPADS and mobile fire groups",
                    "counter_drone": "Counter-drone",
                }
            ),
        ),
        "missiles": (
            "Land-attack missiles and glide bombs",
            MappingProxyType(
                {
                    "ballistic": "Ballistic missiles",
                    "cruise": "Cruise missiles",
                    "anti_radiation": "Anti-radiation and anti-ship missiles",
                    "guided_rockets": "Guided rockets",
                    "glide_bombs": "Glide bombs",
                }
            ),
        ),
        "artillery": (
            "Artillery",
            MappingProxyType(
                {
                    "self_propelled": "Self-propelled guns",
                    "towed": "Towed guns",
                    "rocket": "Rocket artillery",
                    "thermobaric": "Thermobaric",
                }
            ),
        ),
        "small_arms": (
            "Small arms and infantry weapons",
            MappingProxyType(
                {
                    "rifles": "Rifles",
                    "machine_guns": "Machine guns",
                    "anti_tank": "Anti-tank weapons",
                    "mortars": "Mortars and grenade launchers",
                    "sniper": "Sniper and anti-materiel rifles",
                }
            ),
        ),
        "tanks": (
            "Tanks",
            MappingProxyType({"main_battle": "Main battle tanks", "legacy": "Legacy tanks"}),
        ),
        "ifv_apc": (
            "Infantry fighting vehicles and armoured personnel carriers",
            MappingProxyType(
                {
                    "ifv": "Infantry fighting vehicles",
                    "apc": "Armoured personnel carriers",
                    "mrap": "Protected mobility",
                }
            ),
        ),
        "aviation": (
            "Aviation",
            MappingProxyType(
                {
                    "fighters": "Fighters",
                    "strike": "Strike and attack aircraft",
                    "helicopters": "Helicopters",
                    "bombers": "Bombers and special mission",
                }
            ),
        ),
        "naval": (
            "Naval",
            MappingProxyType(
                {
                    "surface": "Surface combatants",
                    "submarines": "Submarines",
                    "coastal": "Coastal and riverine",
                    "mines": "Naval mines and countermeasures",
                }
            ),
        ),
        "sensors": (
            "Radars, sensors and imagery",
            MappingProxyType(
                {
                    "counter_battery": "Counter-battery and ground surveillance radars",
                    "air_surveillance": "Air surveillance radars",
                    "acoustic": "Acoustic and passive detection",
                    "optics": "Night vision and thermal optics",
                    "space_isr": "Satellite imagery and space services",
                }
            ),
        ),
        "engineering": (
            "Engineering, mine warfare and logistics",
            MappingProxyType(
                {
                    "bridging": "Bridging and crossing",
                    "fortification": "Fortification and obstacles",
                    "mine_laying": "Mine laying",
                    "demining": "Demining and breaching",
                    "logistics": "Logistics and recovery vehicles",
                }
            ),
        ),
    }
)

TIMELINE_THEMES: Mapping[str, str] = MappingProxyType(
    {
        "ground": "Ground war",
        "air": "Air and missile war",
        "naval": "Naval war",
        "diplomacy": "Diplomacy and aid",
        "mobilisation": "Mobilisation and command",
        "economy": "Economy and infrastructure",
    }
)


@dataclass(frozen=True, slots=True)
class Link:
    label: str
    url: str


@dataclass(frozen=True, slots=True)
class ReferenceImage:
    id: str
    licence: str
    credit: str
    source_url: str
    width: int
    height: int
    bytes: int


@dataclass(frozen=True, slots=True)
class EquipmentEntry:
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
    links: tuple[Link, ...]


@dataclass(frozen=True, slots=True)
class ForceNode:
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
    links: tuple[Link, ...]


@dataclass(frozen=True, slots=True)
class TimelinePhase:
    id: str
    label: str
    start: date
    end: date | None
    summary: str


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    id: str
    phase_id: str
    on: date
    title: str
    text: str
    theme: str
    wikidata_id: str | None
    image_id: str | None
    links: tuple[Link, ...]


@dataclass(frozen=True, slots=True)
class ReferenceCatalogue:
    retrieved_at: datetime
    source_note: str
    equipment: tuple[EquipmentEntry, ...]
    forces: tuple[ForceNode, ...]
    phases: tuple[TimelinePhase, ...]
    events: tuple[TimelineEvent, ...]
    images: Mapping[str, ReferenceImage]

    def __post_init__(self) -> None:
        if len(self.equipment) > MAX_EQUIPMENT or len(self.forces) > MAX_FORCE_NODES:
            raise ValueError("Reference catalogue exceeds the equipment or force bound")
        if len(self.events) > MAX_TIMELINE_EVENTS or len(self.phases) > MAX_PHASES:
            raise ValueError("Reference catalogue exceeds the timeline bound")
        if len(self.images) > MAX_IMAGES:
            raise ValueError("Reference catalogue exceeds the image bound")
        ids = [*(e.id for e in self.equipment), *(f.id for f in self.forces)]
        ids += [*(p.id for p in self.phases), *(e.id for e in self.events)]
        if len(set(ids)) != len(ids):
            raise ValueError("Reference ids must be unique across the catalogue")
        node_ids = {node.id for node in self.forces}
        if any(n.parent_id is not None and n.parent_id not in node_ids for n in self.forces):
            raise ValueError("Force node parent missing")
        phase_ids = {phase.id for phase in self.phases}
        if any(event.phase_id not in phase_ids for event in self.events):
            raise ValueError("Timeline event phase missing")
        for entry in self.equipment:
            groups = SPECIALITIES.get(entry.group)
            if groups is None or entry.subgroup not in groups[1]:
                raise ValueError(f"Unknown speciality {entry.group}/{entry.subgroup}")
        if any(event.theme not in TIMELINE_THEMES for event in self.events):
            raise ValueError("Unknown timeline theme")
        images = {
            *(e.image_id for e in self.equipment),
            *(n.image_id for n in self.forces),
            *(e.image_id for e in self.events),
        }
        if any(image is not None and image not in self.images for image in images):
            raise ValueError("Image reference missing from the manifest")
