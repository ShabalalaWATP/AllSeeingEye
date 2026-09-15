"""Which documented setting unlocks each keyed or gated source, and whether it is present."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ase.adapters.feeds.aisstream import SPEC as AISSTREAM_SPEC
from ase.adapters.feeds.barentswatch import SPEC as BARENTSWATCH_SPEC
from ase.adapters.feeds.conflict_acled import SPEC as ACLED_SPEC
from ase.adapters.feeds.conflict_reliefweb import SPEC as RELIEFWEB_SPEC
from ase.adapters.feeds.network_outages import CLOUDFLARE_RADAR
from ase.application.source_inventory import RequirementKind, SourceRequirement
from ase.container.research_inputs import media_tools
from ase.domain.web_research import WEB_SOURCE_ID

if TYPE_CHECKING:
    from ase.infrastructure.settings import Settings

OPTIONAL_CONNECTOR_SPECS = (
    AISSTREAM_SPEC,
    BARENTSWATCH_SPEC,
    ACLED_SPEC,
    RELIEFWEB_SPEC,
    CLOUDFLARE_RADAR,
)

FIRMS_SETTING = "ASE_FIRMS_MAP_KEY or the administrator FIRMS connection"
MEDIA_SETTINGS = (
    "ASE_RESEARCH_TESSERACT_PATH, ASE_RESEARCH_FFMPEG_PATH and ASE_RESEARCH_FFPROBE_PATH"
)


def _key(setting: str, present: bool, what: str, *, optional: bool = False) -> SourceRequirement:
    if present:
        note = f"{what[0].upper()}{what[1:]} is configured on the server."
    elif optional:
        note = f"Optional. Set {setting} to unlock {what}; public access is used without it."
    else:
        note = f"Set {setting} on the server to enable {what}."
    return SourceRequirement(
        "api_key", present, "environment" if present else "none", setting, note, optional
    )


def _configured(
    kind: RequirementKind, setting: str, present: bool, when_present: str, when_missing: str
) -> SourceRequirement:
    return SourceRequirement(
        kind,
        present,
        "environment" if present else "none",
        setting,
        when_present if present else when_missing,
    )


def media_tools_found(settings: Settings) -> list[str]:
    tools = media_tools(settings)
    return [
        name
        for name, path in (
            ("Tesseract OCR", tools.tesseract),
            ("FFmpeg", tools.ffmpeg),
            ("FFprobe", tools.ffprobe),
        )
        if path
    ]


def media_requirement(settings: Settings) -> SourceRequirement:
    found = media_tools_found(settings)
    return SourceRequirement(
        "runtime",
        bool(found),
        "environment" if found else "none",
        MEDIA_SETTINGS,
        f"Available locally: {', '.join(found)}."
        if found
        else "No local OCR or video tools were found on the server.",
    )


def source_requirements(settings: Settings) -> dict[str, SourceRequirement]:
    """Which documented setting unlocks each keyed or gated source, and whether it is set."""
    barentswatch = bool(
        settings.barentswatch_client_id
        and settings.barentswatch_client_id.get_secret_value().strip()
        and settings.barentswatch_client_secret
        and settings.barentswatch_client_secret.get_secret_value().strip()
    )
    requirements: dict[str, SourceRequirement] = {
        AISSTREAM_SPEC.id: _key(
            "ASE_AISSTREAM_API_KEY", bool(settings.aisstream_api_key), "global ship positions"
        ),
        BARENTSWATCH_SPEC.id: _configured(
            "credentials",
            "ASE_BARENTSWATCH_CLIENT_ID and ASE_BARENTSWATCH_CLIENT_SECRET",
            barentswatch,
            "BarentsWatch AIS client credentials are configured on the server.",
            "Create a BarentsWatch AIS client and set both settings on the server.",
        ),
        ACLED_SPEC.id: _key(
            "ASE_ACLED_ACCESS_TOKEN", bool(settings.acled_access_token), "ACLED events"
        ),
        RELIEFWEB_SPEC.id: _key(
            "ASE_RELIEFWEB_APPNAME", bool(settings.reliefweb_appname), "the ReliefWeb reports API"
        ),
        CLOUDFLARE_RADAR.id: _key(
            "ASE_CLOUDFLARE_RADAR_TOKEN",
            bool(settings.cloudflare_radar_token),
            "Cloudflare Radar outage annotations",
        ),
        "cloudflare_radar_attack_trends": _key(
            "ASE_CLOUDFLARE_RADAR_TOKEN",
            bool(settings.cloudflare_radar_token),
            "Cloudflare Radar aggregated attack distributions",
        ),
        **{
            source_id: _configured(
                "acknowledgement",
                "ASE_CLOUDFLARE_RADAR_TOKEN and "
                "ASE_CLOUDFLARE_RADAR_NONCOMMERCIAL_USE_ACKNOWLEDGED",
                bool(settings.cloudflare_radar_token)
                and settings.cloudflare_radar_noncommercial_use_acknowledged,
                "Cloudflare Radar token and non-commercial use acknowledgement are configured.",
                "Configure the Radar token and acknowledge suitable CC BY-NC 4.0 use before "
                "enabling Radar research.",
            )
            for source_id in (
                "research-cloudflare-radar-layer3",
                "research-cloudflare-radar-layer7",
            )
        },
        "ucdp_candidate": _key(
            "ASE_UCDP_ACCESS_TOKEN",
            bool(settings.ucdp_access_token),
            "the authenticated UCDP API",
            optional=True,
        ),
        "research-openalex": _key(
            "ASE_OPENALEX_API_KEY",
            bool(settings.openalex_api_key),
            "higher OpenAlex limits",
            optional=True,
        ),
        "research-openaq-area": _key(
            "ASE_OPENAQ_API_KEY", bool(settings.openaq_api_key), "OpenAQ air-quality research"
        ),
        "research-certificate-transparency": _key(
            "ASE_CERTIFICATE_TRANSPARENCY_KEY",
            bool(settings.certificate_transparency_key),
            "certificate transparency search",
        ),
        WEB_SOURCE_ID: SourceRequirement(
            "model",
            None,
            "unknown",
            None,
            "Uses the destination's OpenAI connection; administrators assign models under "
            "Admin, Models.",
        ),
        "research-ooni-aggregate": _configured(
            "acknowledgement",
            "ASE_OONI_NONCOMMERCIAL_USE_ACKNOWLEDGED",
            settings.ooni_noncommercial_use_acknowledged,
            "Non-commercial use of OONI aggregates is acknowledged on the server.",
            "Set ASE_OONI_NONCOMMERCIAL_USE_ACKNOWLEDGED=true after confirming suitable use "
            "of CC BY-NC-SA data.",
        ),
        "research-ioda-outage-events": _configured(
            "acknowledgement",
            "ASE_IODA_PUBLIC_DATA_USE_ACKNOWLEDGED",
            settings.ioda_public_data_use_acknowledged,
            "Operator reviewed IODA public data-use terms and enabled research collection.",
            "Review IODA public data-use permission, then set "
            "ASE_IODA_PUBLIC_DATA_USE_ACKNOWLEDGED=true if suitable.",
        ),
        "research-aiddata-projects": _configured(
            "catalogue",
            "ASE_AIDDATA_CATALOGUE_PATH",
            bool(settings.aiddata_catalogue_path),
            "A local AidData catalogue is configured.",
            "Import a catalogue with ase import-aiddata and set ASE_AIDDATA_CATALOGUE_PATH.",
        ),
        "research_media": media_requirement(settings),
    }
    for suffix in ("", "-officers", "-psc"):
        requirements[f"research-companies-house{suffix}"] = _key(
            "ASE_COMPANIES_HOUSE_KEY",
            bool(settings.companies_house_key),
            "Companies House registry research",
        )
    for authority, setting, path in (
        ("uksl", "ASE_UKSL_SNAPSHOT_PATH", settings.uksl_snapshot_path),
        ("ofac_sdn", "ASE_OFAC_SDN_SNAPSHOT_PATH", settings.ofac_sdn_snapshot_path),
    ):
        requirements[f"research-designations-{authority}"] = _configured(
            "snapshot",
            setting,
            bool(path),
            "A validated designation snapshot is configured.",
            f"Import a snapshot with ase import-designations and set {setting}.",
        )
    return requirements
