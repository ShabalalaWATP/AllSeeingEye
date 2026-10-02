"""Reviewed allocation vocabulary and duplicate-safe profile construction."""

from ase.application.research.source_allocation_types import AllocationProfile

PROFILE_VERSION = "ase-research-allocation-profiles-v1"
REVIEW_DATE = "2026-09-14"
NEWS = (
    "politics|government|diplomacy|conflict war|military|security|attacks|economy|trade|energy|"
    "migration|humanitarian|elections|sanctions|protests|technology|climate|health"
)
DEFENCE = "defence defense|military|security|warfare|drone drones|procurement|Ukraine|NATO|weapons"
CYBER = (
    "cyber cybersecurity|vulnerability vulnerabilities|exploitation exploits|malware|ransomware|"
    "phishing|intrusion|espionage|campaign|network|patch|attack attacks"
)
ECONOMY = (
    "economy economic|inflation|interest rates|growth|employment|monetary|banking|financial|"
    "trade|energy|GDP|business|investment"
)
COMPANY = "company corporate|registry|identity|ownership|control|officers|parent|business|LEI"
TECHNICAL = "domain|DNS|infrastructure|network|registration|registrar|hosting|ownership|mail"


def add_profile(
    result: dict[str, AllocationProfile],
    ids: str,
    terms: str,
    note: str,
    *,
    prefix: str = "research_publisher_",
    countries: tuple[str, ...] = (),
    primary: bool = False,
    local: bool = False,
) -> None:
    for suffix in ids.split():
        source_id = prefix + suffix
        if source_id in result:
            raise ValueError("Duplicate reviewed allocation profile")
        result[source_id] = AllocationProfile(
            tuple(terms.split("|")), f"{REVIEW_DATE}: {note}", countries, primary, local
        )
