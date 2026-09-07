"""Bounded structured observation facts, without embedding coordinate arrays in prompts."""

from ase.domain.evidence import EvidenceItem, injection_flags
from ase.domain.project import project_to_dict


def observation_lines(item: EvidenceItem, *, for_prompt: bool = False) -> tuple[str, ...]:
    lines: list[str] = []
    project_safe = not (
        for_prompt
        and item.project is not None
        and injection_flags(
            *(value for value in project_to_dict(item.project).values() if isinstance(value, str))
        )
    )
    if item.project is not None and project_safe:
        project = item.project
        lines.append(
            f"Project {project.project_id}, dataset {project.dataset_id}, "
            f"release {project.release_id}"
        )
        for label, year in (
            ("Commitment", project.commitment_year),
            ("Implementation", project.implementation_year),
            ("Completion", project.completion_year),
        ):
            lines.append(
                f"{label} year: {year} (exact date unknown)"
                if year is not None
                else f"{label} year: unknown"
            )
        lines.append(
            f"Source-reported status: {project.reported_status}; not a current verified finding."
        )
        lines.append(f"Project source SHA-256: {project.source_sha256}")
        lines.append(
            f"Attribution: {project.attribution}. Data licence: {project.data_licence}; "
            f"geometry licence: {project.geometry_licence}."
        )
        lines.append(project.limitations)
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
