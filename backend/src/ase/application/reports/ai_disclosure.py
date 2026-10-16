"""Use only the selected frozen version, never current configuration or client input."""

from ase.domain.ai_disclosure import AiDisclosure, Provider
from ase.domain.errors import InvalidRequest
from ase.domain.llm import LlmRole
from ase.domain.report_records import ReportVersion


def report_ai_disclosure(version: ReportVersion) -> AiDisclosure:
    # This marker is emitted only by no_evidence_draft, which never calls a model.
    # Attempts alone is insufficient: resumed generated checkpoints can also be zero.
    if any(finding.rule == "no_evidence" for finding in version.findings):
        return AiDisclosure("", "unknown", assessment_generated=False)
    provider: Provider = "unknown"
    if version.model_routing is not None:
        matches = [
            profile
            for profile in version.model_routing.profiles
            if profile.role is LlmRole.ASSESSMENT and profile.profile_id == version.profile_id
        ]
        if len(matches) == 1:
            provider = matches[0].provider.value
    try:
        return AiDisclosure(version.model, provider)
    except ValueError:
        raise InvalidRequest("The saved model provenance cannot be safely displayed.") from None
