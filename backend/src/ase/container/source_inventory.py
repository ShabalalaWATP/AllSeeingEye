"""Source and platform connection inventory for signed-in users, without credential values."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.firms_credentials import SqlFirmsCredentials
from ase.application.model_routing import ModelRouting
from ase.application.source_inventory import (
    ConnectionState,
    PlatformConnection,
    RequirementKind,
    SourceInventory,
    SourceRequirement,
)
from ase.container.source_requirements import (
    FIRMS_SETTING,
    OPTIONAL_CONNECTOR_SPECS,
    media_requirement,
    media_tools_found,
    source_requirements,
)
from ase.domain.errors import NoModelAvailable
from ase.domain.llm import LlmRole
from ase.domain.sources import SourceSpec
from ase.domain.users import User

if TYPE_CHECKING:
    from ase.container import Container


def _platform(
    key: str,
    name: str,
    purpose: str,
    kind: RequirementKind,
    present: bool,
    setting: str,
    *,
    optional: bool = False,
) -> PlatformConnection:
    if present:
        state = ConnectionState.CONNECTED
    elif kind in ("api_key", "credentials"):
        state = ConnectionState.KEY_MISSING
    else:
        state = ConnectionState.NOT_CONFIGURED
    return PlatformConnection(
        key,
        name,
        purpose,
        state,
        SourceRequirement(
            kind,
            present,
            "environment" if present else "none",
            setting,
            f"{setting} is set." if present else f"Set {setting} on the server.",
            optional,
        ),
        "Configured." if present else "Optional." if optional else "Not configured.",
    )


class SourceInventoryWiring:
    """Composes the user-facing inventory. Credential values never leave the server."""

    def optional_connector_specs(self) -> tuple[SourceSpec, ...]:
        """Keyed live feeds that are only constructed once their credential exists."""
        return OPTIONAL_CONNECTOR_SPECS

    def source_inventory(self, session: AsyncSession) -> SourceInventory:
        container = cast("Container", self)
        settings = container.settings
        credentials = SqlFirmsCredentials(session)

        async def resolve(source_id: str) -> SourceRequirement | None:
            if not source_id.startswith("firms_viirs_"):
                return None
            if settings.firms_map_key:
                return SourceRequirement(
                    "api_key",
                    True,
                    "environment",
                    FIRMS_SETTING,
                    "NASA FIRMS map key configured on the server.",
                )
            if (await credentials.get()).active_encrypted:
                return SourceRequirement(
                    "api_key",
                    True,
                    "database",
                    FIRMS_SETTING,
                    "NASA FIRMS map key saved by an administrator.",
                )
            return SourceRequirement(
                "api_key",
                False,
                "none",
                FIRMS_SETTING,
                "Set ASE_FIRMS_MAP_KEY or save a key under Admin, Sources to collect NASA FIRMS "
                "detections with your own allowance.",
            )

        return SourceInventory(
            container.scheduler.connectors,
            container.research_sources,
            self.optional_connector_specs(),
            source_requirements(settings),
            container.health,
            container.source_admission,
            tuple(settings.disabled_feed_ids),
            resolve,
        )

    async def platform_connections(
        self, session: AsyncSession, user: User
    ) -> list[PlatformConnection]:
        container = cast("Container", self)
        settings = container.settings
        repos = container.repositories(session)
        purpose = "Writes briefings, reports and the Eye assistant's answers."
        try:
            routing = await ModelRouting(repos.llm_profiles, repos.llm_bindings).snapshot(
                personal_owner_id=user.id
            )
            profile = routing.required(LlmRole.ASSESSMENT)
            model = PlatformConnection(
                "assessment_model",
                "AI assessment model",
                purpose,
                ConnectionState.CONNECTED,
                SourceRequirement(
                    "model",
                    True,
                    "database",
                    None,
                    f"{profile.name}: {profile.provider.value} {profile.model}.",
                ),
                "Assigned for your personal workspace.",
            )
        except NoModelAvailable as exc:
            model = PlatformConnection(
                "assessment_model",
                "AI assessment model",
                purpose,
                ConnectionState.KEY_MISSING,
                SourceRequirement("model", False, "none", None, str(exc)),
                "No model is available for your personal workspace.",
            )
        found = media_tools_found(settings)
        return [
            model,
            _platform(
                "credential_encryption",
                "Credential encryption",
                "Stores AI provider keys entered by administrators.",
                "credentials",
                container.cipher.available,
                "ASE_ENCRYPTION_KEY",
            ),
            _platform(
                "os_maps",
                "Ordnance Survey maps",
                "OS Road, Outdoor and Light base layers on the map.",
                "api_key",
                container.tiles.configured,
                "ASE_OS_MAPS_KEY",
            ),
            _platform(
                "email",
                "Email delivery",
                "Account activation, password reset and email MFA codes.",
                "credentials",
                bool(settings.smtp_host and settings.smtp_from_email),
                "ASE_SMTP_HOST and ASE_SMTP_FROM_EMAIL",
            ),
            _platform(
                "highway_cameras",
                "Washington State highway cameras",
                "WSDOT camera snapshots in the CCTV catalogue.",
                "api_key",
                bool(settings.wsdot_access_code),
                "ASE_WSDOT_ACCESS_CODE",
            ),
            _platform(
                "alert_webhook",
                "Alert webhook",
                "Posts fired indicators to an external https endpoint.",
                "endpoint",
                bool(settings.alert_webhook_url),
                "ASE_ALERT_WEBHOOK_URL",
                optional=True,
            ),
            _platform(
                "url_archive",
                "Wayback archiving",
                "Asks the Internet Archive to preserve each cited URL after a report.",
                "toggle",
                bool(settings.archive_enabled),
                "ASE_ARCHIVE_ENABLED",
                optional=True,
            ),
            _platform(
                "conflict_screening",
                "Conflict relevance screening",
                "Uses the global model to screen machine-coded conflict reports.",
                "toggle",
                settings.conflict_screening_enabled,
                "ASE_CONFLICT_SCREENING_ENABLED",
                optional=True,
            ),
            PlatformConnection(
                "media_tools",
                "Local OCR and video tools",
                "Extracts text and keyframes from private image and video uploads.",
                ConnectionState.CONNECTED if found else ConnectionState.NOT_CONFIGURED,
                media_requirement(settings),
                "Discovered on PATH or from operator settings.",
            ),
            _platform(
                "pdf_runtime",
                "Isolated PDF runtime",
                "Optional operator-owned Linux runtime for PDF and Word exports.",
                "runtime",
                bool(settings.report_pdf_runtime),
                "ASE_REPORT_PDF_RUNTIME",
                optional=True,
            ),
        ]
