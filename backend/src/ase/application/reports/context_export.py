"""Plain-text frozen context disclosures shared by report exports."""

from ase.domain.research_context import ResearchContext


def context_sections(value: ResearchContext | None) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if value is None:
        return ()
    sections = [("Research context", (f"Method: {value.method_version}.", *value.limitations))]
    timeline = tuple(
        f"{row.evidence_label}: {row.title}. Published: "
        f"{row.published_at.isoformat() if row.published_at else 'unknown'}; "
        f"observed: {row.observed_at.isoformat() if row.observed_at else 'unknown'}; "
        f"captured: {row.captured_at.isoformat()}. "
        f"Timestamp basis: {row.timestamp_basis or 'unknown'}; "
        f"precision: {row.date_precision or 'unknown'}. {' '.join(row.limitations)}"
        for row in value.timeline
    )
    sections.append(("Recorded publication timeline", timeline or ("No timeline records.",)))
    identities = tuple(
        f"{row.evidence_label}, unverified candidate. "
        + "; ".join(f"{item.namespace}: {item.value}" for item in (*row.identifiers, *row.aliases))
        + f". Declared match status: {row.declared_match_status or 'unknown'}."
        for row in value.identity_candidates
    )
    sections.append(
        ("Captured identity candidates", identities or ("No candidate identifiers saved.",))
    )
    chains = tuple(
        f"{row.evidence_label}: {row.collector_source_id}; {row.relation.replace('_', ' ')}: "
        f"{row.declared_name or 'unknown'}, identifier {row.declared_id or 'unknown'}. "
        f"Captured URL (unverified text): {row.declared_url or 'unknown'}."
        for row in value.source_chains
    )
    sections.append(("Declared source chains", chains or ("No attribution edges saved.",)))
    relations = tuple(
        f"{', '.join(row.evidence_labels)}: "
        f"{'; '.join(reason.replace('_', ' ') for reason in row.reasons)}. "
        f"Shared declared parent: {row.shared_parent or 'unknown'}; relationship unverified."
        for row in value.source_relationships[:100]
    )
    if len(value.source_relationships) > 100:
        relations += (
            f"{len(value.source_relationships) - 100} further pairs remain in saved metadata.",
        )
    sections.append(
        ("Source relationship cautions", relations or ("No relationship pairs saved.",))
    )
    return tuple(sections)
