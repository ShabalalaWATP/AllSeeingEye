"""Deployment gates select one transport per dataset and preserve public fallbacks."""

import pytest
from pydantic import ValidationError

from ase.adapters.feeds.conflict_acled import AcledConnector
from ase.adapters.feeds.conflict_reliefweb import ReliefWebReportsConnector
from ase.adapters.feeds.conflict_ucdp import UcdpCandidateConnector
from ase.adapters.feeds.conflict_ucdp_public import UcdpPublicCandidateConnector
from ase.adapters.feeds.registry import build_connectors
from ase.infrastructure.settings import Settings
from feeds_helpers import NOW, FakeClock, FakeHttp


def test_default_registration_has_public_monthly_baseline_and_reliefweb_rss() -> None:
    connectors = build_connectors(FakeHttp(), FakeClock(NOW))  # type: ignore[arg-type]
    by_id = {connector.spec.id: connector for connector in connectors}
    assert len(by_id) == len(connectors)
    assert isinstance(by_id["ucdp_candidate"], UcdpPublicCandidateConnector)
    assert "reliefweb_updates" in by_id
    assert "acled_events" not in by_id and "reliefweb_reports" not in by_id


def test_credentials_select_api_without_duplicate_public_or_rss_feeds() -> None:
    connectors = build_connectors(
        FakeHttp(),
        FakeClock(NOW),
        ucdp_access_token="ucdp-fixture",
        acled_access_token="acled-fixture",
        reliefweb_appname="approved-app",
        iso3_to_iso2={"UKR": "UA"},
    )  # type: ignore[arg-type]
    by_id = {connector.spec.id: connector for connector in connectors}
    assert len(by_id) == len(connectors)
    assert isinstance(by_id["ucdp_candidate"], UcdpCandidateConnector)
    assert isinstance(by_id["acled_events"], AcledConnector)
    assert isinstance(by_id["reliefweb_reports"], ReliefWebReportsConnector)
    assert "reliefweb_updates" not in by_id
    assert all("fixture" not in connector.spec.url for connector in connectors)


def test_disabled_sources_are_not_reenabled_by_credentials_or_fallbacks() -> None:
    disabled = {"ucdp_candidate", "acled_events", "reliefweb_reports"}
    connectors = build_connectors(
        FakeHttp(),
        FakeClock(NOW),
        disabled,
        ucdp_access_token="fixture",
        acled_access_token="fixture",
        reliefweb_appname="approved-app",
    )  # type: ignore[arg-type]
    ids = {connector.spec.id for connector in connectors}
    assert not disabled & ids
    assert "reliefweb_updates" not in ids


@pytest.mark.parametrize(
    "field,value",
    [
        ("ucdp_candidate_version", "latest"),
        ("ucdp_candidate_version", "26.0.13"),
        ("reliefweb_appname", "bad query?"),
        ("reliefweb_appname", ""),
    ],
)
def test_invalid_provider_configuration_is_rejected(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, env="test", **{field: value})


def test_secrets_are_redacted_and_default_month_is_explicit() -> None:
    settings = Settings(
        _env_file=None,
        env="test",
        ucdp_access_token="ucdp-fixture-secret",
        acled_access_token="acled-fixture-secret",
    )
    assert settings.ucdp_candidate_version == "26.0.7"
    assert "ucdp-fixture-secret" not in repr(settings)
    assert "acled-fixture-secret" not in settings.model_dump_json()
