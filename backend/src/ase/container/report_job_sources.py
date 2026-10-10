"""Source provenance of every retained report input, refreshed on each payload change."""

from typing import TYPE_CHECKING, Any

from ase.application.report_jobs.collection_records import evidence_from_json
from ase.application.reports.challenge_expansion_checkpoint import packet_from_dict, plan_from_dict
from ase.application.reports.challenge_expansion_partial import KEY, decode_partial
from ase.application.reports.production_checkpoint import collection_from_dict
from ase.container.report_job_cache import attempt_cache, snapshot_key
from ase.domain.errors import InvalidRequest
from ase.domain.evidence_sources import evidence_source_ids
from ase.domain.report_jobs import ReportJob
from ase.domain.report_records import ReportVersion
from ase.domain.research_records import ResearchReceipt
from ase.domain.web_research import WEB_SOURCE_ID

if TYPE_CHECKING:
    from ase.container import Container


class ReportJobSourceDisabled(InvalidRequest):
    code = "report_job_source_disabled"
    default_message = "A source in this report is disabled. Its saved content cannot be used."


def _web_sources(receipt: ResearchReceipt | None) -> set[str]:
    web = receipt.web_research if receipt else None
    return (
        {WEB_SOURCE_ID} if web and (web.synthesis or web.citations or web.consulted_urls) else set()
    )


def _sources(payload: dict[str, Any]) -> frozenset[str]:
    frozen = payload["input"]
    identifiers = evidence_source_ids(evidence_from_json(frozen["evidence"]))
    collection = payload.get("collection")
    if collection is not None:
        snapshot = collection_from_dict(collection)
        identifiers.update(evidence_source_ids(snapshot.selection.items))
        identifiers.update(_web_sources(snapshot.receipt))
    expansion = payload.get("challenge_expansion_packet")
    if expansion is not None:
        packet = packet_from_dict(expansion)
        identifiers.update(evidence_source_ids(packet.added))
        identifiers.update(_web_sources(packet.receipt))
    if payload.get(KEY) is not None:
        plan = plan_from_dict(payload.get("challenge_expansion_plan"))
        partial = decode_partial(payload[KEY], plan.fingerprint)
        identifiers.update(evidence_source_ids(item for row in partial for item in row.evidence))
    return frozenset(identifiers)


async def check_sources(
    container: "Container", stored: ReportJob, baseline: ReportVersion | None = None
) -> None:
    frozen = stored.payload.get("input")
    if frozen is None:
        return
    source_payload = {
        key: stored.payload.get(key)
        for key in (
            "input",
            "collection",
            "challenge_expansion_packet",
            "challenge_expansion_plan",
            KEY,
        )
    }
    cache = attempt_cache.get()
    key = snapshot_key(source_payload) if cache is not None else None
    if cache is None or cache.source_key != key:
        identifiers = _sources(source_payload)
        if cache is not None:
            cache.source_key, cache.source_ids = key, identifiers
    else:
        identifiers = cache.source_ids
    current = set(identifiers)
    if baseline is not None:
        current.update(evidence_source_ids(baseline.evidence))
    # The cache stores parsed provenance only. Current source switches and the
    # freshly authorised baseline are consulted on every checkpoint and heartbeat.
    if current and not all(
        (await container.source_admission.enabled_many(tuple(current))).values()
    ):
        raise ReportJobSourceDisabled()
