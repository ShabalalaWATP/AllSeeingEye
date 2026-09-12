"""Source admission registration for the packaged historical actor reference."""

from datetime import timedelta

from ase.domain.events import Category, Reliability
from ase.domain.sources import SourceKind, SourceSpec

MITRE_ATTACK_SPEC = SourceSpec(
    id="mitre_attack",
    name="MITRE ATT&CK actor reference",
    organisation="The MITRE Corporation",
    category=Category.CYBER,
    kind=SourceKind.API,
    url="https://github.com/mitre-attack/attack-stix-data",
    reliability=Reliability.F,
    # This metadata satisfies the source contract. No collector is scheduled.
    poll_interval=timedelta(days=1),
    licence_note="MITRE ATT&CK terms of use; packaged copyright and licence retained",
    homepage="https://attack.mitre.org/groups/",
    flags=frozenset({"reference", "on_demand", "unassessed"}),
)
