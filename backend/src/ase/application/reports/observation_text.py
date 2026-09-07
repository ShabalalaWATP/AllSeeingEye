"""Bounded structured observation facts, without embedding coordinate arrays in prompts."""

from ase.domain.evidence import EvidenceItem


def observation_lines(item: EvidenceItem) -> tuple[str, ...]:
    lines: list[str] = []
    if item.observation is not None:
        observed = item.observation
        lines.append(f"Acquisition time: {observed.acquired_at.isoformat()}")
        if observed.processed_at is not None:
            lines.append(f"Processing time: {observed.processed_at.isoformat()}")
        if observed.scene_cloud_cover is not None:
            lines.append(f"Scene cloud cover: {observed.scene_cloud_cover:g}%")
        lines.append(
            "Acquisition, processing, publication, retrieval and report snapshot "
            "are distinct times. "
            "Scene metadata does not establish usable coverage, an event or a cause."
        )
    if item.geometry is not None:
        lines.append(f"Source geometry role: {item.geometry.location_role.value}")
        lines.append(f"Source geometry SHA-256: {item.geometry.sha256}")
    return tuple(lines)
